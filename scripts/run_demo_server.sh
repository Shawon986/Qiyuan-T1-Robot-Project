#!/usr/bin/env bash
# Start the exhibition demo server (LIVE generation, v2 pages served)
set -o pipefail
cd "/mnt/d/Qiyuan T1 Robotics project/Qiyuan-T1-Robot-Project"
source /opt/ros/humble/setup.bash
source ~/t1_workspaces/primebot_sdk_v1.0.0.0/install/setup.bash
source install/setup.bash
export PYTHONPATH="$(pwd)/apps/demo_ui:$(pwd)/apps/seedance:$(pwd)/apps/conversation"
exec python3 -m demo_ui.server --host 0.0.0.0 --port 8765 --pages "$(pwd)/exhibition/exhibition"
