# 启元 T1 项目 — 执行日志（全部步骤详细记录 · 中文版）

> 本项目每一步操作的权威记录。本文件的 Word 版本位于
> `D:\Qiyuan T1 Robotics project\Qiyuan_T1_执行日志.docx`（每次更新后重新生成）。
> 开始时间：2026-10-08。

## 2026-10-08 — 阶段 1：WSL 与 Ubuntu 检查

1. 检查 WSL：版本 **3.0.1.0**，内核 6.18.40.1，WSLg 1.0.79，发行版 `Ubuntu-22.04`（WSL2）。
2. 检查发行版内部：**Ubuntu 22.04.5 LTS (jammy)**，x86_64，默认用户 `shawon986`，
   磁盘可用 954 GB，内存 7.7 GiB，locale 为 `C.UTF-8`。
3. 注意到警告：Windows 配置了本地代理（`127.0.0.1:17890`），未镜像到 WSL NAT 模式。

## 2026-10-08 — 阶段 2：安装 ROS 2 Humble Desktop

1. **网络诊断**（本网络屏蔽 `packages.ros.org` 和 `raw.githubusercontent.com`；Ubuntu 官方源与国内镜像可用）：
   - `mirrors.tuna.tsinghua.edu.cn/ros2/ubuntu` → HTTP 200
   - `mirrors.ustc.edu.cn/ros2/ubuntu` → HTTP 200
   - `mirrors.ustc.edu.cn/rosdistro/*` 与清华 rosdistro → HTTP 200
   - `raw.githubusercontent.com` → 连接被重置
2. 安装前置依赖：`locales`、`software-properties-common`、`curl`、`gnupg2`、`lsb-release`；
   生成并设置 `en_US.UTF-8`；启用 universe 软件源。
3. **ROS 2 apt 软件源 — 切换到清华镜像**（官方地址不可达）：
   - 密钥：`curl -fsSL https://mirrors.tuna.tsinghua.edu.cn/rosdistro/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg`
   - 源：`deb [arch=amd64 signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] https://mirrors.tuna.tsinghua.edu.cn/ros2/ubuntu jammy main` → `/etc/apt/sources.list.d/ros2.list`
4. 安装：`ros-humble-desktop` + `ros-dev-tools` + `python3-rosdep` — 共 **273 个软件包**。
5. **rosdep**（GitHub 被屏蔽，因此）：
   - `ROS_DISTRO_INDEX_URL=https://mirrors.ustc.edu.cn/rosdistro/index-v4.yaml`（已写入 `~/.bashrc`）
   - `/etc/ros/rosdep/sources.list.d/20-default.list` 从中科大镜像获取，全部 URL 改写到
     `https://mirrors.ustc.edu.cn/rosdistro/...`；删除过时的 `fuerte` 行。
   - `rosdep update` → 成功，退出码 0。
6. pip 系统配置 `/etc/pip.conf` → 清华 PyPI 镜像。
7. `~/.bashrc` 添加：`source /opt/ros/humble/setup.bash` + `export ROSDISTRO_INDEX_URL=...`。
8. **验证**：`ros2 doctor` → 5 项检查全部通过；`demo_nodes_cpp talker` 正常发布 4 条消息；
   `ros2`、`rviz2`、`colcon` 均可用。

## 2026-10-08 — 阶段 3：手册研读与项目计划

1. 提取《Qiyuan_T1_Complete_Engineering_Guide.docx》全文（约 900 KB，30 章）并梳理结构。
2. 记录关键事实：SDK 固定提交 `fe2e186c867391ec78b301accdc91f0260ad0ff3`；仓库标签 v0.9.4.7；
   门户卡片 v1.0.0.0（两者不视为等价）；`aimdk_msgs` 1.0.0；主板默认 IP `10.1.1.100`/`.101`；
   SSH 账号形式 `run@<IP>`，凭据仅由售后提供；开发者模式通过 `yamo mode edit` 切换；SDK 本身不需要任何 API 密钥。
3. 生成《Qiyuan_T1_Project_Setup_Guide.docx》：账号/激活、安装命令、验证清单与 11 天计划（10 月 9 日–19 日）。

## 2026-10-08 — 阶段 4：T1 SDK 环境搭建（计划第 2 天）

