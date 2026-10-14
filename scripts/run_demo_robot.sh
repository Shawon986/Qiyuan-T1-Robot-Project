#!/usr/bin/env bash
# Start the exhibition demo server ON THE ROBOT (brain board).
# Usage: bash run_demo_robot.sh   (run from the qiyuan-demo deploy dir)
set -o pipefail
cd "$(dirname "$0")"

# The robot has its own ROS 2 distro; source the first one found (never fail otherwise).
# Needed so the official capture tool can import rclpy + aimdk_msgs.
for ros_setup in /opt/ros/*/setup.bash; do
  if [ -f "$ros_setup" ]; then
    source "$ros_setup"
    break
  fi
done

# Board-specific SDK environment (paths from the official developer framework).
# Without these, aimdk_msgs imports can fail on the board even with /opt/ros sourced.
[ -f /robot/etc/basic_env ] && source /robot/etc/basic_env
[ -f /robot/software/housekeeper/bin/setup.bash ] && source /robot/software/housekeeper/bin/setup.bash

# Pure-python apps run straight from source — no colcon build needed.
export PYTHONPATH="$(pwd)/apps/demo_ui:$(pwd)/apps/seedance:$(pwd)/apps/conversation"
# .env sits next to the apps; the loaders also check $PWD/.env and QIYUAN_ENV_FILE.
export QIYUAN_ENV_FILE="$(pwd)/.env"
# On the robot: speak replies through the OFFICIAL PlayAudioFile service
# (local file playback - the platform's Mandarin-only cloud TTS is never used).
export AUDIO_PLAYBACK=playaudiofile

exec python3 -m demo_ui.server --host 0.0.0.0 --port 8765 --pages "$(pwd)/exhibition/exhibition"
