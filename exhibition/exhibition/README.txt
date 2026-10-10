展会大屏页面 · 使用说明（离线包）

【包内有什么】
  v2-aurora-flow.html      大屏页面（唯一要打开的文件）
  ark-config.example.js    现场配置模板
  assets/fallback/*.mp4    四条离线兜底视频（都带声音），出片失败/断外网时放

【换到新电脑上怎么做（两步）】
  1. 把 ark-config.example.js 复制一份，改名为 ark-config.js，填三样：
       arkKey   方舟 API Key（sk- 开头）
       arkModel 展会用的模型名
       arkBase  必须填新加坡域名 https://ark.ap-southeast.bytepluses.com/api/v3
                ⚠ 填北京域名会返回 200 但 total:0，看着像「没权限」，其实是两套任务台账
       robotUrl 机器人对话的小 JSON 地址；监听程序跑在这台机器就填 http://127.0.0.1:8766/demo/last
  2. 打开页面 —— 推荐用本机 http 打开，别直接双击文件：
       http://127.0.0.1:8766/v2-aurora-flow.html
     （监听程序顺带就是这台机器的静态服务器，页面和兜底视频都从它出。）
     直接双击 = 浏览器认为这是「无来源」的页面，问机器人/问方舟的跨域请求可能被它自己拦掉；
     断网彩排想双击打开也行：地址栏加 ?mode=local，纯前端演示，不需要任何服务。

【没有 ark-config.js 也能跑】
  地址栏带参数即可临时覆盖，比如断网彩排：
       v2-aurora-flow.html?mode=local
  控制面板（右下角齿轮）里所有参数都能现场改，改完立刻生效，并记在这台浏览器的本地存储里。

【两个必须知道的开关】
  真实模拟 = 开：绝不放兜底视频，只等真片，等不到就回待机。彩排/断网演示请关掉它。
  台面独占：一位观众的视频在生成或在播时，下一位开口只进对话流水、不抢台，播完才上台。

【注意】
  ark-config.js 里有密钥，不要提交到 Git、不要转发给厂商。展会结束后去方舟控制台把这把 key 换掉。
