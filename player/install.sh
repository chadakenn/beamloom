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
apt-get install -y python3 avahi-daemon cage network-manager
if ! apt-get install -y chromium; then
  apt-get install -y chromium-browser
fi

install -d /opt/beamloom-player /var/lib/beamloom
if ! id beamloom >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash beamloom
fi
usermod -aG video,render,input beamloom
install -m 0644 "$(dirname "$0")/beamloom_player.py" /opt/beamloom-player/beamloom_player.py
install -m 0644 "$(dirname "$0")/wifi.py" /opt/beamloom-player/wifi.py
install -m 0644 "$(dirname "$0")/updater.py" /opt/beamloom-player/updater.py
install -m 0644 "$(dirname "$0")/play.html" /opt/beamloom-player/play.html
install -m 0644 "$(dirname "$0")/VERSION" /opt/beamloom-player/version
if [[ ! -f /var/lib/beamloom/player.json ]]; then
  printf '%s\n' '{"pcUrl": ""}' > /var/lib/beamloom/player.json
fi

hostnamectl set-hostname beamloom
install -m 0644 "$(dirname "$0")/systemd/beamloom-wifi.service" /etc/systemd/system/beamloom-wifi.service
install -m 0644 "$(dirname "$0")/systemd/beamloom-player.service" /etc/systemd/system/beamloom-player.service
install -m 0644 "$(dirname "$0")/systemd/beamloom-kiosk.service" /etc/systemd/system/beamloom-kiosk.service
install -m 0644 "$(dirname "$0")/systemd/beamloom-kiosk.pam" /etc/pam.d/beamloom-kiosk
install -d /usr/share/icons/beamloom-blank/cursors
for name in left_ptr default pointer arrow top_left_arrow; do
  install -m 0644 "$(dirname "$0")/cursor/left_ptr" "/usr/share/icons/beamloom-blank/cursors/${name}"
done
systemctl daemon-reload
systemctl enable --now avahi-daemon beamloom-wifi.service beamloom-player.service beamloom-kiosk.service
echo "If the Pi is not on Ethernet, join Wi-Fi Beamloom, password beamloom, then open http://192.168.4.1/"
