#!/bin/bash
# Run with the phone in TWRP, before the first flash. Saves the current boot
# (to get Android back) and the per-device partitions nothing in this
# project should ever touch, but that cannot be rebuilt if lost (EFS = IMEI).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backup
adb wait-for-recovery
for p in boot efs modemst1 modemst2 fsg fsc persist; do
	dev=/dev/block/bootdevice/by-name/$p
	if adb shell "test -e $dev"; then
		adb pull "$dev" "backup/$p.img"
	else
		echo "skip $p (no $dev)"
	fi
done
(cd backup && sha256sum ./*.img > SHA256SUMS && cat SHA256SUMS)