1. root 安装（全部成功）：
   - `python3-colcon-common-extensions python3-dev python3-pip ros-humble-rosidl-default-generators ros-humble-rosidl-default-runtime`
   - `cmake build-essential pkg-config libavcodec-dev libavformat-dev libavutil-dev libswscale-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev libyaml-cpp-dev`
   - 验证：colcon 22 个扩展、cmake 3.22.1、g++ 11.4.0、pip 22.0.2、20 个 rosidl 软件包。
2. UDP 套接字缓冲区（厂商建议 24 MiB）：
   - `/etc/sysctl.d/99-primebot-sdk.conf`：`net.core.rmem_max = 25165824`、`net.core.wmem_max = 25165824` → 已生效。
3. Python 依赖（普通用户）：`pip install --user nanobind numpy opencv-python` →
   nanobind 3.1.0、numpy 2.2.6、cv2 5.0.0（经清华 PyPI 镜像）。
4. WSL 镜像网络模式（`C:\Users\shawo\.wslconfig` → `networkingMode=mirrored`）：初次生效
   （eth0 镜像宿主机局域网 192.168.0.19/23），清华与 GitCode 仍可达。

## 2026-10-08 — 阶段 5：SDK 克隆与编译（计划第 3 天）

1. `git ls-remote https://gitcode.com/primebot/t1-sdk.git HEAD` → `fe2e186c867391ec78b301accdc91f0260ad0ff3`（与手册一致）。
2. 克隆到 `~/t1_workspaces/primebot_sdk`（73 MB），检出固定提交
   （提交信息："启元 T1 四足/双足人形机器人 ROS2 二次开发 SDK v0.9.4.7"）。
3. 扫描 CMake 外部下载指令（FetchContent/ExternalProject/GIT_REPOSITORY）→ 无，全部随仓库附带
   （examples 目录：`cpp`、`opencv`、`python`、`ruckig_for_primebot`）。
4. **编译**：`colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release` →
   **Summary: 4 packages finished [9 分 41 秒]，退出码 0**
   （aimdk_msgs、aimdk_examples_cpp、aimdk_opencv、ruckig_for_primebot）。（用户已批准执行厂商构建代码。）
5. **编译后验证**（全部通过）：
   - `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`
   - `FASTRTPS_DEFAULT_PROFILES_FILE` / `FASTDDS_DEFAULT_PROFILES_FILE` →
     `install/aimdk_msgs/share/aimdk_msgs/config/fastdds_profiles.xml`
   - `ros2 interface show aimdk_msgs/msg/Bms` 与 `srv/PlayTts` → 完整定义（含 TtsPriorityLevel 枚举）
   - **53 个 aimdk_msgs 接口**可用。

## 2026-10-08 — 阶段 6：网络故障处理与项目仓库建立

1. **镜像网络模式不稳定**：WSL 报 `CreateInstance/CreateVm/ConfigureNetworking/0x8007054f`，
   回退到 "None"（无网络）。重试复现 — 与本地代理/VPN 驱动冲突。**回退 NAT 模式**（删除 `.wslconfig`）
   → 清华/GitCode 连通恢复；WSL 内 `github.com` 仍不可达（符合预期）。
   - **机器人连接方案变更**（方案 B）：第 4 天通过 `usbipd-win` 将 USB 网卡直通进 WSL，
     或在代理软件关闭时重试镜像模式。计划文档已更新。
   - WSL 备注：建议 Windows 重启以彻底清除镜像模式崩溃的残留状态。
2. **GitHub 工作流决定**：GitHub 从 Windows git 可直接访问。本仓库所有 `git` 操作在 Windows 侧执行
   （Git Bash）；ROS 编译在 WSL 内执行。
3. **项目仓库初始化**：`D:\Qiyuan T1 Robotics project\Qiyuan-T1-Robot-Project`
   - `git init -b main`；`git remote add origin https://github.com/Shawon986/Qiyuan-T1-Robot-Project.git`（仓库原为空）
   - 添加：`README.md`、`.gitignore`、`docs/`（计划 docx + 本日志）、`scripts/`（环境搭建脚本，便于复现）。

## 2026-10-08 — 阶段 7：USB 直通工具（第 4 天准备）

