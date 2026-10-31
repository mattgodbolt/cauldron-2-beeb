#!/usr/bin/env python3
"""Write one data block of a TAP file (its bytes without the flag and
checksum).

    python3 -I tools/tapblock.py original/CauldronII.tap 6 build/data/title.scr

Blocks count from 1, as tapinfo.py numbers them. Block 6 of Palace's tape
is the loading screen (SCREEN$, 6912 bytes at 16384).
"""
import sys


def blocks(tap):
    i = 0
    while i < len(tap):
        n = tap[i] | tap[i + 1] << 8
        yield tap[i + 2:i + 2 + n]
        i += 2 + n


def main():
    tap, num, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    block = list(blocks(open(tap, "rb").read()))[num - 1]
    open(out, "wb").write(block[1:-1])


if __name__ == "__main__":
    main()
