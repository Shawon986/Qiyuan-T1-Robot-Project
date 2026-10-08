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

## Status & next steps

| Item | Status |
|---|---|
| WSL Ubuntu 22.04 + ROS 2 Humble | ✅ verified |
| TUNA/USTC mirror plumbing (apt, rosdep, pip) | ✅ permanent |
| T1 SDK pinned build + interface verification | ✅ 4 packages, 53 interfaces |
| Project GitHub repo | ✅ initialized, populated |
| WSL networking | ⚠️ NAT stable; Windows reboot recommended to clear mirrored-mode crash residue |
| usbipd-win + WSL usbip tools | ✅ installed & ready (5.3.0; vhci-hcd loaded) |
| Robot SSH credentials | ⏳ awaiting user request to PrimeBot after-sales |
| Firmware ↔ SDK compatibility confirmation | ⏳ awaiting PrimeBot |
| Developer Mode activation | ⏳ Day 5 (needs credentials + physical access) |
| Monitoring app development | next (Day 6 target) |
