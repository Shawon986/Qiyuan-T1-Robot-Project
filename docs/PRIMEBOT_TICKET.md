# PrimeBot 技术支持工单草案 / PrimeBot Support Ticket (Draft)

机器人序列号 Robot SN: `QY02BGH2609100103`
SDK: 门户 v1.0.0.0（T1，2026-10-10 下载）
上下文 Context: 展会演示（约 10 月 19 日彩排）；我们的应用只使用官方 SDK 接口，
应用层开发，不改动硬件/固件。Exhibition demo (~Oct 19 rehearsal); our app uses
official SDK interfaces only — application-layer, no hardware/firmware changes.

---

## 1. 保修确认 / Warranty confirmation  ⚠️ 最重要 / most important

**中文**：手机 APP 的「开发者功能 → 基础开发模式 (Basic)」启用后是否影响保修？
启用页面的提示写「开发者功能将失去保修」——请确认**仅开启基础开发模式**是否属于
豁免范围。我们的项目硬性要求保修完整。若基础开发模式也影响保修，请告知官方
建议的、不影响保修的二次开发开通方式。

**EN**: Does enabling **Basic developer mode** (phone APP: Settings → 开发者功能 →
基础开发模式) affect the warranty? The notice says enabling developer features
voids warranty — please confirm whether **Basic mode alone** is exempt. Warranty
must stay intact (project hard constraint). If Basic mode also voids it, please
give the officially recommended warranty-safe path for secondary development.

## 2. 展会期间如何避免「双应答」？/ How to avoid double responses during the exhibition?

**中文**：机器人内置 Agent 会响应原生唤醒词「元仔元仔」并用平台普通话 TTS 回复。
我们的应用同样监听该唤醒词并用粤语回复——访客唤醒时会出现**双应答**（内置助手
说普通话 + 我们的应用说粤语）。请按优先级回答以下问题：

2.1 **能否更换/关闭内置唤醒词？**（我们最希望的方案）机器人的 APP 或控制台能否
把内置助手的唤醒词改成其他词（如「小元」），或支持双唤醒词/自定义唤醒词？这样
访客说「元仔元仔」时只有我们的应用应答，内置助手完全不会被触发。

2.2 **是否存在官方的「展会模式/静音模式」？** 能否在不改硬件、不影响保修的前提下，
临时关闭内置助手的 NLU/TTS（静音其回复），或把内置提示音量调为 0？

2.3 **`only_voice` 模式是否官方支持？** 开发者社区的做法是把 Agent 运行模式属性
（`AGENT_PROPERTY_RUN_MODE`）通过 `SetAgentPropertiesRequest` 服务改为
`only_voice` 并重启 Agent。请确认：① 该模式在贵方固件上是否官方支持、效果是否
为「保留唤醒与拾音、停止内置 NLU/TTS」；② 是否影响保修；③ 该属性是运行时生效
还是重启后保持？

2.4 若以上都不可行：内置助手与应用同时通过 `PlayAudioFile` 播放时，系统如何仲裁
（优先级/media_role 避让规则）？能否将内置助手音量降为 0？

**EN**: The built-in agent responds to the native wake word 「元仔元仔」 with
platform (Mandarin) TTS. Our app listens to the same wake word and replies in
Cantonese — visitors would get **two responses** (built-in assistant in
Mandarin + our app in Cantonese). Please answer in priority order:

2.1 **Can the built-in wake word be changed or disabled?** (preferred) Can the
APP/console change the built-in assistant's wake word to something else (e.g.
「小元」), or does the robot support dual/custom wake words? Then 「元仔元仔」
would trigger ONLY our app, and the built-in assistant would never fire.

2.2 **Is there an official exhibition/silent mode?** Without touching hardware
or affecting warranty — temporarily disable the built-in assistant's NLU/TTS
(mute its replies) or set its prompt volume to 0?

2.3 **Is `only_voice` officially supported?** The developer community switches
the agent RUN_MODE property (`AGENT_PROPERTY_RUN_MODE`) to `only_voice` via the
`SetAgentPropertiesRequest` service and restarts the agent. Please confirm:
① officially supported on this firmware, and its effect is "keep wake +
pickup, stop built-in NLU/TTS"; ② warranty impact, if any; ③ runtime-only or
persistent across reboots?

2.4 If none of the above: when both the built-in assistant and our app play
audio via `PlayAudioFile`, how does the system arbitrate (priority/media_role
ducking rules)? Can the built-in assistant volume be set to 0?

## 3. 板间 SSH 与音频服务 / Inter-board SSH & audio service

**中文**：
- 我们已收到 SoC0/SoC1 的 SSH 密钥（SN 如上），登录用户是 `run` 吗？
- `PlayAudioFile` 音频服务运行在 **SoC 0**，读取 SoC 0 磁盘文件。我们的应用运行在
  SoC 1（脑板），需要从 SoC 1 **SSH 到 SoC 0**（`run@10.1.1.100`）上传临时音频
  文件后播放。请确认：① 板间 SSH 是否默认开放、登录用户；② 是否需要密码
  （`/tmp` 下临时目录读写权限）；③ 官方对「SoC 1 应用经板间 SSH 上传音频到
  SoC 0 播放」是否有推荐做法（或 SoC 1 本地磁盘是否也可被音频服务读取）。
