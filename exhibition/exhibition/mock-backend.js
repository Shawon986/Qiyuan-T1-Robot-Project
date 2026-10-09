// 展会演示系统 · 本地联调 mock 后端
// 作用：同时充当「后端中转站(白板)」+「冒充机器人」，让你在真后端/真机器人就绪前，
//       就能把「提交 → 轮询 → 渲染 → 播放」全链路跑通。零依赖，纯 Node。
//
// 用法：
//   node mock-backend.js
//   浏览器打开： http://localhost:8787/v1-command-center.html?live=1
//   再开一个标签「冒充机器人说话」： http://localhost:8787/robot?text=帮我生成海边日落视频
//   → 回到页面标签，就能看到自动冒对话、跑进度到95%保持、GEN_MS 后播放视频。
//
// 可选环境变量：
//   PORT=8787            监听端口
//   GEN_MS=6000          模拟 SeeDance 生成耗时（毫秒），到点后 phase→ready
//   FAIL=0               置 1 则生成完成后返回 failed（测试失败兜底）
//   VIDEO=<url>          自定义就绪后的视频地址（默认用原型里的示例 mp4）
//
// 手动控制钩子（浏览器直接访问即可）：
//   /api/v1/demo/_control?action=ready    立即就绪
//   /api/v1/demo/_control?action=failed   立即失败
//   /api/v1/demo/_control?action=reset    回到 idle（可开始下一轮）

const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 8787;
const GEN_MS = parseInt(process.env.GEN_MS || '6000', 10);
const FORCE_FAIL = (process.env.FAIL || '0') === '1';
const VIDEO = process.env.VIDEO || 'https://www.w3schools.com/html/mov_bbb.mp4';
const FIXED_BOT = '好的，我已收到您的请求，正在为您生成视频，请稍候。';

// 白板状态（对应契约 GET /api/v1/demo/state）
let state = { round: 0, phase: 'idle', messages: [], videoUrl: null };
let genTimer = null;

function nowHM() {
  const d = new Date();
  return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
}

// 处理一次 submit（机器人 / /robot 都走这里）。始终返回 Result.data 形状（accepted 标志，不用 HTTP 错误码），与真实后端一致。
function submit(text) {
  if (!text || !text.trim()) return { round: state.round, accepted: false, reason: 'invalid_text' };
  if (state.phase === 'generating') return { round: state.round, accepted: false, reason: 'busy' };

  state.round += 1;
  state.phase = 'generating';
  state.videoUrl = null;
  state.messages = [
    { role: 'user', text: text.trim(), time: nowHM() },
    { role: 'bot', text: FIXED_BOT, time: nowHM() }
  ];
  console.log(`[submit] round=${state.round} text="${text.trim()}"  →  ${GEN_MS}ms 后${FORCE_FAIL ? '失败' : '就绪'}`);

  if (genTimer) clearTimeout(genTimer);
  genTimer = setTimeout(() => {
    if (FORCE_FAIL) { state.phase = 'failed'; state.videoUrl = null; console.log('[gen] phase=failed'); }
    else { state.phase = 'ready'; state.videoUrl = VIDEO; console.log('[gen] phase=ready videoUrl=' + VIDEO); }
  }, GEN_MS);

  return { round: state.round, accepted: true, reason: null };
}

function resetState() {
  if (genTimer) clearTimeout(genTimer);
  genTimer = null;
  state = { round: state.round, phase: 'idle', messages: [], videoUrl: null };
}

function sendJson(res, status, obj) {
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': '*',
    'Cache-Control': 'no-store'
  });
  res.end(JSON.stringify(obj));
}

// 与真实后端一致：/api/* 一律 Result 信封 {code,msg,data}（编码规范 §3.2）
function ok(res, data) {
  sendJson(res, 200, { code: 0, msg: 'success', data });
}

const server = http.createServer((req, res) => {
  const u = new URL(req.url, 'http://localhost');

  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
      'Access-Control-Allow-Headers': '*'
    });
    return res.end();
  }

  // ① 页面轮询：读白板
  if (u.pathname === '/api/v1/demo/state' && req.method === 'GET') return ok(res, state);

  // ② 机器人提交：写白板（真机器人对接的就是这个）
  if (u.pathname === '/api/v1/demo/submit' && req.method === 'POST') {
    let body = '';
    req.on('data', c => body += c);
    req.on('end', () => {
      let text = '';
      try { text = (JSON.parse(body || '{}')).text || ''; } catch { text = ''; }
      ok(res, submit(text));
    });
    return;
  }

  // ③ 冒充机器人：浏览器直接打开 /robot?text=... 就提交，最方便手动测
  if (u.pathname === '/robot') {
    const text = u.searchParams.get('text') || '帮我生成一个海边日落的视频';
    return ok(res, submit(text));
  }

  // ④ 测试控制钩子
  if (u.pathname === '/api/v1/demo/_control') {
    const a = u.searchParams.get('action');
    if (a === 'ready') { if (genTimer) clearTimeout(genTimer); state.phase = 'ready'; state.videoUrl = VIDEO; }
    else if (a === 'failed') { if (genTimer) clearTimeout(genTimer); state.phase = 'failed'; state.videoUrl = null; }
    else if (a === 'reset') resetState();
    return ok(res, state);
  }

  // ⑤ 静态文件：把同目录 html 供出来（同源，免 CORS）
  const rel = u.pathname === '/' ? '/v1-command-center.html' : u.pathname;
  const fp = path.join(__dirname, path.normalize(rel).replace(/^(\.\.[/\\])+/, ''));
  fs.readFile(fp, (err, data) => {
    if (err) { res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' }); return res.end('Not found: ' + rel); }
    const ext = path.extname(fp).toLowerCase();
    const ct = ext === '.html' ? 'text/html; charset=utf-8'
      : ext === '.js' ? 'text/javascript; charset=utf-8'
      : ext === '.css' ? 'text/css; charset=utf-8'
      : ext === '.mp4' ? 'video/mp4' : 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': ct });
    res.end(data);
  });
});

server.listen(PORT, () => {
  console.log('==================================================');
  console.log(' 展会演示 · mock 后端已启动');
  console.log('--------------------------------------------------');
  console.log(` 页面(在线模式):  http://localhost:${PORT}/v1-command-center.html?live=1`);
  console.log(` 冒充机器人说话:  http://localhost:${PORT}/robot?text=帮我生成海边日落视频`);
  console.log(` 手动就绪/失败/重置: http://localhost:${PORT}/api/v1/demo/_control?action=ready|failed|reset`);
  console.log(` 生成耗时 GEN_MS=${GEN_MS}ms   强制失败 FAIL=${FORCE_FAIL}`);
  console.log('==================================================');
});
