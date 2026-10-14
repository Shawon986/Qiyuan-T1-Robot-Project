# Robot On-Site Deployment Checklist (Days 4–5)

Robot arrived 2026-10-10. Software is complete and verified on the PC — this
checklist covers bringing the exhibition demo live on the robot.

## Day 1 — Physical + access

1. **Network**: the robot supports WiFi (confirmed with the user 2026-10-11) —
   connect the robot to the same WiFi as the exhibition PC (via the PrimeBOT APP
   if not already configured; the robot was registered with IP `10.1.1.100`).
   No cable needed. (Fallback if WiFi is unreliable on-site: USB-C gigabit
   Ethernet adapter RTL8153 + Cat6 — usbipd already installed on the PC.)
2. **Power on** the robot.
3. **Find the board IP**: check the PrimeBot portal / APP for the registered IP,
   or `ping 10.1.1.100` (board defaults `10.1.1.100`/`.101`).
4. **SSH in** — keys RECEIVED 2026-10-11 (robot SN `QY02BGH2609100103`):
   `D:\Qiyuan T1 Robotics project\启元机器人二次开发密钥SN：QY02BGH2609100103\QY02BGH2609100103_soc0\id_ed25519` (soc0; soc1 also present — try soc1 if soc0 is rejected).
   Brain board default IP `10.1.1.101` (MC board `10.1.1.100`); run from Windows Git Bash:
   `ssh -i "D:\Qiyuan T1 Robotics project\启元机器人二次开发密钥SN：QY02BGH2609100103\QY02BGH2609100103_soc0\id_ed25519" run@10.1.1.101`
5. **Developer Mode** — OFFICIAL: via the phone APP (not SSH): APP connected →
   Settings → 开发者功能 → read the notice → 开发者模式 → **基础开发模式 (Basic)**
   → 保存配置 → **power-cycle the robot** for it to take effect.
   ⚠️ The notice states enabling the developer feature voids warranty — CONFIRM
   with PrimeBot after-sales whether Basic mode is exempt before enabling
   (user's hard constraint: warranty intact).

## Day 1 — Robot checks (run via SSH, record results)

| # | Check | Command | Expect |
|---|---|---|---|
| 1 | Disk/SD state | `df -h` | brain board free space; SD mount |
| 2 | Topics enabled | `ros2 topic list -t` | `/aima/hal/camera/head_stereo_left_orin`, `/aima/hal/audio/capture` |
| 3 | Camera capture | `python3 examples/python/get_video_stream.py --camera_id head_stereo_left --robot_ip <IP> --capture_seconds 5.0` | 5s mp4 saved; check orientation |
| 4 | Mode (biped?) | `ros2 service call /aimdk_5Fmsgs/srv/GetMcAction ...` | biped → `CAMERA_FLIP_180=1` (CONFIRMED on-site 2026-10-11: robot display shows 180°-rotated view in biped; flip already enabled in .env). If the robot runs quadruped, re-check orientation and set 0 if correct |
| 5 | Internet | `curl -sI https://ark.ap-southeast.bytepluses.com/api/v3` | 2xx/3xx → direct cloud OK |
| 6 | PrimeConsole | open console → device online → camera preview + record button | note where recordings land |
| 7 | Capture tool env | `python3 -c "import cv2, rclpy, aimdk_msgs"` (after sourcing ROS + SDK setups) | all import ok — the official capture tool needs all three; pip install opencv-python if cv2 missing |

## Day 2 — Deploy the demo

```bash
# from the PC (Git Bash / WSL), repo scripts/
bash scripts/deploy_to_robot.sh 10.1.1.100 ./T1-XXXX_soc0
```

This copies apps + page + fallback videos + `.env` (chmod 600) + a board-local
`ark-config.js` (robotUrl loopback) and installs `requirements-robot.txt`.

Start on the board:
```bash
ssh -i ./T1-XXXX_soc0/id_ed25519 run@10.1.1.100 \
  'setsid bash /home/user/qiyuan-demo/run_demo_robot.sh > /tmp/qiyuan-demo.log 2>&1 < /dev/null &'
```

Open the page on the exhibition PC: `http://<board-ip>:8766/v2-aurora-flow.html`

## Day 2 — Live loop test (the money shot)

1. Visitor speaks (Mandarin or Cantonese) → robot answers Cantonese ✅
2. Video request → wait phrase → official RTSP capture (4–5 s) → cloud → page
   plays the 15 s result (~3 min on 2.0-fast)
3. If a task fails with `OutputAudioSensitiveContentDetected` → retry (transient
   policy false-positive; a slightly different prompt passes)
4. Biped mode → `CAMERA_FLIP_180=1` in the board `.env`

## Audio playback & capture — robot-confirmed facts

Cross-checked 2026-10-14 against the official 接口说明.md AND the developer's
on-robot framework (PrimeBuddy). The app now handles all of this automatically.

**Playback (`demo_ui/robot_audio.py`, official PlayAudioFile service):**

- `file_path` = **directory**, `file_name` = filename (official Python example:
  `file_path:=/robot/software/aimrt_agent/bin/cfg/t1/audio`, `file_name:=小星星.wav`).
- The audio service runs on **SoC 0** and reads files from SoC 0's disk. The app
  scp's each reply to `/tmp/qiyuan-demo.<rand>/` on SoC 0 (inter-board SSH,
  user `run@10.1.1.100`, `ROBOT_SSH_*` in `.env`; `ROBOT_AUDIO_UPLOAD=auto`
  turns it on when running on the robot) and cleans up afterwards.