1. 通过 winget 在 Windows 安装 **usbipd-win 5.3.0**（包 `dorssel.usbipd-win`，校验安装包哈希通过）。
2. 安装 **WSL 侧 usbip 工具**：`linux-tools-generic` + `hwdata`（apt）→ `/usr/bin/usbip` 可用。
3. 在 WSL 中加载 `vhci-hcd` 内核模块 — 虚拟 USB 主机控制器就绪。
4. 第 4 天使用方法（插入 USB 网卡后）：
   - Windows：`usbipd list` → 找到 BUSID → `usbipd bind --busid <BUSID>` → `usbipd attach --wsl`
   - WSL：网卡显示为 Linux 网卡（如 `eth1`）→ 在其上配置 `10.1.1.99/24`（计划第 5 节）。

## 2026-10-08 — 阶段 8：开发者门户与 API 文档研读

1. 研读 **dev.primebot.com**：登录方式为 **AtomGit OAuth**；`/download` 页面按机型提供资料包
   （T1 与 Q1 分区），提供 PrimeConsole 桌面调试客户端，并链接 **atomgit.com/primebot** 与
   **skillhub.primebot.com**。
2. **下载**到 `D:\Qiyuan T1 Robotics project\downloads\`：
   - `sdk_t1-v1.0.0.0.zip`（13.2 MB，10 月 7 日）— 门户 T1 SDK
   - `T1_URDF.zip`（18.3 MB）
   - （记录备用：docker 工具链包 — `docker_arm_native_arm.zip`、`docker_x86_native_x86.zip`、
     `docker_x86_cross_arm-v1.0.0.zip`；Q1 资料包为另一机型。）
3. **从 AtomGit 克隆**：`t1-urdf`（66 MB — meshes/urdf/config/launch，用于仿真）与 `qzai-guide`
   （1.6 MB — Q仔消费者体验指南：PrimeBOT APP、唤醒词 你好Q仔/Q仔Q仔）。
4. **关键发现 — 门户 SDK ≠ 固定提交的 git SDK**：对门户压缩包与提交 fe2e186 做 `diff`，
   门户 v1.0.0.0 **更新**：
   - 新增 `aimdk_msgs/agent/msg/AsrResult.msg` → 话题 `/aima/agent/asr_result`
     （is_final、confidence、event_id）— 机器人端 ASR 结果。
   - 新增 ASR 示例（`get_asr_result.py/.cpp`）；音频示例重构（`play_audio_from_pc` /
     `play_audio_from_robot`、`media_role` 参数、机器人端音频路径
     `/robot/software/aimrt_agent/bin/cfg/t1/audio`）。
   - 更新 `接口说明.md`（完整接口手册，含语音识别章节）、Fast DDS 配置、Bms.msg 修正
     （bit 13/14 温度下限修正）。
   - 解压到 `~/t1_workspaces/primebot_sdk_v1.0.0.0/` 备查。**基准版本待 PrimeBot 确认固件后再定**
     — 两个 overlay 均保留。
5. **AIUI 文档链接**（`yuque.com/aiui_open_platform/fqow12/esgax5gboxdq5s07`）：页面报"页面出错了"、
   公开 API 返回 404 — 文档为私有或已迁移。等待用户提供正确链接。
   机器人端 ASR 已内置（`/aima/agent/asr_result`），因此 AIUI 账号可能仅用于自定义语音服务配置。

## 2026-10-08 — 阶段 9：门户 SDK 编译 + t1_monitor 应用（机器人就绪）

1. **门户 SDK v1.0.0.0 编译完成**（`~/t1_workspaces/primebot_sdk_v1.0.0.0`）：4 个包，
   11 分 9 秒，退出码 0。overlay 现在提供 **54 个 aimdk_msgs 接口**（53 + 新增 `agent/msg/AsrResult`）。
2. **t1_monitor 应用**（仓库 `apps/t1_monitor`，ament_python）：BMS/触摸/ASR 订阅（sensor_data QoS）、
   带三重门禁的 TTS 客户端（启用开关 + 确认令牌 + ≤240 字符）、运动永久禁用、launch 文件、
   6 个离线策略单元测试。
3. 基于门户 overlay 编译应用：`colcon build --base-paths apps` → 1 个包，退出码 0。
   离线测试 **6/6 通过**（无需机器人、无需 ROS）。
4. **经验记录（手册原则"schema ≠ 在线发布者"）**：首次冒烟运行报告 BMS/触摸/ASR "存在" —
   那是应用自己的订阅出现在图上。修复 `_log_runtime_graph()` 改用 `count_publishers()`
   （只统计机器人端发布者）与 `service_is_ready()`；`first_contact.sh` 现在先做
   `ros2 topic info -v` 发布者检查再回显。重新编译并复验：正确输出
   `Robot-side publishers: bms=0 touch=0 asr=0; tts_service_ready=False`，无发布者时给出明确警告。
5. 新增 `scripts/first_contact.sh`（第 5 天：证据采集，含发布者检查）与
   `scripts/net_bringup.sh`（第 4 天：USB 网卡静态 IP + ping 测试）。

**PC 侧机器人就绪完成。** 剩余：USB 网卡、PrimeBot SSH 凭据、开发者模式激活（均需用户侧操作）。

## 2026-10-08 — 阶段 10：项目范围确认

1. **与用户确认范围**：仅做应用层开发（不改硬件/固件，保修完好）。四个演示功能：
   (a) 粤语对话（唤醒词 机器人 → 讯飞粤语 ASR → 通义千问 LLM（会话记忆）→ 讯飞粤语 TTS → 扬声器），
   (b) 跟拍（视觉锁定 → 云台跟踪 → 录像），(c) 舞蹈（JSON 时间轴编排预设动作/音乐/灯带/屏幕），
   (d) SeeDance 集成（视频 + 语音提示 → 火山 TOS → SeeDance AI 视频 → 网页状态 → 结果回传机器人）。
2. **架构决策记录**（全部保持在 MC 高层接口）：粤语 ASR/TTS 走讯飞云端（机器人内置 ASR 大概率仅普通话；
   用 SDK 麦克风/音频接口采集与播放）；视频由应用侧从 CaptureJpegImage/RTSP 编码；舞蹈仅用预设动作；
   密钥经环境变量/密钥管理，绝不进代码。
3. **需求清单**：讯飞 APPID/APIKey/APISecret；通义 DashScope 密钥（qwen-long）；火山 TOS AK/SK + 桶；
   SeeDance REST API 规范；PrimeBot 确认项（SSH 凭据、固件↔SDK、云台资源/动作 ID、预设动作列表）。
4. 计划文档已更新（Rev 3：项目定义 + 云端凭据清单 + 第 6–11 天调整）。
   对话/TOS/SeeDance 部分无需机器人即可在 PC 上开发测试。

## 2026-10-08 — 阶段 11：PrimeAgent 技能生态研读（需求已找到）

1. 克隆 AtomGit 组织全部仓库：`q1-dev-guide`、`robot_video_call`、`carry-clothes`、
   `didi_taxi_agent`、`luobodun_game`、`weather_forecast`、`AboutUs`、`arm-native-toolchain`、
   `atomcode-skills`。
2. **PrimeAgent + Lumina**：厂商在机器人上运行的智能体运行时；技能为 Python 应用，
   打包为 `.rpk`，含 `cfg/pkg.yaml` 清单（`user_id, version, sdk_version: "v1.0.0", package_name,
   author, description`）、`main.py` 入口、`src/<pkg>/` 代码、`resource/` 资源。
   入口在机器人上运行（`source /robot/etc/basic_env && source /robot/software/rtsp_server/setup.bash
   && python3 -m <pkg>.app`）。
3. **从 `robot_video_call` 获得的已验证机器人接口**（厂商参考实现）：
   - 摄像头：ROS 话题 `/aima/hal/camera/head_stereo_left_orin`（sensor_msgs/Image）
     + 机器人端 RTSP 服务（`/robot/software/rtsp_server`）；CaptureJpegImage 服务。
   - 麦克风：ROS 话题 `/aima/hal/audio/capture`（`aimdk_msgs/msg/AudioCapture`）。
   - 扬声器：发布 `aimdk_msgs/msg/AudioPlayback`（48 kHz 立体声 PCM，20 ms 分块）或 PlayTts 服务；
     音频焦点服务 `RequestAudioFocus` / `AbandonAudioFocus`；音量/静音服务
     `GetVolume/SetVolume/GetMute/SetMute`；`PlayEmotion` 服务。
   - 网页/控制台模式：Flask/ThreadingHTTPServer 界面 + 媒体桥端口；浏览器媒体经 WebRTC/HTTP。
4. **`carry-clothes` README 揭示的 SDK 能力边界**：SDK **没有**导航接口、没有夹爪、
   没有末端力传感 — 使用视觉伺服 + 预设动作（文中提到 BIPED_LOCOMOTION_WBC 轮式模式）。
5. **参考智能体**：didi_taxi_agent（机器人 ASR + 原生 TTS + 外部 API 密钥文件
   `/home/run/ceshi/runtime/...`）、luobodun_game（复用机器人 ASR 或外部千问 ASR）、
   weather_forecast（Open-Meteo + 机器人 TTS）。
6. **架构决策**：将四个功能实现为 PrimeAgent 技能（官方集成路径 — rpk 包，运行在机器人上），
   同时保留独立 ROS 2 应用路径用于 PC 开发与测试。四个功能均已映射到已验证接口。

## 2026-10-08 — 阶段 12：部署工具链研读（arm-native-toolchain）

1. 通读 `arm-native-toolchain` 完整指南：机器人主板为 **aarch64**（RK / NVIDIA Orin 平台），
   原生运行 ROS 2 Humble。
2. 两种编译路径：在板上用 Docker 做 ARM 原生编译（`native-aarch64-rk` / `native-aarch64-orin`
   镜像，门户可下载）或在 PC 上 x86 交叉编译（`docker_x86_cross_arm`，镜像约 5.4/44.6 GB）。
   可部署产物 = colcon `install/` 目录（tar → scp → source setup.bash）。
3. **我们的应用是纯 Python → 无需编译**；按 video_call 技能所示，机器人已附带
   aarch64 版 site-packages（numpy/opencv）（`/home/run/tennis_coach_t1/vendor/aarch64/site-packages`）。
4. **Windows 换行符警告（3.5 节）**：已按厂商建议在仓库添加 `.gitattributes`，
   强制所有文本文件使用 LF（`*.sh/*.py/*.md/*.yaml/...`），适配 Windows 团队。

## 状态与下一步

| 项目 | 状态 |
|---|---|
| WSL Ubuntu 22.04 + ROS 2 Humble | ✅ 已验证 |
| 清华/中科大镜像（apt、rosdep、pip） | ✅ 永久生效 |
| T1 SDK 固定版本编译 + 接口验证 | ✅ 4 个包、53 个接口 |
| 项目 GitHub 仓库 | ✅ 已初始化并持续提交 |
| WSL 网络 | ⚠️ NAT 稳定；建议 Windows 重启以清除镜像模式残留 |
| usbipd-win + WSL usbip 工具 | ✅ 已安装就绪（5.3.0；vhci-hcd 已加载） |
| 门户 SDK v1.0.0.0 + T1 URDF | ✅ 已下载；门户 SDK 已解压并与 git 版对比（更新：agent/ASR 接口） |
| SDK 基准（门户 vs git） | ⏳ 待 PrimeBot 确认与你的固件匹配的版本 |
| AIUI 文档链接 | ❌ 链接失效（页面错误）— 等待更正链接 |
| 门户 SDK v1.0.0.0 编译 | ✅ 4 个包、54 个接口（含 AsrResult） |
| t1_monitor 应用 | ✅ 已编译 + 6/6 离线测试 + 发布者计数自检 |
| PrimeAgent 技能生态 | ✅ 已研读：技能格式（pkg.yaml/rpk）、摄像头/音频/焦点接口已验证 |
| 机器人 SSH 凭据 | ⏳ 等待用户向 PrimeBot 售后申请 |
| 固件 ↔ SDK 兼容性确认 | ⏳ 等待 PrimeBot |
| 开发者模式激活 | ⏳ 第 5 天（需凭据 + 现场操作） |
| 云端凭据（讯飞/千问/火山） | ⏳ 等待用户在 .env 填写 |
| 监控应用开发 | ✅ 已完成（第 6 天提前完成） |
