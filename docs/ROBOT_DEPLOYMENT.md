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
4. **SSH in** (key/password from PrimeBot after-sales — ticket sent 2026-10-10):
   `ssh -i ./<机器人SN>_soc0/id_ed25519 run@<板卡IP>`
   (Run from Windows Git Bash — no WSL needed; the deploy script also runs there.)
5. **Developer Mode** (official): `yamo mode edit`

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

## Open items still with PrimeBot

- Firmware version ↔ SDK baseline (portal v1.0.0.0 vs repo v0.9.4.7)
- Gimbal trajectory input format (BIPED_GIMBAL 303) + 6 custom-upper joint names
- AIChain Cantonese TTS voiceId (iFlytek team) — BytePlus voice is the working leg
