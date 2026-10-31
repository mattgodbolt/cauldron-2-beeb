#!/usr/bin/env python3
"""Make the original draw any room, headless: the oracle for the port's room drawing.

    .venv/bin/python tools/zxrooms.py [rooms] [--snap build/c2.z80] [--out build/zxrooms] [--full]

rooms is a list such as 0-127 (the default, every room) or 5,97,110-117.

How: from the entry snapshot it starts a game (Kempston, Play, fire) and
keeps that in-game state. For each room it reloads that state, sets A to the
room number, pushes a sentinel return address and jumps to the room-entry
routine at 53949 (docs/research/core.md, "Room drawing"). By default it stops
at 54154, just after the scenery's pixels are written straight to the screen
and the attribute buffer at 24225 is copied to 22656 (54499): that is the
scenery alone, deterministic for any room. With --full it runs on to the
routine's return, which also redraws the player sprite from the slot-0 state
in 24077, spawns the room's monsters (54264) and its ingredient (54229);
those depend on the game state the snapshot holds.

Writes <out>/room_NN.scr (6912 bytes: the bitmap, then the attributes, as a
SCREEN$), room_NN.png, and contact.png (every room drawn, 8 across, with its
number). Rows 0-3 are the panel, left as the game drew it.
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw
from skoolkit.simutils import A, PC, SP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zx import Spectrum, run_script, screen_image  # noqa: E402

START = "2,1:tap,1,4:tap,4,KF:0.3,2"  # menu: 1 Kempston, 4 Play; fire starts
ROOM_ENTRY = 53949      # draw room A (saves and restores every register)
SCENERY_DONE = 54154    # after the tiles and the attribute copy (54499)
SENTINEL = 23296        # printer buffer: never executed by the game
NUM_ROOMS = 128         # the map at 63498 and the layouts at 43750 have 128 entries


def parse_rooms(spec):
    rooms = []
    for part in spec.split(","):
        lo, _, hi = part.partition("-")
        rooms.extend(range(int(lo), int(hi or lo) + 1))
    return rooms


def draw_room(base, room, full):
    spec = Spectrum(base)
    regs = spec.sim.registers
    mem = spec.mem
    sp = (regs[SP] - 2) & 0xFFFF
    mem[sp] = SENTINEL & 0xFF
    mem[sp + 1] = SENTINEL >> 8
    regs[SP] = sp
    regs[A] = room
    regs[PC] = ROOM_ENTRY
    stop = SENTINEL if full else SCENERY_DONE
    pc = spec.run_tstates(50 * spec.frame, stop=stop)
    if pc != stop:
        raise RuntimeError(f"room {room}: stopped at {pc}, not {stop}")
    return spec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rooms", nargs="?", default=f"0-{NUM_ROOMS - 1}")
    ap.add_argument("--snap", default="build/c2.z80")
    ap.add_argument("--out", default="build/zxrooms")
    ap.add_argument("--full", action="store_true", help="run to the routine's return (sprites, monsters, item)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    base = os.path.join(args.out, "ingame.z80")
    spec = Spectrum(args.snap)
    run_script(spec, START, "")
    spec.save(base)

    tiles = []
    for room in parse_rooms(args.rooms):
        spec = draw_room(base, room, args.full)
        mem = spec.mem
        with open(os.path.join(args.out, f"room_{room:02d}.scr"), "wb") as f:
            f.write(bytes(mem[16384:16384 + 6912]))
        im = screen_image(mem, scale=1)
        im.save(os.path.join(args.out, f"room_{room:02d}.png"))
        tiles.append((room, im))

    cols = 8
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 260, rows * 206), (64, 64, 64))
    draw = ImageDraw.Draw(sheet)
    for i, (room, im) in enumerate(tiles):
        x, y = (i % cols) * 260 + 2, (i // cols) * 206 + 12
        sheet.paste(im, (x, y))
        draw.text((x, y - 11), str(room), fill=(255, 255, 255))
    sheet.save(os.path.join(args.out, "contact.png"))
    print(f"{len(tiles)} rooms -> {args.out}/room_NN.scr, contact.png")


if __name__ == "__main__":
    sys.exit(main())
