#!/bin/bash
# Install the Beamloom player onto a Raspberry Pi that already has
# Raspberry Pi OS (64-bit) with a desktop. After this, use the browser
# on the show PC. Do not sign in on the Pi for show setup.
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run: sudo ./install.sh"
  exit 1
fi

if [[ -r /proc/device-tree/model ]]; then
  model="$(tr -d '\0' < /proc/device-tree/model)"
else
  model=""
fi
if [[ "$model" != Raspberry\ Pi* ]]; then
  echo "This installer only runs on a Raspberry Pi. Found: ${model:-nothing}"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 avahi-daemon cage
if ! apt-get install -y chromium; then
  apt-get install -y chromium-browser
fi

install -d /opt/beamloom-player /var/lib/beamloom
install -m 0644 "$(dirname "$0")/beamloom_player.py" /opt/beamloom-player/beamloom_player.py
if [[ ! -f /var/lib/beamloom/player.json ]]; then
  printf '%s\n' '{"pcUrl": ""}' > /var/lib/beamloom/player.json
fi

hostnamectl set-hostname beamloom
install -m 0644 "$(dirname "$0")/systemd/beamloom-player.service" /etc/systemd/system/beamloom-player.service
install -m 0644 "$(dirname "$0")/systemd/beamloom-kiosk.service" /etc/systemd/system/beamloom-kiosk.service
systemctl daemon-reload
systemctl enable --now avahi-daemon beamloom-player.service beamloom-kiosk.service
echo "Player settings: http://beamloom.local/"
