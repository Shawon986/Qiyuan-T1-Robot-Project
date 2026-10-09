// 复制成同目录的 ark-config.js 再填真值。ark-config.js 已写进 .gitignore，绝不进 Git（编码规范红线 9）。
// 展示笔记本上只需要这一个文件 + 那个 HTML，双击 HTML 即现场模式启动。
window.ARK_CFG = {
  mode: 'direct',                                            // 现场默认走「页面直连轮询」
  robotUrl: 'http://192.168.1.20:8766/demo/last',            // 机器人小 JSON 端点（IP 现场填）
  arkKey: '',                                                // SeeDance/方舟 API 密钥：只填这里，别填进 HTML
  arkModel: 'dreamina-seedance-2-5-260628',                  // 这把 key 下挂着多个模型，必须锁定展会用的那个
  arkBase: 'https://ark.cn-beijing.volces.com/api/v3',
  fakeVideo: ''                                              // 可选：本地压底视频，如 assets/fallback/fallback-1.mp4
};
