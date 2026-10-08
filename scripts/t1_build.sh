#!/usr/bin/env bash
# T1 SDK colcon build (run as regular user)
set -o pipefail
cd "$HOME/t1_workspaces/primebot_sdk"
source /opt/ros/humble/setup.bash
LOG="$HOME/t1_workspaces/build.log"
echo "Build started $(date)" | tee "$LOG"
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release >> "$LOG" 2>&1
RC=$?
tail -30 "$LOG"
echo "BUILD_EXIT=$RC"
