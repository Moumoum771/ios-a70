#!/bin/bash
# Phone in TWRP: stream an iOS root image (raw HFS+, tools mkiosroot.sh) into
# the userdata partition, gzip on the wire, then compare the sha256 of the
# written range with the image. ERASES whatever userdata held.
#   tools/flash-userdata.sh IMAGE
set -euo pipefail
img=$1
size=$(stat -c %s "$img")
adb wait-for-recovery
adb shell 'echo 50000 > /sys/class/backlight/panel0-backlight/brightness' 2>/dev/null || true
dev=$(adb shell 'for p in /dev/block/bootdevice/by-name/userdata /dev/block/by-name/userdata /dev/block/platform/*/*/by-name/userdata; do [ -e $p ] && readlink -f $p && break; done' | tr -d '\r')
[ -n "$dev" ] || { echo "userdata not found" >&2; exit 1; }
if adb shell "grep -q '^$dev ' /proc/mounts"; then
	echo "$dev is mounted: unmount it in TWRP first" >&2
	exit 1
fi
part=$(adb shell "blockdev --getsize64 $dev" | tr -d '\r')
[ "$size" -le "$part" ] || { echo "image ($size) larger than $dev ($part)" >&2; exit 1; }
echo "writing $img ($size bytes) to $dev ($part bytes)"
want_file=$(mktemp)
sha256sum "$img" | cut -d' ' -f1 > "$want_file" &
gzip -1 -c "$img" | adb shell -T "gunzip -c > $dev && sync"
wait
want=$(cat "$want_file")
rm -f "$want_file"
got=$(adb shell "head -c $size $dev | sha256sum" | cut -d' ' -f1)
[ "$want" = "$got" ] || { echo "readback $got != $want" >&2; exit 1; }
echo "userdata = $img ($want)"