- 官方示例格式为 24 kHz 单声道 PCM16 WAV，我们已按此转换（ffmpeg）。请确认
  支持的文件格式与时长上限（我们按 ≤605 s 处理）。

**EN**:
- SSH keys for soc0/soc1 received (SN above). Is the login user `run`?
- `PlayAudioFile` runs on **SoC 0** and reads SoC 0 disk. Our app runs on
  SoC 1 (brain board) and needs inter-board SSH (`run@10.1.1.100`) to upload
  temp audio files before playback. Please confirm: ① inter-board SSH is open
  by default + the login user; ② password needed? (read/write under /tmp);
  ③ the recommended official pattern for SoC 1 apps playing audio via files
  uploaded to SoC 0 (or can the audio service read SoC 1's local disk?).
- The official example uses 24 kHz mono PCM16 WAV — we convert accordingly
  (ffmpeg). Please confirm accepted formats and max duration (we assume ≤605 s).

## 4. 固件与 SDK 版本匹配 / Firmware ↔ SDK version

**中文**：请确认此台机器人当前固件对应的 SDK 基线版本（门户 SDK v1.0.0.0 与
git 仓库 v0.9.4.7 内容有差异，例如 agent/ASR 接口）。我们应以哪个版本为准？

**EN**: Please confirm which SDK baseline matches this robot's current firmware
(portal SDK v1.0.0.0 differs from git repo v0.9.4.7, e.g. agent/ASR interfaces).
Which one should we target?

## 5. 脑板外网访问 / Brain-board internet access

**中文**：展会期间 SoC 1（脑板）需直连云 API（火山引擎 ModelArk/Seedance、
TOS 对象存储、讯飞 AIChain、BytePlus TTS）。请确认脑板支持连接 WiFi 并访问外网，
以及官方对长期云 API 调用的限制（如有）。

**EN**: During the exhibition, SoC 1 (brain board) must reach cloud APIs
(Volcano ModelArk/Seedance, TOS object storage, iFlytek AIChain, BytePlus TTS).
Please confirm WiFi + outbound internet on the brain board, and any official
limits on sustained cloud API calls.

## 6. 音视频接口启用确认 / Audio & video interfaces

**中文**：请确认以下接口在基础开发模式下已启用：
- 相机 RTSP：`rtsp://<ip>:2554/live_head_stereo_left`（我们使用官方
  `get_video_stream.py` 录制参考片段）
- 麦克风：PulseAudio 源 `alsa_input.platform-aw89403_sound.pro-input-0`
  （8 声道 48 kHz，ch5-6 主拾音），本机 unix socket / 远程 TCP 4713
- 音频播放：`/aimdk_5Fmsgs/srv/PlayAudioFile`、`/aimdk_5Fmsgs/srv/StopAudioPlay`
- 播放状态话题：`/aima/hal/audio/play_state`

**EN**: Please confirm these interfaces are enabled under Basic developer mode:
- Camera RTSP: `rtsp://<ip>:2554/live_head_stereo_left` (we use the official
  `get_video_stream.py` to record reference clips)
- Mic: PulseAudio source `alsa_input.platform-aw89403_sound.pro-input-0`
  (8 ch / 48 kHz, ch5-6 main pickup), local unix socket / remote TCP 4713
- Playback: `/aimdk_5Fmsgs/srv/PlayAudioFile`, `/aimdk_5Fmsgs/srv/StopAudioPlay`
- Playback state topic: `/aima/hal/audio/play_state`

## 7. 云台轨迹与自定义上肢关节（备用项）/ Gimbal trajectory & custom upper joints (backlog)

**中文**：展会演示目前只用预设动作。备用的扩展项请一并告知：
- 云台轨迹输入格式（如 BIPED_GIMBAL 303 相关说明）
- 6 个自定义上肢关节的名称列表（如后续需要 MC 高层自定义动作，我们会先单独
  确认再使用）

**EN**: The demo currently uses preset motions only. For a possible later
extension, please also provide:
- Gimbal trajectory input format (e.g. BIPED_GIMBAL 303 documentation)
- The names of the 6 custom upper joints (we would confirm separately before
  using any MC high-level custom motion)

---

## 发送清单 / What to send with this ticket

1. 本工单（去掉本行起的说明区块）This ticket (drop the note blocks from here down)
2. 机器人 SN：`QY02BGH2609100103`
3. SDK 版本：门户 v1.0.0.0；git v0.9.4.7（如有版本截图更佳）
4. 展会时间：约 2026-10-19 彩排（如需优先处理）

（此文件为草稿，发送前请按实际情况删改。）
