# Qiyuan T1 Robot Project

Secondary development project for the **Qiyuan / PRIMEBOT T1** transformable quadruped/bipedal robot.

## Stack & baseline

| Item | Value |
|---|---|
| Host | Windows 11 + WSL2, distro `Ubuntu-22.04` (jammy) |
| ROS | ROS 2 **Humble** Desktop (`ros-humble-desktop` + `ros-dev-tools`) |
| Middleware | `rmw_fastrtps_cpp` (Fast DDS), SDK-managed profile |
| SDK | PRIMEBOT `t1-sdk` from **gitcode.com/primebot/t1-sdk.git**, pinned commit `fe2e186c867391ec78b301accdc91f0260ad0ff3` (repo label v0.9.4.7) |
| Interfaces | `aimdk_msgs` 1.0.0 — 53 messages/services/actions |
| SDK workspace | WSL: `~/t1_workspaces/primebot_sdk` (built & verified) |
| Robot LAN | MC board `10.1.1.100`, brain board `10.1.1.101`, PC `10.1.1.99/24` (defaults — confirm actual) |

## Repository layout

```
Qiyuan-T1-Robot-Project/
├── README.md              # this file
├── docs/                  # plan, execution log, guides
├── scripts/               # setup/build helper scripts (reproducible environment)
├── apps/                  # our ROS 2 application packages (coming)
└── evidence/              # test evidence packs (SHA, firmware, IPs, QoS, logs)
```

## Every shell needs

```bash
source /opt/ros/humble/setup.bash
source ~/t1_workspaces/primebot_sdk/install/setup.bash
```

## Key references

- Handbook: `D:\Qiyuan T1 Robotics project\Qiyuan_T1_Complete_Engineering_Guide.docx` (30 chapters, source-led)
- Plan: `docs/Qiyuan_T1_Project_Setup_Guide.docx`
- Detailed step-by-step record: `docs/EXECUTION_LOG.md` (+ generated `.docx`)
- Vendor SDK: https://gitcode.com/primebot/t1-sdk

## Safety first (from the handbook)

- Inspect before you invoke — never "test connectivity" with motion commands.
- Developer Mode is enabled by an authorized operator (`yamo mode edit` → develop → basic → reboot).
- Low-level joint control requires a dedicated physical test plan + PrimeBot confirmation.
- Never store SSH credentials or API keys in code/logs.
