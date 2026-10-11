# 展会演示系统 — 机器人侧功能交接说明

版本：2026-10-11（全量深度验证后） | 面向：页面侧开发团队

---

## 一、系统架构总览

```
访客（普通话或粤语）
  → 机器人应用（Python，部署在大脑板）
      ├─ AIChain：语音识别 + 对话理解（iFlytek）
      ├─ AIChain TTS voiceId 94「子谦(粤)」：粤语语音合成
      ├─ 官方 RTSP 抓拍工具：5 秒参考视频（get_video_stream.py，原样使用）
      ├─ TOS（BytePlus 桶 qiyuanseedance）：参考视频临时托管
      └─ Seedance（dreamina-seedance-2-0-fast-260128）：15 秒 / 16:9 视频生成
  → 你们的 v2 页面（直连模式）
      ├─ 轮询 GET :8766/demo/last 获取任务
      └─ 自行 pollArk 查询结果并播放
```

页面打开方式（现场）：`http://<机器人IP>:8766/v2-aurora-flow.html`
（:8766 同时提供页面、兜底视频 assets 与 /demo/last JSON）

---

## 二、已验证功能清单（逐项验证证据）

| # | 功能 | 验证结果 |
|---|---|---|
| 1 | 双语语音对话 | 普通话与粤语输入均被正确识别（AIChain STT engine 5, zh-HK）；NLU 一律以粤语回复（多次实测，含 3 轮完整对话录音） |
| 2 | 粤语语音合成 | AIChain voiceId 94「子谦(粤)」（男声）实听确认；备选 BytePlus 温柔粤语女声 |
| 3 | 视频生成流程 | 访客专用指令（如「帮我生成视频」）→ 粤语等待语「請稍等，我馬上幫你生成視頻。」→ 5 秒抓拍 → 固定提示词生成（访客不提供场景，场景全部来自实拍画面） |
| 4 | 固定提示词 | `VIDEO_GEN_PROMPT=把這個場景變成一段自然流暢、色彩生動的電影感短片。`（.env 可改） |
| 5 | 参考视频规则 | 分辨率必须 ≥ 854×480（API 硬性要求，机器人摄像头远高于此）；640×480 会被拒（HTTP 400） |
| 6 | 视频仅生成（无音频） | `generate_audio=false` 默认开启：规避输出音频版权策略失败（真实办公室素材曾连续触发 `OutputAudioSensitiveContentDetected`，视频模式下同一素材成功） |
| 7 | 生成耗时 | 实测 117–237 秒（2.0-fast 模型） |
| 8 | 多观众并发控制 | 每轮独立临时文件（互不覆盖）；指令识别后立即抓拍（画面即为当时所见）；上传/提交串行；旧轮次不会覆盖新轮次的 /demo/last |
| 9 | 数据共享控制 | **仅向页面侧传递视频生成指令**：/demo/last 仅视频轮次写入；WS 聊天内容默认不广播（`SHARE_CHAT_WITH_PAGE=0`）；对话内容不出机器人 |
| 10 | 双足画面翻转 | 机器人双足形态下左目摄像头原始画面倒置（官方手册明文）；机器人侧已启用 `CAMERA_FLIP_180=1`，上传前自动旋转 180° |
| 11 | 上传链路 | TOS 桶（ap-southeast-1，虚拟主机寻址；路径式寻址会被拒 InvalidPathAccess，已修复并实测往返成功） |
| 12 | 页面包集成 | 你们的 2026-10-10 页面包已安装并在 :8766 提供；页面与机器人侧模型一致（`dreamina-seedance-2-0-fast-260128`，pollArk 过滤依赖此一致） |
| 13 | 仿真演练 | 官方 MuJoCo 模型（T1-V2mesh.xml）+ 模拟画面 → 完整生成链路实测成功（156 秒） |
| 14 | 自动化测试 | demo_ui 33 / conversation 26 / seedance 21，全部通过 |

---

## 三、页面侧接口契约

### GET http://<host>:8766/demo/last
```json
{"round": 2, "text": "帮我生成一个视频", "time": "15:01", "taskId": "cgt-..."}
```
- 仅视频请求轮次会更新此接口；闲聊不写入（已回归测试）
- `text` = 访客原话（触发指令）；生成所用提示词为固定 VIDEO_GEN_PROMPT
- 旧轮次不会覆盖新轮次

### WS ws://<host>:8765（契约 v2.0，备用通道）
- 消息类型：system / pong / chat / video_failed
- 视频轮次广播：访客原话 + 粤语等待语（属视频指令，允许共享）
- 聊天轮次：默认不广播回复（数据共享控制）；调试可 `SHARE_CHAT_WITH_PAGE=1`

### 模型一致性要求
页面 pollArk 按模型过滤任务 —— **两端的模型必须保持 `dreamina-seedance-2-0-fast-260128`**。

---

## 四、关键配置（.env，随部署拷贝至机器人）

```
SEEDANCE_MODEL_ID=dreamina-seedance-2-0-fast-260128
VIDEO_GEN_PROMPT=<固定粤语提示词>
AICHAIN_TTS_VOICE_ID=94 / AICHAIN_TTS_ENABLED=1
CAMERA_VIDEO_REFERENCE=1 / CAMERA_CAPTURE_SECONDS=5.0 / CAMERA_FLIP_180=1
SEEDANCE_GENERATE_AUDIO=0（默认，规避版权策略）
SHARE_CHAT_WITH_PAGE=0（默认，仅共享视频指令）
```

---

## 五、已知行为与限制

1. **生成视频无音频**（默认）。如需音频：`SEEDANCE_GENERATE_AUDIO=1`，但部分素材可能触发输出音频版权策略失败，需重试。
2. **AIChain TTS 固定 16 kHz raw**；24 kHz 与 opus 请求被忽略；speed/pitch 参数无效。
3. **PrimeConsole 直播画面显示原始流**（双足下可能倒置）—— 属平台显示问题，不影响机器人侧抓拍（已自动翻转）。
4. 生成期间新视频请求会排队（等待语已先行回复）；页面侧「台面独占」开关行为与机器人侧互补。

---

## 六、部署与启动（机器人侧）

```bash
bash scripts/deploy_to_robot.sh <机器人IP> <SN_soc0密钥目录>
# 板上启动：
setsid bash /home/user/qiyuan-demo/run_demo_robot.sh > /tmp/qiyuan-demo.log 2>&1 < /dev/null &
```

---

## 七、需要页面侧确认的事项

1. 生成视频**无音频**是否可接受？（兜底视频带声音，如需一致可页面侧垫背景音）
2. 「台面独占」模式下，页面等待期间是否仍轮询 /demo/last（当前是）？
3. 页面机器人 URL 在板上应为 `http://127.0.0.1:8766/demo/last`（本机回环）；开发机为 WSL NAT IP。
