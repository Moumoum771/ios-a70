#!/bin/bash
# Phone in TWRP: what is really in the boot partition, and what the phone
# can tell us: the shim's RAM log (pstore), the command line and the device
# tree that ABL handed to TWRP's kernel.
#   tools/twrp-check.sh [IMAGE]   IMAGE = what boot should hold (out/boot.img)
set -uo pipefail
cd "$(dirname "$0")/.."
img=${1:-out/boot.img}
stamp=$(date +%Y%m%d-%H%M%S)
mkdir -p logs dtb
adb wait-for-recovery
# This panel shows mostly black below ~90 % brightness: TWRP at the max.
adb shell 'echo 50000 > /sys/class/backlight/panel0-backlight/brightness' 2>/dev/null || true

boot=$(adb shell 'for p in /dev/block/bootdevice/by-name/boot /dev/block/by-name/boot /dev/block/platform/*/by-name/boot /dev/block/platform/*/*/by-name/boot; do [ -e $p ] && echo $p && break; done' | tr -d '\r')
n=$(( $(stat -c %s "$img") / 4096 ))
want=$(sha256sum "$img" | cut -d' ' -f1)
got=$(adb shell "dd if=$boot bs=4096 count=$n 2>/dev/null | sha256sum" | cut -d' ' -f1)
echo "== boot ($boot): $([ "$want" = "$got" ] && echo "igual a $img" || echo "DIFERENTE de $img")"
echo "   primeiros bytes: $(adb shell "dd if=$boot bs=8 count=1 2>/dev/null" | tr -c '[:print:]' '.')"

echo "== pstore (caixa-preta do shim)"
adb shell 'grep -q " /sys/fs/pstore " /proc/mounts || mount -t pstore pstore /sys/fs/pstore; ls -l /sys/fs/pstore'
adb shell 'cat /sys/fs/pstore/console-ramoops* 2>/dev/null' > "logs/pstore-$stamp.txt"
echo "   salvo em logs/pstore-$stamp.txt ($(wc -c < "logs/pstore-$stamp.txt") bytes); fim:"
grep -a -A200 "=== S9 shim" "logs/pstore-$stamp.txt" | tail -40
adb shell 'dmesg | grep -i -E "ramoops|pstore|persistent_ram"; zcat /proc/config.gz 2>/dev/null | grep -E "PSTORE_RAM|PSTORE_CONSOLE"'

echo "== o que o ABL passou"
adb shell cat /proc/cmdline > "logs/cmdline-$stamp.txt"
tr ' ' '\n' < "logs/cmdline-$stamp.txt" | grep -E "dsi_display|lcd_id|bootmode|androidboot.(revision|hw_rev|bootloader|debug_level)|reboot|reason" || true
adb shell 'cat /proc/device-tree/model; echo'
adb pull /sys/firmware/fdt "dtb/live-twrp-$stamp.dtb" >/dev/null && echo "   DTB vivo em dtb/live-twrp-$stamp.dtb"
