/*
 * mock-ws-backend.js —— 冒充「机器人 Python」的零依赖 WebSocket 服务器（展会大屏 demo 联调用）
 *
 * 用途：机器人团队还没接上时，用它按《接口契约》WS 版吐消息，让展示页面先跑通渲染链路；
 *       也是给 Python 团队的「协议活样例」——他们照本文件发出的 JSON 结构实现即可。
 * 零依赖：只用 Node 内置 http + crypto，自己实现 RFC6455 握手与帧编解码，无需 npm install。
 *
 * 跑法：  node mock-ws-backend.js            → 默认 8765 端口
 *         打开页面：http://localhost:8765/v1-command-center.html?ws=ws://localhost:8765
 *         （页面连本机 WS；控制面板输入一句话 → 本 mock 回推 chat(user)+chat(bot)，
 *          GEN_MS 后回推 video_ready(上游直链) → 页面播视频）
 *
 * 环境变量：PORT(8765) / GEN_MS(6000 生成耗时) / VIDEO(上游直链样例) / FAIL(0 正常 1 演示失败)
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PORT = parseInt(process.env.PORT || '8765', 10);
const GEN_MS = parseInt(process.env.GEN_MS || '6000', 10);
const FAIL = process.env.FAIL === '1';
const VIDEO = process.env.VIDEO || 'https://www.w3schools.com/html/mov_bbb.mp4';
const FIXED_BOT = '好的，我已收到您的请求，正在为您生成视频，请稍候。';
const GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11';

// ---------- 演示状态（单连接、单轮，够联调用）----------
let round = 0;
let genTimer = null;

// ---------- RFC6455 帧编解码（服务端→客户端不掩码；客户端→服务端需去掩码）----------
function encodeFrame(str) {
  const payload = Buffer.from(str, 'utf8');
  const len = payload.length;
  let header;
  if (len < 126) {
    header = Buffer.from([0x81, len]);                 // FIN + text(0x1)
  } else if (len < 65536) {
    header = Buffer.alloc(4); header[0] = 0x81; header[1] = 126; header.writeUInt16BE(len, 2);
  } else {
    header = Buffer.alloc(10); header[0] = 0x81; header[1] = 127; header.writeBigUInt64BE(BigInt(len), 2);
  }
  return Buffer.concat([header, payload]);
}
function sendWS(socket, obj) {
  try { socket.write(encodeFrame(JSON.stringify(obj))); } catch (e) { /* 连接已断 */ }
}
// 解析客户端帧（可能一 TCP 包多帧 / 半帧），返回剩余未消费 buffer
function decodeFrames(socket, buf) {
  let offset = 0;
  while (offset + 2 <= buf.length) {
    const b0 = buf[offset], b1 = buf[offset + 1];
    const opcode = b0 & 0x0f;
    const masked = (b1 & 0x80) !== 0;
    let len = b1 & 0x7f, p = offset + 2;
    if (len === 126) { if (p + 2 > buf.length) break; len = buf.readUInt16BE(p); p += 2; }
    else if (len === 127) { if (p + 8 > buf.length) break; len = Number(buf.readBigUInt64BE(p)); p += 8; }
    let mask = null;
    if (masked) { if (p + 4 > buf.length) break; mask = buf.slice(p, p + 4); p += 4; }
    if (p + len > buf.length) break;
    let payload = buf.slice(p, p + len);
    if (masked) { const out = Buffer.alloc(len); for (let i = 0; i < len; i++) out[i] = payload[i] ^ mask[i % 4]; payload = out; }
    offset = p + len;
    if (opcode === 0x8) { try { socket.end(); } catch (e) {} return null; }   // close
    if (opcode === 0x9) { /* ping → 回 pong，demo 简化忽略 */ }
    if (opcode === 0x1) handleClientMsg(socket, payload.toString('utf8'));
  }
  return buf.slice(offset);
}

