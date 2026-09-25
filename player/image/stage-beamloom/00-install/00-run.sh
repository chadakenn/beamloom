#!/bin/bash -e
install -d "${ROOTFS_DIR}/opt/beamloom-player" "${ROOTFS_DIR}/var/lib/beamloom" "${ROOTFS_DIR}/etc/systemd/system"
install -m 0644 files/beamloom_player.py "${ROOTFS_DIR}/opt/beamloom-player/beamloom_player.py"
install -m 0644 files/wifi.py "${ROOTFS_DIR}/opt/beamloom-player/wifi.py"
install -m 0644 files/updater.py "${ROOTFS_DIR}/opt/beamloom-player/updater.py"
install -m 0644 files/beamloom-player.service "${ROOTFS_DIR}/etc/systemd/system/beamloom-player.service"
install -m 0644 files/beamloom-kiosk.service "${ROOTFS_DIR}/etc/systemd/system/beamloom-kiosk.service"
install -m 0644 files/beamloom-wifi.service "${ROOTFS_DIR}/etc/systemd/system/beamloom-wifi.service"
printf '%s\n' '{"pcUrl": ""}' > "${ROOTFS_DIR}/var/lib/beamloom/player.json"
