# Qiyuan T1 Project — Execution Log (All Steps in Detail)

> Source of truth for every step performed on this project. A `.docx` rendering of this
> file is regenerated at `D:\Qiyuan T1 Robotics project\Qiyuan_T1_Execution_Log.docx`.
> Started: 2026-10-08.

## 2026-10-08 — Phase 1: WSL & Ubuntu verification

1. Checked WSL: version **3.0.1.0**, kernel 6.18.40.1, WSLg 1.0.79, distro `Ubuntu-22.04` (WSL2, stopped).
2. Inspected the distro: **Ubuntu 22.04.5 LTS (jammy)**, x86_64, default user `shawon986`,
   954 GB free disk, 7.7 GiB RAM, locale `C.UTF-8`.
3. Noted warning: Windows has a localhost proxy configured (`127.0.0.1:17890`) not mirrored into WSL NAT.

## 2026-10-08 — Phase 2: ROS 2 Humble Desktop installation

1. **Network diagnosis** (this network blocks `packages.ros.org` and `raw.githubusercontent.com`; Ubuntu archives and Chinese mirrors work):
   - `mirrors.tuna.tsinghua.edu.cn/ros2/ubuntu` → HTTP 200
   - `mirrors.ustc.edu.cn/ros2/ubuntu` → HTTP 200
   - `mirrors.ustc.edu.cn/rosdistro/*` and TUNA rosdistro → HTTP 200
   - `raw.githubusercontent.com` → connection reset
2. Installed prerequisites: `locales`, `software-properties-common`, `curl`, `gnupg2`, `lsb-release`; generated and set `en_US.UTF-8`; enabled universe repo.
3. **ROS 2 apt repository — switched to TUNA mirror** (official endpoint unreachable):
   - Key: `curl -fsSL https://mirrors.tuna.tsinghua.edu.cn/rosdistro/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg`
   - Source: `deb [arch=amd64 signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] https://mirrors.tuna.tsinghua.edu.cn/ros2/ubuntu jammy main` → `/etc/apt/sources.list.d/ros2.list`
4. Installed: `ros-humble-desktop` + `ros-dev-tools` + `python3-rosdep` — **273 packages**, candidate 0.10.0-1jammy.
5. **rosdep** (GitHub blocked, so):
   - `ROS_DISTRO_INDEX_URL=https://mirrors.ustc.edu.cn/rosdistro/index-v4.yaml` (exported in `~/.bashrc`)
   - `/etc/ros/rosdep/sources.list.d/20-default.list` fetched from USTC mirror, all URLs remapped to `https://mirrors.ustc.edu.cn/rosdistro/...`; obsolete `fuerte` line removed.
   - `rosdep update` → clean, exit 0.
6. pip system config `/etc/pip.conf` → TUNA PyPI mirror.
7. `~/.bashrc` additions: `source /opt/ros/humble/setup.bash` + `export ROSDISTRO_INDEX_URL=...`.
8. **Verification**: `ros2 doctor` → all 5 checks passed; `demo_nodes_cpp talker` published 4 messages; `ros2`, `rviz2`, `colcon` present.

## 2026-10-08 — Phase 3: Handbook review & project plan

1. Extracted the full text of `Qiyuan_T1_Complete_Engineering_Guide.docx` (≈900 KB, 30 chapters) and mapped its structure.
2. Key facts recorded: SDK pinned commit `fe2e186c867391ec78b301accdc91f0260ad0ff3`; repo label v0.9.4.7; portal card v1.0.0.0 (NOT equivalent); `aimdk_msgs` 1.0.0; board defaults `10.1.1.100`/`.101`; SSH `run@<IP>` credentials only from after-sales; Developer Mode via `yamo mode edit`; no SDK API keys required.
3. Produced `Qiyuan_T1_Project_Setup_Guide.docx` with accounts/activation, install commands, verification checklist and the 11-day plan (Oct 9–19).

## 2026-10-08 — Phase 4: T1 SDK environment setup (Plan Day 2)

1. Root installs (all succeeded):
   - `python3-colcon-common-extensions python3-dev python3-pip ros-humble-rosidl-default-generators ros-humble-rosidl-default-runtime`
   - `cmake build-essential pkg-config libavcodec-dev libavformat-dev libavutil-dev libswscale-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev libyaml-cpp-dev`
   - Verified: colcon 22 extensions, cmake 3.22.1, g++ 11.4.0, pip 22.0.2, 20 rosidl packages.