// ---------- 收到页面消息：目前只处理 send（控制面板手动喂一句话）----------
function handleClientMsg(socket, text) {
  let m; try { m = JSON.parse(text); } catch (e) { return; }
  if (m.type === 'ping') { sendWS(socket, { type: 'pong' }); return; }
  if (m.type === 'send') {
    const visitorText = (m.text || '').trim() || '帮我生成一个海边日落的视频';
    startRound(socket, visitorText);
  }
}

// ---------- 起一轮：chat(user) → chat(bot) → (GEN_MS 后) video_ready / video_failed ----------
function startRound(socket, visitorText) {
  if (genTimer) clearTimeout(genTimer);
  round += 1;
  const r = round;
  const t = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  sendWS(socket, { type: 'chat', round: r, role: 'user', text: visitorText, time: t });
  sendWS(socket, { type: 'chat', round: r, role: 'bot', text: FIXED_BOT, time: t });
  console.log(`[round ${r}] 访客: ${visitorText}`);
  genTimer = setTimeout(() => {
    if (FAIL) {
      sendWS(socket, { type: 'video_failed', round: r, reason: 'upstream_error' });
      console.log(`[round ${r}] → video_failed`);
    } else {
      sendWS(socket, { type: 'video_ready', round: r, url: VIDEO });
      console.log(`[round ${r}] → video_ready ${VIDEO}`);
    }
  }, GEN_MS);
}

// ---------- HTTP：升级 WS + 顺带把同目录 html 供出来（同源免 CORS）----------
const server = http.createServer((req, res) => {
  const u = new URL(req.url, 'http://localhost');
  if (u.pathname === '/_control') {   // 测试钩子：/?_control 手动触发一轮 / 复位
    const a = u.searchParams.get('action');
    if (a === 'reset') { round = 0; if (genTimer) clearTimeout(genTimer); }
    res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
    return res.end('ok, round=' + round);
  }
  const rel = u.pathname === '/' ? '/v1-command-center.html' : u.pathname;
  const fp = path.join(__dirname, path.normalize(rel).replace(/^(\.\.[/\\])+/, ''));
  fs.readFile(fp, (err, data) => {
    if (err) { res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' }); return res.end('Not found: ' + rel); }
    const ext = path.extname(fp).toLowerCase();
    const type = ext === '.html' ? 'text/html; charset=utf-8'
      : ext === '.js' ? 'application/javascript; charset=utf-8'
      : ext === '.mp4' ? 'video/mp4' : ext === '.webm' ? 'video/webm' : 'text/plain; charset=utf-8';
    res.writeHead(200, { 'Content-Type': type }); res.end(data);
  });
});

server.on('upgrade', (req, socket) => {
  const key = req.headers['sec-websocket-key'];
  if (!key) { socket.destroy(); return; }
  const accept = crypto.createHash('sha1').update(key + GUID).digest('base64');
  socket.write(
    'HTTP/1.1 101 Switching Protocols\r\n' +
    'Upgrade: websocket\r\n' +
    'Connection: Upgrade\r\n' +
    'Sec-WebSocket-Accept: ' + accept + '\r\n\r\n'
  );
  socket.setNoDelay(true);
  let buf = Buffer.alloc(0);
  socket.on('data', (d) => { buf = Buffer.concat([buf, d]); const left = decodeFrames(socket, buf); if (left === null) { buf = Buffer.alloc(0); } else { buf = left; } });
  socket.on('close', () => { if (genTimer) clearTimeout(genTimer); });
  socket.on('error', () => {});
  // 连上即发一条 system 在线，页面状态灯转绿
  sendWS(socket, { type: 'system', online: true });
  console.log('[ws] 页面已连接');
});

server.listen(PORT, () => {
  console.log('机器人 mock WS 已启动：http://localhost:' + PORT);
  console.log('  打开页面： http://localhost:' + PORT + '/v1-command-center.html?ws=ws://localhost:' + PORT);
  console.log('  生成耗时 GEN_MS=' + GEN_MS + '  FAIL=' + (FAIL ? '1(演示失败)' : '0') + '  VIDEO=' + VIDEO);
});
