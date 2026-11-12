#!/bin/bash
# Fast loop: phone in TWRP, write a boot image straight into the boot
# partition, read it back, and reboot into it only if the hashes match
# (a flash we did not verify cost us a night: see NOTES.md, Flash 1).
set -euo pipefail
cd "$(dirname "$0")/.."
img=${1:-out/boot.img}
adb wait-for-recovery
# This panel shows mostly black below ~90 % brightness: TWRP at the max.
adb shell 'echo 50000 > /sys/class/backlight/panel0-backlight/brightness' 2>/dev/null || true
boot=$(adb shell 'for p in /dev/block/bootdevice/by-name/boot /dev/block/by-name/boot /dev/block/platform/*/by-name/boot /dev/block/platform/*/*/by-name/boot; do [ -e $p ] && echo $p && break; done' | tr -d '\r')
[ -n "$boot" ] || { echo "boot partition not found" >&2; exit 1; }
adb push "$img" /tmp/shim-boot.img
adb shell "dd if=/tmp/shim-boot.img of=$boot bs=4096 && sync"
n=$(( $(stat -c %s "$img") / 4096 ))
want=$(sha256sum "$img" | cut -d' ' -f1)
got=$(adb shell "dd if=$boot bs=4096 count=$n 2>/dev/null | sha256sum" | cut -d' ' -f1)
[ "$want" = "$got" ] || { echo "readback $got != $want: not rebooting" >&2; exit 1; }
echo "boot = $img ($want)"
[ "${NOREBOOT:-0}" = 1 ] || adb reboot
