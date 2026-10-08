#!/usr/bin/env bash
# Day 4 - bring up the robot LAN over the USB-Ethernet adapter (run as root in WSL).
#
# Windows side FIRST (PowerShell, admin):
#   usbipd list                         # find the adapter's BUSID
#   usbipd bind --busid <BUSID>
#   usbipd attach --wsl                 # adapter now appears inside WSL
#
# Then run this script. It expects the adapter to show up as a Linux NIC that is
# NOT the default WSL eth0. It sets the documented direct-link address 10.1.1.99/24
# and probes the documented board defaults (change them if the robot differs).
set -uo pipefail

echo "=== interfaces before ==="
ip -br link
ip -br addr

# First extra ethernet interface that is not the default WSL eth0.
NIC=$(ip -br link | awk '$1 ~ /^eth[0-9]+$/ && $1 != "eth0" {print $1; exit}')
if [ -z "$NIC" ]; then
  echo "No extra NIC found - did you usbipd attach the adapter? Aborting."
  exit 1
fi
echo "Using $NIC for the robot LAN."

ip addr flush dev "$NIC" 2>/dev/null || true
ip addr add 10.1.1.99/24 dev "$NIC"
ip link set "$NIC" up

echo "=== reachability (documented defaults; adjust to actual board IPs) ==="
ping -c 3 10.1.1.100 || echo "MC board 10.1.1.100 not reachable"
ping -c 3 10.1.1.101 || echo "brain board 10.1.1.101 not reachable"
ip route get 10.1.1.100