- Robot format: **24 kHz mono PCM16 WAV** (the official example's own format).
  Our TTS legs output 16 kHz PCM (AIChain) or mp3 (BytePlus) → converted with
  **ffmpeg** on the board (`apt install ffmpeg`).
- Success = header `code == 0` OR `status == SUCCESS`.
- Playback is verified via `/aima/hal/audio/play_state` events (start within
  8 s, natural end); failures are warnings only.
- Fallback playback path if PlayAudioFile misbehaves: **TCP :6001**
  (接口说明.md §2.2.1.4, PulseAudio simple-protocol; official
  `play_audio_from_pc.py` loads the module over SSH; WAV auto-resampled to
  48 kHz mono).

**Capture (`conversation/mic_capture.py`, official record_audio.py pattern):**

- Robot mic = 8-channel 48 kHz S16LE PulseAudio source
  `alsa_input.platform-aw89403_sound.pro-input-0`; **ch5-6** are the main
  pickup channels (mixed mono, ×10 gain — exactly what the official example's
  `mic_mono.wav` does), resampled to 16 kHz for ASR.
- On the robot: PulseAudio unix socket (no module loading). From the PC:
  TCP :4713 (needs `module-native-protocol-tcp` on the robot — run the
  official `record_audio.py` example once over SSH to load it).
- Robot-day voice loop: `python3 -m conversation.main --listen` (continuous:
  capture → ASR → LLM → TTS → PlayAudioFile → re-arm; Ctrl+C stops).
  `--mic 6` is the one-shot variant for testing. Safe by construction: replies
  only on wake-word transcripts and never captures while the robot is
  speaking (reply duration + quiet margin), so the robot can't hear itself.
  `MIC_PULSE_SERVER` env overrides the endpoint.
- Plan B (from the developer's framework, reverse-engineered, UNVERIFIED on
  this robot): subscribe `/agent/process_audio_output` (stream_id 0, VAD
  states) + `/aima/agent/interaction_state` — the official agent's processed
  audio with VAD; may replace TCP capture if the PulseAudio route is blocked.
- The robot's native wake word is **元仔元仔** — added to `WAKE_WORDS` in
  `.env` (visitors will use it naturally).

**⚠️ Do not run PrimeBuddy (the developer's voice-skill framework) at the
same time as our demo** — it switches the official agent to `only_voice` mode
and owns audio playback; concurrent use causes agent-mode and audio conflicts.

## Open items still with PrimeBot

- Firmware version ↔ SDK baseline (portal v1.0.0.0 vs repo v0.9.4.7)
- Gimbal trajectory input format (BIPED_GIMBAL 303) + 6 custom-upper joint names
- AIChain Cantonese TTS voiceId (iFlytek team) — BytePlus voice is the working leg
