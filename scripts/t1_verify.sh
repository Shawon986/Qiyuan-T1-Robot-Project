#!/usr/bin/env bash
# T1 SDK post-build verification (run as regular user)
set -o pipefail
cd "$HOME/t1_workspaces/primebot_sdk"
source /opt/ros/humble/setup.bash
source "$PWD/install/setup.bash"

echo "==> built packages"
ls install/ | grep -vE 'setup|local_setup|COLCON'

echo "==> ROS distro + RMW (handbook expects rmw_fastrtps_cpp)"
echo "ROS_DISTRO=$ROS_DISTRO"
echo "RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION"
echo "FASTRTPS_DEFAULT_PROFILES_FILE=$FASTRTPS_DEFAULT_PROFILES_FILE"
echo "FASTDDS_DEFAULT_PROFILES_FILE=$FASTDDS_DEFAULT_PROFILES_FILE"

echo "==> interface checks (handbook Chapter 4)"
echo "--- aimdk_msgs/msg/Bms ---"
ros2 interface show aimdk_msgs/msg/Bms | head -30
echo "--- aimdk_msgs/srv/PlayTts ---"
ros2 interface show aimdk_msgs/srv/PlayTts | head -20

echo "==> aimdk_msgs interface count"
ros2 interface list | grep -c aimdk_msgs || true
echo "==> verify done"
