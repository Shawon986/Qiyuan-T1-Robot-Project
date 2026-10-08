#!/usr/bin/env bash
# ROS 2 Humble Desktop installer for WSL Ubuntu 22.04 (Jammy)
# Network note: packages.ros.org and GitHub are blocked on this network,
# so the ROS 2 apt repo uses the TUNA mirror instead.
# Usage (as root): bash ros2_humble_setup.sh setup|fixmirror|install|post
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

CODENAME=$(. /etc/os-release && echo "$UBUNTU_CODENAME")
KEY_URL=https://mirrors.tuna.tsinghua.edu.cn/rosdistro/ros.key
MIRROR_URL=https://mirrors.tuna.tsinghua.edu.cn/ros2/ubuntu

do_setup() {
  if [ "$CODENAME" != "jammy" ]; then
    echo "ERROR: Ubuntu codename '$CODENAME' is not jammy; aborting."
    exit 1
  fi

  echo "==> [1/5] apt update"
  apt-get update -y

  echo "==> [2/5] install prerequisites"
  apt-get install -y locales software-properties-common curl gnupg2 lsb-release

  echo "==> [3/5] set en_US.UTF-8 locale"
  locale-gen en_US en_US.UTF-8
  update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
  export LANG=en_US.UTF-8

  echo "==> [4/5] enable universe repository"
  add-apt-repository -y universe
  apt-get update -y

  echo "==> [5/5] add ROS 2 apt repository (TUNA mirror)"
  curl -fsSL "$KEY_URL" -o /usr/share/keyrings/ros-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] $MIRROR_URL $CODENAME main" \
    > /etc/apt/sources.list.d/ros2.list
  apt-get update -y
  echo "==> setup done"
}

do_fixmirror() {
  echo "==> fetch ROS 2 GPG key from TUNA mirror"
  curl -fsSL "$KEY_URL" -o /usr/share/keyrings/ros-archive-keyring.gpg

  echo "==> point ros2.list at TUNA mirror"
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] $MIRROR_URL $CODENAME main" \
    > /etc/apt/sources.list.d/ros2.list

  echo "==> apt update"
  apt-get update -y

  echo "==> candidate check (ros-humble-desktop)"
  apt-cache policy ros-humble-desktop | head -5

  echo "==> rosdistro index mirror check (needed later for rosdep)"
  for idx in https://mirrors.ustc.edu.cn/rosdistro/index-v4.yaml https://mirrors.tuna.tsinghua.edu.cn/rosdistro/index-v4.yaml; do
    printf "%s -> " "$idx"
    code=$(curl -sS -o /dev/null -m 8 -w "%{http_code}" "$idx" 2>/dev/null) && echo "$code" || echo FAIL
  done
  echo "==> fixmirror done"
}

do_install() {
  echo "==> installing ros-humble-desktop + ros-dev-tools + python3-rosdep (big download)"
  apt-get install -y ros-humble-desktop ros-dev-tools python3-rosdep
  echo "==> install done"
}

do_post() {
  echo "==> rosdep init"
  rosdep init || echo "rosdep already initialized"
  echo "==> post done"
}

case "${1:-}" in
  setup) do_setup ;;
  fixmirror) do_fixmirror ;;
  install) do_install ;;
  post) do_post ;;
  *) echo "usage: $0 setup|fixmirror|install|post"; exit 1 ;;
esac
