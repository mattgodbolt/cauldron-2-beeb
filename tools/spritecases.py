#!/usr/bin/env python3
"""Random sprite calls on the original and the port: 57415 then 57058
(any slot: 0 and 1 clipped, 2-5 through 57182) or 57194 straight, drawn
and erased, over a room.

    .venv/bin/python tools/spritecases.py make [--cases 40] [--seed 1] [--edges]
    node tools/spritecheck.mjs
    .venv/bin/python tools/spritecases.py cmp

make: the cases (build/sprite/cases.json), each run on the original from
the room as tools/zxrooms.py draws it; writes what the port must show
(build/sprite/exp_NNN.bin: the 12K MODE 1 screen, then the original's
768 attributes and bytes 24223 on, the pre-shift's). The screen is the port's colour rule (draw.6502's head)
applied to the bits each call XORs on the original's screen: a pixel
the XOR lights takes the sprite's colour (drawing: its frame's
attribute EOR 70, or the pumpkin's yellow for slot 0 without one) or
its cell's scenery ink (erasing, or a frame without colour); one it
leaves lit keeps its colour; one it clears is black.

--edges: the unclipped draws (57194) also run off the right of their
cell row and down into the attributes (to the third attribute row at
most: the original's XOR past them reaches its own variables).

cmp: tools/spritecheck.mjs's dumps (bbc_NNN.bin) against them: lit
pixels, attributes and colours, every byte. Exits non-zero on any
difference.
"""
import argparse
import json
import os
import random
import sys

from skoolkit.simutils import A, D, E, H, L, PC, SP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colours import mode1_byte, pick, plan_room, room_rows  # noqa: E402
from roomcmp import expected, pixel  # noqa: E402
from zx import Spectrum  # noqa: E402
from zxrooms import draw_room  # noqa: E402

OUT = "build/sprite"
BASE = "build/zxrooms/ingame.z80"
SENTINEL = 23296
FRAMES, FRAME_ATTR = 59798, 60422
BUF = 24225
# The pre-shift's buffers and what its stream runs over: from the two
# bytes before 24225 to past 24427's longest stream.
BUF_END = 24900


def call(spec, addr, regs):
    r = spec.sim.registers
    mem = spec.mem
    sp = (r[SP] - 2) & 0xFFFF
    mem[sp], mem[sp + 1] = SENTINEL & 0xFF, SENTINEL >> 8
    r[SP] = sp
    for k, v in regs.items():
        r[k] = v
    r[PC] = addr
    pc = spec.run_tstates(20 * spec.frame, stop=SENTINEL)
    assert pc == SENTINEL, (addr, pc)


