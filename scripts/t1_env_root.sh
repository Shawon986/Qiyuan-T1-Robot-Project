#!/usr/bin/env bash
# T1 SDK environment setup — part 1 (run as root)
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "==> [1/3] SDK build dependencies (vendor list)"
apt-get update -y
apt-get install -y \
  python3-colcon-common-extensions \
  python3-dev \
  python3-pip \
  ros-humble-rosidl-default-generators \
  ros-humble-rosidl-default-runtime

echo "==> [2/3] C++ / vision / Ruckig dependencies"
apt-get install -y \
  cmake build-essential pkg-config \
  libavcodec-dev libavformat-dev libavutil-dev libswscale-dev \
  libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
  libyaml-cpp-dev

echo "==> [3/3] UDP socket buffer sysctl (vendor 24 MiB recommendation)"
cat > /etc/sysctl.d/99-primebot-sdk.conf <<'EOF'
net.core.rmem_max = 25165824
net.core.wmem_max = 25165824
EOF
sysctl --system
sysctl net.core.rmem_max net.core.wmem_max

echo "==> tool versions"
colcon --version
cmake --version | head -1
g++ --version | head -1
python3 -m pip --version
echo "==> env setup (root) done"
