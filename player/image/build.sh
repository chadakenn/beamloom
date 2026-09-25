#!/bin/bash
# Build a Beamloom SD card image with the Raspberry Pi OS image builder.
# The result is a zip in the pi-gen deploy folder. Write that with Raspberry Pi Imager.
# Do not run player/install.sh on a card made from this image.
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
work="${BEAMLOOM_PIGEN_DIR:-/tmp/pi-gen}"
rm -rf "$work"
git clone --depth 1 https://github.com/RPi-Distro/pi-gen.git "$work"

mkdir -p "$work/stage-beamloom/00-install/files"
cp -a "$root/player/image/stage-beamloom/." "$work/stage-beamloom/"
cp "$root/player/beamloom_player.py" "$root/player/wifi.py" "$work/stage-beamloom/00-install/files/"
cp "$root/player/systemd/"*.service "$work/stage-beamloom/00-install/files/"
cp "$root/player/image/config" "$work/config"
chmod +x "$work/stage-beamloom/00-install/00-run.sh" "$work/stage-beamloom/01-enable/00-run-chroot.sh"

touch "$work/stage3/SKIP" "$work/stage4/SKIP" "$work/stage5/SKIP"
touch "$work/stage2/SKIP_IMAGES" "$work/stage3/SKIP_IMAGES" "$work/stage4/SKIP_IMAGES" "$work/stage5/SKIP_IMAGES"

cd "$work"
./build.sh
echo "Image files:"
ls -lh "$work/deploy"