2. UDP socket buffers (vendor 24 MiB recommendation):
   - `/etc/sysctl.d/99-primebot-sdk.conf`: `net.core.rmem_max = 25165824`, `net.core.wmem_max = 25165824` → applied.
3. Python deps (user): `pip install --user nanobind numpy opencv-python` → nanobind 3.1.0, numpy 2.2.6, cv2 5.0.0 (via TUNA PyPI).
4. WSL mirrored networking (`C:\Users\shawo\.wslconfig` → `networkingMode=mirrored`): initially worked (eth0 mirrored host LAN 192.168.0.19/23), TUNA + GitCode still reachable.

## 2026-10-08 — Phase 5: SDK clone & build (Plan Day 3)

1. `git ls-remote https://gitcode.com/primebot/t1-sdk.git HEAD` → `fe2e186c867391ec78b301accdc91f0260ad0ff3` (matches handbook).
2. Cloned to `~/t1_workspaces/primebot_sdk` (73 MB), checked out pinned commit (commit message: "启元 T1 四足/双足人形机器人 ROS2 二次开发 SDK v0.9.4.7").
3. Scanned CMake for external downloads (FetchContent/ExternalProject/GIT_REPOSITORY) → none; everything vendored (examples: `cpp`, `opencv`, `python`, `ruckig_for_primebot`).
4. **Build**: `colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release` → **Summary: 4 packages finished [9 min 41 s], exit 0** (aimdk_msgs, aimdk_examples_cpp, aimdk_opencv, ruckig_for_primebot). (User-approved execution of vendor build code.)
5. **Post-build verification** (all passed):
   - `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`
   - `FASTRTPS_DEFAULT_PROFILES_FILE` / `FASTDDS_DEFAULT_PROFILES_FILE` → `install/aimdk_msgs/share/aimdk_msgs/config/fastdds_profiles.xml`
   - `ros2 interface show aimdk_msgs/msg/Bms` and `srv/PlayTts` → full schemas (incl. TtsPriorityLevel enums)
   - **53 aimdk_msgs interfaces** resolvable.

## 2026-10-08 — Phase 6: Networking incident & project repository

1. **Mirrored networking became unstable**: WSL failed with `CreateInstance/CreateVm/ConfigureNetworking/0x8007054f`, falling back to "None" (no network). Reproduced on retry — conflict with the local proxy/VPN driver. **Reverted to NAT mode** (deleted `.wslconfig`) → TUNA/GitCode connectivity restored; `github.com` still unreachable from WSL (expected).
   - **Robot-connectivity plan changed** (Plan B): pass a USB-Ethernet adapter into WSL via `usbipd-win` at Day 4, or retry mirrored mode with the proxy software off. Plan document updated.
   - WSL-side note: VM networking may need a full Windows reboot to fully recover from the mirrored-mode crash.
2. **GitHub workflow decision**: GitHub is reachable from Windows git (direct). All `git` operations for this repo run from Windows (Git Bash); ROS builds run inside WSL.
3. **Project repository initialized** at `D:\Qiyuan T1 Robotics project\Qiyuan-T1-Robot-Project`:
   - `git init -b main`; `git remote add origin https://github.com/Shawon986/Qiyuan-T1-Robot-Project.git` (repo was empty)
   - Added: `README.md`, `.gitignore`, `docs/` (plan docx + this log), `scripts/` (environment setup scripts for reproducibility).

## 2026-10-08 — Phase 7: USB passthrough tooling (Day-4 prep)

1. Installed **usbipd-win 5.3.0** on Windows via winget (package `dorssel.usbipd-win`, installer hash verified).
2. Installed **WSL-side usbip tools**: `linux-tools-generic` + `hwdata` (apt) → `/usr/bin/usbip` present.
3. Loaded the `vhci-hcd` kernel module in WSL — the virtual USB host controller is ready.
4. Day-4 usage (when the USB-Ethernet adapter is plugged in):
   - Windows: `usbipd list` → find BUSID → `usbipd bind --busid <BUSID>` → `usbipd attach --wsl`
   - WSL: the adapter appears as a Linux NIC (e.g. `eth1`) → configure `10.1.1.99/24` on it (Section 5 of plan).

## 2026-10-08 — Phase 8: Developer portal & API docs review

