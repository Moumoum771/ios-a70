#!/usr/bin/env python3
"""Pull the DTBs appended to the stock S9 kernel (boot.img v0, Image.gz-dtb).

ABL picks the one matching the board's msm-id/board-id and passes it to the
"kernel" in x0, so the shim ships the same list. The trailing RTIC blob
(qcom,rtic-id + MP_DATA, a measurement of Samsung's own kernel) is dropped:
it has no msm-id and describes a kernel we are not.
"""
import struct
import sys
import zlib


def main():
    if len(sys.argv) != 3:
        sys.exit('usage: extract-stock-dtbs.py STOCK_boot.img OUT.bin')
    img = open(sys.argv[1], 'rb').read()
    if img[:8] != b'ANDROID!':
        sys.exit('not an Android boot image')
    kernel_size, = struct.unpack_from('<I', img, 8)
    page_size, = struct.unpack_from('<I', img, 36)
    kernel = img[page_size:page_size + kernel_size]
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    d.decompress(kernel)
    if not d.eof:
        sys.exit('kernel is not one complete gzip stream')
    tail = d.unused_data

    out, kept, off = bytearray(), 0, 0
    while off + 8 <= len(tail):
        magic, total = struct.unpack_from('>II', tail, off)
        if magic != 0xd00dfeed:
            break
        dtb = tail[off:off + total]
        if b'qcom,msm-id\0' in dtb:
            out += dtb
            kept += 1
        else:
            print(f'skip blob at +{off:#x} ({total} bytes, no qcom,msm-id)')
        off += total
    if off != len(tail):
        sys.exit(f'unexpected data after the DTBs at +{off:#x}')
    if not kept:
        sys.exit('no DTBs found')
    open(sys.argv[2], 'wb').write(out)
    print(f'{kept} DTBs, {len(out)} bytes -> {sys.argv[2]}')


if __name__ == '__main__':
    main()
