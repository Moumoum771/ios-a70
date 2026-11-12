#!/bin/bash
# Build the Samsung Galaxy A70 (SM-A705, SM6150) shim and wrap it the way
# Samsung's ABL expects: boot.img header v0, Image.gz with the A70 DTB appended.
#   ./build.sh [m1|m2|m3] stage to build (default m2)
#   PAYLOAD=out/payload.bin ./build.sh m4   XNU payload as the ramdisk
#   out/boot.img      -> tools/flash-twrp.sh (verified dd), also kept as out/boot-STAGE.img
#   out/boot.tar.md5  -> Odin, AP slot
set -euo pipefail
cd "$(dirname "$0")"

# Arch's cross gcc unpacked into toolchain/root (no root needed), unless told otherwise.
if [ -z "${CROSS_COMPILE:-}" ] && [ -x ../toolchain/root/usr/bin/aarch64-linux-gnu-gcc ]; then
	CROSS_COMPILE=../toolchain/root/usr/bin/aarch64-linux-gnu-
fi
CROSS=${CROSS_COMPILE:-aarch64-linux-gnu-}
CC=${CROSS}gcc
OBJCOPY=${CROSS}objcopy
READELF=${CROSS}readelf
NM=${CROSS}nm
STOCK_BOOT=${STOCK_BOOT:-../boot_a70.img}
CFLAGS="-O2 -ffreestanding -nostdlib -fno-pic -mgeneral-regs-only -mstrict-align -fno-stack-protector -fno-tree-loop-distribute-patterns -Wall -Wextra"

STAGE=${1:-m2}
case $STAGE in
m1) main="m1.c screen.c" ;;
m2) main="m2.c console.c" ;;
m3) main="m3.c console.c plat.c ufs.c mmu.c" ;;
m4) main="m4.c console.c plat.c loader.c"
    [ -f "${PAYLOAD:-}" ] || { echo "m4 needs PAYLOAD=path/to/payload.bin (tools/mkpayload.py)" >&2; exit 2; } ;;
*) echo "usage: build.sh [m1|m2|m3|m4]" >&2; exit 2 ;;
esac

mkdir -p out/obj
rm -f out/obj/*.o
objs=()
for f in start.S $main fb.c mdss.c fdt.c ramlog.c lib.c; do
	o=out/obj/${f%.*}.o
	"$CC" $CFLAGS -c "shim/$f" -o "$o"
	objs+=("$o")
done

# ABL runs us wherever it loads us, with no relocation pass: only the
# header's image_size (start.o, linked at 0) may be an absolute address.
abs=$("$READELF" -r "${objs[@]:1}" | grep -c ABS64 || true)
[ "$abs" = 0 ] || { echo "error: $abs absolute relocations in C objects" >&2; exit 1; }
"$CC" $CFLAGS -static -T shim/shim.ld -Wl,--build-id=none -Wl,--no-warn-rwx-segments -Wl,-N \
	"${objs[@]}" -o out/shim.elf
"$OBJCOPY" -O binary out/shim.elf out/Image
# ABL copies the file; pad to image_size so .bss/stack exist as zeroed bytes.
size=$("$NM" out/shim.elf | awk '$3=="_end"{print strtonum("0x"$1)}')
truncate -s "$size" out/Image
gzip -9 -n -c out/Image > out/Image.gz

# Append A70 DTB so ABL passes it to the shim in x0
if [ -f dtb/stock-dtbs.bin ]; then
	cat out/Image.gz dtb/stock-dtbs.bin > out/Image.gz-dtb
elif [ -f ../dtb/a70q.dtb ]; then
	cat out/Image.gz ../dtb/a70q.dtb > out/Image.gz-dtb
elif [ -f "$STOCK_BOOT" ]; then
	python3 -I tools/extract-stock-dtbs.py "$STOCK_BOOT" dtb/stock-dtbs.bin
	cat out/Image.gz dtb/stock-dtbs.bin > out/Image.gz-dtb
else
	echo "warning: no dtb found, Image.gz left without appended dtb" >&2
	cp out/Image.gz out/Image.gz-dtb
fi

# Ramdisk: the XNU payload for m4; otherwise an empty newc cpio
if [ "$STAGE" = m4 ]; then
	cp "$PAYLOAD" out/ramdisk.cpio.gz
else
	(cd out && rm -rf rd && mkdir rd && cd rd && touch -d @0 . && find . | cpio -o -H newc --reproducible --quiet | gzip -9 -n > ../ramdisk.cpio.gz)
fi

# Samsung A70 boot.img header v0
mkbootimg --header_version 0 --kernel out/Image.gz-dtb --ramdisk out/ramdisk.cpio.gz \
	--base 0x00000000 --kernel_offset 0x00008000 --ramdisk_offset 0x02000000 \
	--second_offset 0x00f00000 --tags_offset 0x01e00000 --pagesize 4096 \
	--cmdline "console=null" -o out/boot.img

# Odin tar
(cd out && tar -H ustar -cf boot.tar boot.img && md5sum -t boot.tar >> boot.tar && mv boot.tar boot.tar.md5)

cp out/boot.img "out/boot-$STAGE.img"
ls -l out/Image out/boot.img out/boot.tar.md5
sha256sum out/boot.img
