// 复制成同目录的 ark-config.js 再填真值。ark-config.js 已写进 .gitignore，绝不进 Git（编码规范红线 9）。
// 展示笔记本上只需要这一个文件 + 那个 HTML，双击 HTML 即现场模式启动。
window.ARK_CFG = {
  mode: 'direct',                                            // 现场默认走「页面直连轮询」
  robotUrl: 'http://127.0.0.1:8766/demo/last',               // 监听程序就在大屏本机，回环即可（不用填机器人 IP）
  arkKey: '',                                                // SeeDance/方舟 API 密钥：只填这里，别填进 HTML
  arkModel: 'dreamina-seedance-2-0-fast-260128',             // 🛑 必须与 submitter 的 SEEDANCE_MODEL_ID 同款，否则页面 pollArk 的模型过滤会跳过 submitter 下的单
  arkBase: 'https://ark.ap-southeast.bytepluses.com/api/v3', // 海外（新加坡）账号；填 cn-beijing 会返回 200 但 total:0（两套台账不通）
  fakeVideo: ''                                              // 可选：本地压底视频，如 assets/fallback/fallback-1.mp4
};
