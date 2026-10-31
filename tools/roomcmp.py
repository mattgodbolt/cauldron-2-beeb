#!/usr/bin/env python3
"""Compare the rooms the BBC viewer drew (tools/roomcheck.mjs,
build/bbcrooms) with the original's own drawing of them
(tools/zxrooms.py, build/zxrooms).

    .venv/bin/python tools/roomcmp.py [rooms] [--png build/bbcrooms]

For each room, the whole screen and the attributes:

- lit pixels: the BBC's (any non-zero logical colour) against the
  Spectrum's bits, every pixel;
- attributes: all 768 bytes, exactly (rows 0-3 are the panel the
  viewer drew, rows 4-23 the room);
- colour: every MODE 1 byte against what the port's rule makes of the
  original's screen (tools/colours.py: each cell's lit pixels in its ink's
  pattern for its row, the room's plan);

and the share of lit pixels shown in their own colour on the BBC (the
row's physical colour of the pixel's logical one against the cell's ink).
Writes contact.png (every room as the BBC shows it, through each row's
palette) and, for a room that differs, room_NN.png. Exits non-zero on any
difference.
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colours import BBC_RGB, ZX_TO_BBC, mode1_byte, pick, plan_room, room_rows, scr_cell_byte  # noqa: E402


def expected(scr, rows):
    mem = bytearray(0x3000)
    for cy in range(24):
        for cx in range(32):
            ink = scr[6144 + cy * 32 + cx] & 7
            a, b = pick(rows[cy], ink)
            for i in range(8):
                byte = scr_cell_byte(scr, cy * 8 + i, cx)
                pat = mode1_byte(a, b, i & 1)
                base = cy * 512 + cx * 16 + i
                mem[base] = ((byte >> 4) * 0x11) & pat
                mem[base + 8] = ((byte & 15) * 0x11) & pat
    return mem


def pixel(mem, x, y):
    b = mem[(y // 8) * 512 + (x // 8) * 16 + (8 if x & 4 else 0) + (y & 7)]
    p = x & 3
    return ((b >> (7 - p)) & 1) * 2 + ((b >> (3 - p)) & 1)


def image(mem, rows):
    im = Image.new("RGB", (256, 192))
    px = im.load()
    for y in range(192):
        pal = (0,) + tuple(rows[y // 8])
        for x in range(256):
            px[x, y] = BBC_RGB[pal[pixel(mem, x, y)]]
    return im


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rooms", nargs="?", default="0-127")
    ap.add_argument("--zx", default="build/zxrooms")
    ap.add_argument("--bbc", default="build/bbcrooms")
    args = ap.parse_args()
    rooms = []
    for part in args.rooms.split(","):
        lo, _, hi = part.partition("-")
        rooms.extend(range(int(lo), int(hi or lo) + 1))
    bad = 0
    lit_all = own_all = 0
    tiles = []
    for room in rooms:
        scr = open(os.path.join(args.zx, f"room_{room:02d}.scr"), "rb").read()
        bbc = open(os.path.join(args.bbc, f"room_{room:02d}.bin"), "rb").read()
        mem, attrs = bbc[:0x3000], bbc[0x3000:0x3000 + 768]
        rows = room_rows(plan_room(scr))
        lit_bad = sum(1 for y in range(192) for x in range(256)
                      if bool(pixel(mem, x, y)) != bool(scr_cell_byte(scr, y, x // 8) & (0x80 >> (x & 7))))
        attr_bad = sum(1 for k in range(768) if attrs[k] != scr[6144 + k])
        exp = expected(scr, rows)
        col_bad = sum(1 for k in range(0x3000) if exp[k] != mem[k])
        lit = own = 0
        for y in range(32, 192):
            pal = (0,) + tuple(rows[y // 8])
            for x in range(256):
                c = pixel(mem, x, y)
                if c:
                    lit += 1
                    own += pal[c] == (ZX_TO_BBC[scr[6144 + (y // 8) * 32 + x // 8] & 7] or 7)
        lit_all += lit
        own_all += own
        im = image(mem, rows)
        tiles.append((room, im))
        if lit_bad or attr_bad or col_bad:
            bad += 1
            print(f"room {room}: {lit_bad} lit pixels, {attr_bad} attributes, {col_bad} bytes' colours differ")
            im.resize((512, 384), Image.NEAREST).save(os.path.join(args.bbc, f"room_{room:02d}.png"))
    cols = 8
    nrows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 260, nrows * 206), (64, 64, 64))
    draw = ImageDraw.Draw(sheet)
    for k, (room, im) in enumerate(tiles):
        x, y = (k % cols) * 260 + 2, (k // cols) * 206 + 12
        sheet.paste(im, (x, y))
        draw.text((x, y - 11), str(room), fill=(255, 255, 255))
    sheet.save(os.path.join(args.bbc, "contact.png"))
    print(f"roomcmp: {len(rooms) - bad} of {len(rooms)} rooms identical (lit pixels, attributes, colours); "
          f"rows 4-23: {own_all} of {lit_all} lit pixels in their own colour ({100 * own_all / max(lit_all, 1):.2f}%); "
          f"{args.bbc}/contact.png")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
