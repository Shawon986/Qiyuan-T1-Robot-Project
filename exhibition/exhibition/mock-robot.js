// 展会演示 · 「假机器人 + 假 SeeDance」联调桩（direct 模式本地彩排用，零依赖纯 Node）
//
// 它同时扮演两个角色，让页面在真机器人/真 SeeDance 之前就能把 direct 模式跑通：
//   ① 机器人小 JSON 端点  GET  /demo/last            → {round,text,time}
//   ② 假 SeeDance 任务列表 GET  .../contents/generations/tasks → 新任务先 pending，GEN_MS 后 succeeded
//
// 用法：
//   node mock-robot.js
//   说一句话（= 观众对机器人说完话）：http://127.0.0.1:8766/say?text=帮我生成海边日落
//   页面（另开浏览器标签）：file:///…/v2-aurora-flow.html?mode=direct&robot=http://127.0.0.1:8766/demo/last
//     &arkBase=http://127.0.0.1:8766/mock-ark&arkKey=mock&arkModel=mock-seedance
//   → 左侧冒观众气泡 + 机器人话术、进度爬到 95% 保持、GEN_MS 后自动播视频、播完回待机接着听下一位。
//
// 环境变量：PORT=8766  GEN_MS=8000  VIDEO=<url>
// 手动钩子： /say?text=… 说话 ｜ /say?text=…&fail=1 说一句但上游生成失败 ｜ /_control?action=reset 回到第 0 轮

const http = require('http');

const PORT = process.env.PORT || 8766;
const GEN_MS = parseInt(process.env.GEN_MS || '8000', 10);
const VIDEO = process.env.VIDEO || 'https://www.w3schools.com/html/mov_bbb.mp4';
const MODEL = 'mock-seedance';

let round = 0, lastText = '', lastTime = '';
let tasks = [];   // {id, model, status, created_at, content:{video_url}}

function hhmm() {
  const d = new Date();
  return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
}

// 观众说了一句 → 轮次 +1，并立刻提交一条「生成中」的假任务（真机器人就是在这个时刻调 SeeDance）
// fail=1 模拟上游自己判死（实测真发生过：输出音频版权），用来彩排「失败立刻切离线片」这条路径
function say(text, fail) {
  const t = String(text || '').trim();
  if (!t) return;
  round += 1; lastText = t; lastTime = hhmm();
  const id = 'cgt-' + new Date().toISOString().replace(/[-:TZ]/g, '').slice(0, 14) + '-' + Math.random().toString(36).slice(2, 6);
  tasks.unshift({ id, model: MODEL, status: 'pending', created_at: Math.floor(Date.now() / 1000), content: {} });
  setTimeout(() => {
    const task = tasks.find(x => x.id === id);
    if (!task) return;
    if (fail) {
      task.status = 'failed';
      task.error = { code: 'OutputAudioSensitiveContentDetected.PolicyViolation', message: 'output audio may be related to copyright restrictions' };
      console.log('[ark] ' + id + ' → failed');
    } else {
      task.status = 'succeeded'; task.content = { video_url: VIDEO };
      console.log('[ark] ' + id + ' → succeeded');
    }
  }, GEN_MS);
  console.log('[robot] round=' + round + ' text="' + t + '"' + (fail ? ' [会失败]' : '') + ' → ' + GEN_MS + 'ms 后落定');
}

function json(res, obj) {
  res.writeHead(200, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'authorization,content-type',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Cache-Control': 'no-store'
  });
  res.end(JSON.stringify(obj));
}

const server = http.createServer((req, res) => {
  const u = new URL(req.url, 'http://localhost');
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'authorization,content-type',
      'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
      'Access-Control-Max-Age': '86400'
    });
    return res.end();
  }

  if (u.pathname === '/demo/last') return json(res, { round, text: lastText, time: lastTime });
  if (u.pathname === '/say') { say(u.searchParams.get('text') || '帮我生成一个海边日落的视频', u.searchParams.get('fail') === '1'); return json(res, { round, text: lastText }); }
  if (u.pathname === '/_control') {
    if (u.searchParams.get('action') === 'reset') { round = 0; lastText = ''; tasks = []; }
    return json(res, { round, text: lastText });
  }
  // 假 SeeDance：任意前缀 + /contents/generations/tasks 都认，返回倒序任务列表
  if (u.pathname.endsWith('/contents/generations/tasks')) {
    return json(res, { code: 0, data: { items: tasks, total: tasks.length } });
  }

  res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('Not found: ' + u.pathname);
});

server.listen(PORT, () => {
  console.log('==================================================');
  console.log(' 假机器人 + 假 SeeDance 已启动 :' + PORT);
  console.log('--------------------------------------------------');
  console.log(` 观众说一句:  http://127.0.0.1:${PORT}/say?text=帮我生成海边日落视频`);
  console.log(` 页面地址:    v2-aurora-flow.html?mode=direct&robot=http://127.0.0.1:${PORT}/demo/last`);
  console.log(`              &arkBase=http://127.0.0.1:${PORT}/mock-ark&arkKey=mock&arkModel=${MODEL}`);
  console.log(` GEN_MS=${GEN_MS}ms`);
  console.log('==================================================');
});
