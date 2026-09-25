#!/bin/bash
# Build a Beamloom SD card image with the Raspberry Pi OS image builder.
# The result is a zip in the pi-gen deploy folder. Write that with Raspberry Pi Imager.
# Do not run player/install.sh on a card made from this image.
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
work="${BEAMLOOM_PIGEN_DIR:-/tmp/pi-gen}"

if [[ "$(id -u)" -eq 0 ]]; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y quilt parted coreutils qemu-user-binfmt debootstrap zerofree zip dosfstools e2fsprogs libcap2-bin libarchive-tools grep rsync xz-utils curl xxd file git kmod bc gpg pigz arch-test
fi

rm -rf "$work"
git clone --depth 1 https://github.com/RPi-Distro/pi-gen.git "$work"

mkdir -p "$work/stage-beamloom/00-install/files"
cp -a "$root/player/image/stage-beamloom/." "$work/stage-beamloom/"
cp "$root/player/beamloom_player.py" "$root/player/wifi.py" "$root/player/updater.py" "$work/stage-beamloom/00-install/files/"
cp "$root/player/systemd/"*.service "$work/stage-beamloom/00-install/files/"
cp "$root/player/image/config" "$work/config"
# Current pi-gen forces a 32-bit image after reading config. Pi 4 and Pi 5 use 64-bit.
sed -i 's/^export ARCH=armhf$/export ARCH="${ARCH:-arm64}"/' "$work/build.sh"
chmod +x "$work/stage-beamloom/00-install/00-run.sh" "$work/stage-beamloom/01-enable/00-run-chroot.sh"

touch "$work/stage3/SKIP" "$work/stage4/SKIP" "$work/stage5/SKIP"
touch "$work/stage2/SKIP_IMAGES" "$work/stage3/SKIP_IMAGES" "$work/stage4/SKIP_IMAGES" "$work/stage5/SKIP_IMAGES"

cd "$work"
./build.sh
echo "Image files:"
ls -lh "$work/deploy"
