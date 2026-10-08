#!/usr/bin/env bash
# Day 5 - FIRST CONTACT with the robot (read-only discovery + evidence capture).
# Run inside WSL AFTER: wired link is up (net_bringup.sh), Developer Mode is
# activated (yamo mode edit -> develop -> basic) and the robot was rebooted.
# Usage: bash first_contact.sh [sdk_path]   (defaults to the portal v1.0.0.0 overlay)
set -o pipefail

SDK=${1:-$HOME/t1_workspaces/primebot_sdk_v1.0.0.0}
source /opt/ros/humble/setup.bash
source "$SDK/install/setup.bash"

OUT="$HOME/t1_workspaces/evidence/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"
LOG="$OUT/discovery.log"

{
  echo "=== network ==="
  ip -br addr
  ip -br link
  echo "=== DDS environment ==="
  printenv ROS_DOMAIN_ID RMW_IMPLEMENTATION FASTRTPS_DEFAULT_PROFILES_FILE FASTDDS_DEFAULT_PROFILES_FILE
  echo "=== nodes ==="
  ros2 node list
  echo "=== topics (typed) ==="
  ros2 topic list -t
  echo "=== services (typed) ==="
  ros2 service list -t
  echo "=== BMS publisher check ==="
  ros2 topic info -v /aima/hal/bms/state
  echo "=== touch publisher check ==="
  ros2 topic info -v /aima/hal/touch/state
  echo "=== ASR publisher check ==="
  ros2 topic info -v /aima/agent/asr_result
  echo "=== BMS one-shot (5 s timeout) ==="
  timeout 5 ros2 topic echo /aima/hal/bms/state --once
  echo "=== touch one-shot (5 s timeout) ==="
  timeout 5 ros2 topic echo /aima/hal/touch/state --once
  echo "=== ASR one-shot (5 s timeout) ==="
  timeout 5 ros2 topic echo /aima/agent/asr_result --once
} 2>&1 | tee "$LOG"

echo "evidence saved to $OUT"
