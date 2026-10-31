#!/usr/bin/env python3
"""Make the port's data from the original, into build/data/ (never
committed: the original's files aren't).

    .venv/bin/python tools/mkdata.py [--snap build/c2.z80] [--rooms build/zxrooms] [--out build/data]

The regions of tools/mksyms.py, as the original's bytes, each under its
region's label (docs/how-it-works.md, "Memory"):

    gamedata.6502  r_sprites (25900-34525) then r_tables (57726-64194):
                   the sideways bank GAMEDATA
    roomdata.6502  r_rooms (34526-49510), then room_plans: the sideways
                   bank ROOMDATA
    font.6502      r_font (49511-50022), main RAM

Every pointer word in them is written as the BBC's address of what it
points at (POINTERS): `EQUW aNNNNN` for data, `EQUW zNNNNN` for code.
Pointers into the Spectrum's screen stay the original's values, since
the code does arithmetic on them. A word that a pointer table holds but
that points nowhere the port has (KEEP) is kept as it is.

room_plans: each room's colours (decisions 10 and 11), tools/colours.py's
plan from the original's own drawing of the room (tools/zxrooms.py's
.scr files): 10 bytes a room, colours.pack_plan's nibbles.
"""
import argparse
import os
import sys

from skoolkit.snapshot import Snapshot

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colours import pack_plan, plan_room  # noqa: E402
from mksyms import REGIONS  # noqa: E402

CODE = (50100, 57725)
SCREEN = (16384, 22527)
# Pointer tables in the regions: (first, count, stride, kind, what).
# kind 'a' points at data, 'z' at code, 's' at the screen (kept) or data.
POINTERS = [
    (57726, 1, 2, "z", "the controls reader (52658 or 52695)"),
    (58776, 2, 2, "a", "the credits pages' texts"),
    (58784, 6, 2, "a", "the key prompts"),
    (58817, 9, 2, "a", "the score records by points class"),
    (58883, 24, 2, "s", "each character row's screen address"),
    (58931, 232, 2, "s", "each pixel line's, for the clipped draw (the sink 24995 off screen)"),
    (59393, 22, 2, "a", "the movement scripts"),
    (59800, 156, 4, "a", "each sprite frame's graphics (the frame table 59798, +2)"),
    (60580, 55, 2, "a", "the anim scripts (0: none)"),
    (61120, 11, 2, "z", "the collision handlers"),
    (61677, 128, 2, "a", "each room's monster list"),
    (62954, 128, 2, "a", "each room's tile-bank list"),
    (64019, 4, 2, "z", "the interrupt's tunes (entry 0 unused)"),
]
# Words in pointer tables that point at nothing the port has: kept.
KEEP = {0, 65290}
ROOM_BANKS = 62954
NUM_ROOMS = 128


def region_of(n):
    for lo, hi, label in REGIONS:
        if lo <= n <= hi:
            return label
    return None


def pointer_name(v, kind):
    if v in KEEP:
        return str(v)
    if kind == "z":
        assert CODE[0] <= v <= CODE[1], v
        return f"z{v}"
    if kind == "s" and SCREEN[0] <= v <= SCREEN[1]:
        return str(v)
    assert region_of(v), f"pointer {v} into no region"
    return f"a{v}"


def emit(f, mem, lo, hi, words):
    """EQUB lines for lo..hi, with the words at the addresses in `words`
    (address -> name) as EQUW."""
    a = lo
    run = []

    def flush():
        for i in range(0, len(run), 16):
            f.write("    EQUB " + ",".join(str(b) for b in run[i:i + 16]) + "\n")
        run.clear()
    while a <= hi:
        if a in words:
            flush()
            f.write(f"    EQUW {words[a]}\n")
            a += 2
        else:
            run.append(mem[a])
            a += 1
    flush()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snap", default="build/c2.z80")
    ap.add_argument("--rooms", default="build/zxrooms")
    ap.add_argument("--out", default="build/data")
    args = ap.parse_args()
    mem = [0] * 16384 + list(Snapshot.get(args.snap).ram(-1))
    os.makedirs(args.out, exist_ok=True)
    word = lambda a: mem[a] | mem[a + 1] << 8  # noqa: E731

    words = {}
    for first, count, stride, kind, _ in POINTERS:
        for i in range(count):
            a = first + stride * i
            words[a] = pointer_name(word(a), kind)

    def write(name, text_fn):
        with open(os.path.join(args.out, name), "w") as f:
            f.write(f"\\ Made by tools/mkdata.py from {os.path.basename(args.snap)}. Never edited.\n")
            text_fn(f)

    region = {label: (lo, hi) for lo, hi, label in REGIONS}

    def gamedata(f):
        for label in ("r_sprites", "r_tables"):
            lo, hi = region[label]
            f.write(f".{label}\n")
            emit(f, mem, lo, hi, words)
    write("gamedata.6502", gamedata)

    # The tile-bank lists: the longest, for the copy room entry makes in
    # main RAM (src/room.6502).
    longest = max(1 + 4 * mem[word(ROOM_BANKS + 2 * r)] for r in range(NUM_ROOMS))

    def roomdata(f):
        lo, hi = region["r_rooms"]
        f.write(".r_rooms\n")
        emit(f, mem, lo, hi, {})
        f.write(".room_plans\n")
        for r in range(NUM_ROOMS):
            scr = open(os.path.join(args.rooms, f"room_{r:02d}.scr"), "rb").read()
            f.write("    EQUB " + ",".join(str(b) for b in pack_plan(plan_room(scr))) + f"   ; room {r}\n")
        f.write(f"BANK_LIST_MAX = {longest}\n")
    write("roomdata.6502", roomdata)

    def font(f):
        lo, hi = region["r_font"]
        f.write(".r_font\n")
        emit(f, mem, lo, hi, {})
    write("font.6502", font)
    print(f"mkdata: {len(words)} pointers relocated -> {args.out}/gamedata.6502, roomdata.6502, font.6502")


if __name__ == "__main__":
    main()