1. **dev.primebot.com** reviewed: login is **AtomGit OAuth**; `/download` page hosts per-model packs (separate T1 and Q1 sections), a PrimeConsole desktop client, and links to **atomgit.com/primebot** + **skillhub.primebot.com**.
2. **Downloaded** to `D:\Qiyuan T1 Robotics project\downloads\`:
   - `sdk_t1-v1.0.0.0.zip` (13.2 MB, dated Oct 7) — portal T1 SDK
   - `T1_URDF.zip` (18.3 MB)
   - (Noted for later: docker toolchain packs — `docker_arm_native_arm.zip`, `docker_x86_native_x86.zip`, `docker_x86_cross_arm-v1.0.0.zip`; Q1 packs are a different robot.)
3. **Cloned from AtomGit**: `t1-urdf` (66 MB — meshes/urdf/config/launch, for simulation) and `qzai-guide` (1.6 MB — Q仔 consumer experience guide: PrimeBOT APP, wake words 你好Q仔/Q仔Q仔).
4. **KEY FINDING — portal SDK ≠ pinned git SDK**: `diff` of the portal zip against commit fe2e186 shows the portal v1.0.0.0 is **newer**:
   - Adds `aimdk_msgs/agent/msg/AsrResult.msg` → topic `/aima/agent/asr_result` (is_final, confidence, event_id) — robot-side ASR results.
   - New ASR examples (`get_asr_result.py/.cpp`); audio examples reworked (`play_audio_from_pc` / `play_audio_from_robot`, `media_role` param, robot-side audio path `/robot/software/aimrt_agent/bin/cfg/t1/audio`).
   - Updated `接口说明.md` (full interface manual incl. 语音识别 section), Fast DDS profile, and minor Bms.msg corrections (bit 13/14 温度下限 fix).
   - Extracted to `~/t1_workspaces/primebot_sdk_v1.0.0.0/` for reference. **Baseline decision pending PrimeBot firmware confirmation** — both overlays kept available.
5. **AIUI docs link** (`yuque.com/aiui_open_platform/fqow12/esgax5gboxdq5s07`): page returns 页面出错了 and the public API 404s — the doc is private/moved. Awaiting a corrected link from the user. Robot-side ASR appears to be built in (`/aima/agent/asr_result`), so an AIUI account may only be needed for custom voice-service configuration.

## 2026-10-08 — Phase 9: Portal SDK build + t1_monitor app (robot-readiness)

1. **Portal SDK v1.0.0.0 built** in `~/t1_workspaces/primebot_sdk_v1.0.0.0`: 4 packages, 11 min 9 s, exit 0. Overlay now exposes **54 aimdk_msgs interfaces** (53 + new `agent/msg/AsrResult`).
2. **t1_monitor app** created in repo `apps/t1_monitor` (ament_python): BMS/touch/ASR subscriptions (qos sensor data), guarded TTS client (enable + confirmation token + ≤240 chars), motion permanently disabled, launch file, 6 offline policy unit tests.
3. Built the app against the portal overlay: `colcon build --base-paths apps` → 1 package, exit 0. Offline tests **6/6 passed** (no robot, no ROS needed).
4. **Lesson recorded (handbook principle "schema ≠ live publisher")**: first smoke run reported BMS/touch/ASR "present" — these were the app's own subscriptions appearing in the graph. Fixed `_log_runtime_graph()` to use `count_publishers()` (robot-side publishers only) and `service_is_ready()`; `first_contact.sh` now runs `ros2 topic info -v` publisher checks before echoing. Rebuilt and re-verified: correct output `Robot-side publishers: bms=0 touch=0 asr=0; tts_service_ready=False` + explicit warning when no publisher is detected.
5. Added `scripts/first_contact.sh` (Day 5: evidence capture incl. publisher checks) and `scripts/net_bringup.sh` (Day 4: USB-NIC static IP + pings).

**Robot-readiness complete on the PC side.** Remaining: physical USB-Ethernet adapter, PrimeBot SSH credentials, Developer Mode activation (all user-side).

## 2026-10-08 — Phase 10: Project scope confirmed

1. **Scope confirmed with the user**: application-layer development only (no hardware/firmware changes, warranty intact). Four demo features: (a) Cantonese conversation (wake word 机器人 → iFlytek Cantonese ASR → Qwen LLM with session memory → iFlytek Cantonese TTS → speaker), (b) follow-and-film (vision lock → gimbal track → video record), (c) dancing (JSON timeline over preset motions/music/LED/screen), (d) SeeDance integration (video + voice prompt → Volcano TOS → SeeDance AI video → web status → result to robot).
2. **Architecture decisions recorded** (keeps everything on MC high-level interfaces): Cantonese ASR/TTS via iFlytek cloud (robot onboard ASR likely Mandarin-only; robot mic/audio SDK interfaces used for capture/playback); video encoded app-side from CaptureJpegImage/RTSP; dancing uses preset motions only; secrets via env/secret store.
3. **Requirements collected**: iFlytek APPID/APIKey/APISecret; Qwen DashScope key (qwen-long); Volcano TOS AK/SK + bucket; SeeDance REST API spec; PrimeBot confirmations (SSH creds, firmware↔SDK, gimbal resource/action IDs, preset motion list).
4. Plan document updated (Rev 3: project definition + cloud credential list + revised Days 6–11). Conversation/TOS/SeeDance work is PC-testable without the robot.

## 2026-10-08 — Phase 11: PrimeAgent skill ecosystem review (requirements found)

1. Cloned the full AtomGit org: `q1-dev-guide`, `robot_video_call`, `carry-clothes`, `didi_taxi_agent`, `luobodun_game`, `weather_forecast`, `AboutUs`, `arm-native-toolchain`, `atomcode-skills`.
2. **PrimeAgent + Lumina**: the vendor's agent runtime on the robot; skills are Python apps packaged as `.rpk` with a `cfg/pkg.yaml` manifest (`user_id, version, sdk_version: "v1.0.0", package_name, author, description`), a `main.py` entrypoint, `src/<pkg>/` code, `resource/` assets. Entrypoint runs on the robot (`source /robot/etc/basic_env && source /robot/software/rtsp_server/setup.bash && python3 -m <pkg>.app`).
3. **Verified robot interfaces from `robot_video_call`** (vendor reference implementation):
   - Camera: ROS topic `/aima/hal/camera/head_stereo_left_orin` (sensor_msgs/Image) + robot-side RTSP server (`/robot/software/rtsp_server`); CaptureJpegImage service.
   - Microphone: ROS topic `/aima/hal/audio/capture` (`aimdk_msgs/msg/AudioCapture`).
   - Speaker: publish `aimdk_msgs/msg/AudioPlayback` (48 kHz stereo PCM, 20 ms chunks) or PlayTts service; audio-focus services `RequestAudioFocus` / `AbandonAudioFocus`; volume/mute services `GetVolume/SetVolume/GetMute/SetMute`; `PlayEmotion` service.
   - Web/console pattern: Flask/ThreadingHTTPServer UI + media bridge ports; browser media over WebRTC/HTTP.
4. **SDK capability boundaries from `carry-clothes` README**: NO navigation interface, NO gripper, NO end-effector force sensing in the SDK — use vision servoing + preset motions (BIPED_LOCOMOTION_WBC rolling mode noted).
5. **Reference agents**: didi_taxi_agent (robot ASR + native TTS + external API key file `/home/run/ceshi/runtime/...`), luobodun_game (reuses robot ASR or external Qwen ASR), weather_forecast (Open-Meteo + robot TTS).
6. **Architecture decision**: implement our four features as a PrimeAgent skill (official integration path — rpk package, runs on robot) while keeping the standalone ROS 2 app path for PC development and testing. All four features map to verified interfaces now.

## 2026-10-08 — Phase 12: Deployment toolchain review (arm-native-toolchain)

1. Read the full `arm-native-toolchain` guide: robot boards are **aarch64** (RK / NVIDIA Orin platforms), running ROS 2 Humble natively.
2. Two build paths: ARM-native compile ON the board via Docker (`native-aarch64-rk` / `native-aarch64-orin` images from the portal) or x86 cross-compile from our PC (`docker_x86_cross_arm`, image ~5.4/44.6 GB). Deployable artifact = colcon `install/` dir (tar → scp → source setup.bash).
3. **Our app is Python-only → no compilation needed**; robot already ships vendored aarch64 site-packages (numpy/opencv) per the video_call skill (`/home/run/tennis_coach_t1/vendor/aarch64/site-packages`).
4. **Windows CRLF warning (section 3.5)**: added `.gitattributes` to the repo forcing LF for all text files (`*.sh/*.py/*.md/*.yaml/...`), per the vendor's recommendation for Windows-based teams.

## 2026-10-08 — Phase 13: SeeDance API identified from the developer's web UI

1. User's developer delivered `web/index.html` (79 KB) — a web UI for the Seedance video-generation model.
2. Extracted the real API: Seedance runs on **BytePlus ModelArk** (`https://ark.ap-southeast.bytepluses.com/api/v3`);
   endpoints `POST /contents/generations/tasks` (submit) and `GET /contents/generations/tasks/{id}` (status);
   auth `Authorization: Bearer <API Key>`; tiers Seedance 2.5 / 2.0-fast / 2.0-mini (require console activation).
3. The page needs a forwarder for browser CORS: online hosted version https://apivmorai.com/seedance/ or local
   `node proxy.mjs` (not yet delivered; pending from the developer). The robot-side Python client needs neither —
   it calls Ark server-side.
4. API key handling: web page stores it in browser session/local storage (entered via UI); robot side reads
   `SEEDANCE_API_KEY` from `D:\Qiyuan T1 Robotics project\.env`.

## 2026-10-08 — Phase 14: SeeDance API validated end-to-end (live key, user-approved test)

1. Probed the Ark API with the real key (read-only): task list 200; `/contents/generations/assets` exists but is
   not the documented upload path (JSON-only, internal errors); **Files API** (`POST /api/v3/files`, Bearer,
   multipart) works — uploaded test images got `file-...` ids with ~7-day expiry.
2. **User-approved paid test (minimal)**: submitted 3 generation tasks —
   (a) text-only → **succeeded** with `content.video_url` (TOS-signed mp4);
   (b) `file://` reference → rejected InvalidParameter;
   (c) bare file id → rejected;
   (d) inline base64 data-URI image as first_frame → **succeeded**.
3. **Validated contract** (recorded in SEEDANCE_DESIGN.md): images can be inline base64; videos/audio require a
   public URL or `asset://` (CreateAsset needs AK signing + public URL — so robot videos need a brief public
   hosting step: developer's inbox or BytePlus Object Storage). Cost of the test tasks: a few cents.
4. Next: build the Python client package (`apps/seedance`) — submit/poll/result + video-upload adapter
   (inbox or TOS, pending final choice with the developer).

## 2026-10-08 — Phase 15: seedance client package built (Option B: BytePlus Object Storage)

1. User chose **Option B** for hosting robot-recorded videos: BytePlus Object Storage (same account as ModelArk).
2. Built `apps/seedance` (ament_python): `config.py` (env/.env loader, testable), `client.py` (validated
   payloads + submit/get/wait + fail-closed ArkError), `storage.py` (boto3 S3-compatible TOS upload +
   pre-signed URL, lazy boto3 import), `pipeline.py` (upload → submit → poll → result), `main.py` CLI
   (`seedance run --prompt ... --video x.mp4`).
3. Installed boto3 1.43.109 (user, TUNA mirror). **10/10 offline tests passed**; colcon build:
   2 packages (seedance + t1_monitor), 0 errors.
4. Pending for live video-path test: user fills TOS_ACCESS_KEY/TOS_SECRET_KEY/TOS_BUCKET/TOS_ENDPOINT in `.env`.

## Status & next steps

| Item | Status |
|---|---|
| WSL Ubuntu 22.04 + ROS 2 Humble | ✅ verified |
| TUNA/USTC mirror plumbing (apt, rosdep, pip) | ✅ permanent |
| T1 SDK pinned build + interface verification | ✅ 4 packages, 53 interfaces |
| Project GitHub repo | ✅ initialized, populated |
| WSL networking | ⚠️ NAT stable; Windows reboot recommended to clear mirrored-mode crash residue |
| usbipd-win + WSL usbip tools | ✅ installed & ready (5.3.0; vhci-hcd loaded) |
| Portal SDK v1.0.0.0 + T1 URDF | ✅ downloaded; portal SDK extracted & diffed vs git (newer: agent/ASR interfaces) |
| SDK baseline (portal vs git) | ⏳ confirm with PrimeBot which matches your firmware |
| AIUI docs link | ❌ broken (page error) — awaiting corrected link |
| Portal SDK v1.0.0.0 built | ✅ 4 packages, 54 interfaces (incl. AsrResult) |
| t1_monitor app | ✅ built + 6/6 offline tests + honest publisher-count introspection |
| PrimeAgent skill ecosystem | ✅ reviewed: skill format (pkg.yaml/rpk), verified camera/audio/focus interfaces |
| Robot SSH credentials | ⏳ awaiting user request to PrimeBot after-sales |
| Firmware ↔ SDK compatibility confirmation | ⏳ awaiting PrimeBot |
| Developer Mode activation | ⏳ Day 5 (needs credentials + physical access) |
| Monitoring app development | next (Day 6 target) |