def zx_addr(y, cx):
    return 16384 + ((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2) + cx


def litmask(b):
    n = (b | b >> 4) & 15
    return n * 0x11


def make_cases(mem, n, seed, edges=False):
    rnd = random.Random(seed)
    frames = [f for f in range(156) if mem[FRAMES + 4 * f] and mem[FRAMES + 4 * f + 1]]
    cases = []
    for _ in range(n):
        calls = []
        for _ in range(rnd.randint(4, 12)):
            f = rnd.choice(frames)
            w, h = mem[FRAMES + 4 * f], mem[FRAMES + 4 * f + 1]
            kind = rnd.choice([0, 0, 1])
            erase = rnd.choice([0, 1])
            if kind == 1:
                slot = rnd.randint(2, 5)
                x = 4 * rnd.randint(0, 31 - w) + rnd.randint(0, 3)
                y = rnd.randint(0, 192 - h)
                if edges and rnd.randint(0, 1):
                    x = 4 * rnd.randint(32 - w, 31) + rnd.randint(0, 3)
                if edges and rnd.randint(0, 1):
                    y = rnd.randint(max(0, 192 - h), min(191, 195 - h))
            else:
                slot = rnd.randint(0, 5)
                if slot < 2:
                    x = rnd.randint(0, 143)
                    y = rnd.randint(0, 232 - h)
                else:
                    x = 12 + 4 * rnd.randint(0, 31 - w) + rnd.randint(0, 3)
                    y = rnd.randint(33, 192 - h)
            calls.append([f, x, y, slot, erase, kind])
        cases.append({"room": rnd.randint(0, 127), "calls": calls})
    return cases


def sprite_ink(mem, frame, slot, erase, kind):
    """The ink the port lights a call's pixels in; None: the cell's."""
    if erase:
        return None
    attr = mem[FRAME_ATTR + frame]
    if attr:
        return (attr ^ 70) & 7
    if kind == 0 and slot == 0:
        return 6
    return None


def run_case(case, k):
    spec = draw_room(BASE, case["room"], False)
    mem = spec.mem
    scr0 = bytes(mem[16384:16384 + 6912])
    rows = room_rows(plan_room(open(f"build/zxrooms/room_{case['room']:02d}.scr", "rb").read()))
    model = expected(scr0, rows)
    scen = [scr0[6144 + c] & 7 for c in range(768)]
    for frame, x, y, slot, erase, kind in case["calls"]:
        call(spec, 57415, {A: frame, E: x, D: y, H: BUF >> 8, L: BUF & 255})
        before = bytes(mem[16384:22528])
        mem[24022] = slot
        call(spec, 57194 if kind else 57058, {A: frame})
        ink = sprite_ink(mem, frame, slot, erase, kind)
        for yy in range(192):
            for cx in range(32):
                a = zx_addr(yy, cx) - 16384
                bits = before[a] ^ mem[16384 + a]
                if not bits:
                    continue
                cy = yy // 8
                k_ink = scen[cy * 32 + cx] if ink is None else ink
                pa, pb = pick(rows[cy], k_ink)
                pat = mode1_byte(pa, pb, yy & 1)
                base = cy * 512 + cx * 16 + (yy & 7)
                for off, nib in ((0, bits >> 4), (8, bits & 15)):
                    sb = nib * 0x11
                    o = model[base + off]
                    model[base + off] = (o & ~sb & 0xFF) | (pat & sb & ~litmask(o) & 0xFF)
    with open(os.path.join(OUT, f"exp_{k:03d}.bin"), "wb") as f:
        f.write(bytes(model) + bytes(mem[22528:23296]) + bytes(mem[BUF - 2:BUF_END]))
    with open(os.path.join(OUT, f"zx_{k:03d}.scr"), "wb") as f:
        f.write(bytes(mem[16384:16384 + 6912]))


def compare():
    cases = json.load(open(os.path.join(OUT, "cases.json")))
    bad = 0
    for k in range(len(cases)):
        exp = open(os.path.join(OUT, f"exp_{k:03d}.bin"), "rb").read()
        scr = open(os.path.join(OUT, f"zx_{k:03d}.scr"), "rb").read()
        bbc = open(os.path.join(OUT, f"bbc_{k:03d}.bin"), "rb").read()
        lit_bad = sum(1 for y in range(192) for x in range(256)
                      if bool(pixel(bbc, x, y)) != bool(scr[zx_addr(y, x // 8) - 16384] & (0x80 >> (x & 7))))
        attr_bad = sum(1 for i in range(768) if bbc[0x3000 + i] != scr[6144 + i])
        col_bad = sum(1 for i in range(0x3000) if bbc[i] != exp[i])
        buf_bad = sum(1 for i in range(0x3000 + 768, len(exp)) if bbc[i] != exp[i])
        if lit_bad or attr_bad or col_bad or buf_bad:
            bad += 1
            print(f"case {k} (room {cases[k]['room']}): {lit_bad} lit pixels, {attr_bad} attributes, "
                  f"{col_bad} bytes' colours, {buf_bad} bytes of 24223-{BUF_END - 1} differ")
    calls = sum(len(c["calls"]) for c in cases)
    print(f"spritecases: {len(cases) - bad} of {len(cases)} cases ({calls} calls) identical: "
          f"lit pixels, attributes, colours, and the pre-shift's bytes 24223-{BUF_END - 1}")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["make", "cmp"])
    ap.add_argument("--cases", type=int, default=40)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--edges", action="store_true", help="unclipped draws off the row's end and into the attributes")
    args = ap.parse_args()
    if args.what == "cmp":
        return compare()
    os.makedirs(OUT, exist_ok=True)
    mem = Spectrum(BASE).mem
    cases = make_cases(mem, args.cases, args.seed, args.edges)
    for k, case in enumerate(cases):
        run_case(case, k)
    json.dump(cases, open(os.path.join(OUT, "cases.json"), "w"))
    print(f"spritecases: {len(cases)} cases -> {OUT}")


if __name__ == "__main__":
    sys.exit(main())
