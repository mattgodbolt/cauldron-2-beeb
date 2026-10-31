#!/usr/bin/env python3
"""The port's colour (decisions 7 and 8): the rule that picks how a
Spectrum ink shows on a row whose three inks are given, and the planner
that gives each room's rows their inks. Shared by tools/mkdata.py (which
writes each room's plan into ROOMDATA) and tools/roomcmp.py (which checks
what the BBC drew against the original's pixels through the same rule).
src/room.6502's make_patterns is the same rule in 6502.

A row shows black and three inks, logical 1-3. Rows 0-3 are the panel's,
fixed (PANEL_ROWS). In rows 4-23 logical 1 is yellow everywhere (the
pumpkin's colour, and the empty cells' ink, 70); logical 2 and 3 are the
room's, and from one row to the next at most one of them changes (a
palette split at the row boundary, src/irq.6502).

A Spectrum ink the row lacks is an ordered dither of two of its inks
whose colours add up to it (magenta = red + blue), or else the nearest:
`pick` scores every pair of logical colours.

    .venv/bin/python tools/colours.py   # the plan's figures over all rooms
"""
import collections
import os
import sys

# Spectrum colour (GRB order: 0 black, 1 blue, 2 red, 3 magenta, 4 green,
# 5 cyan, 6 yellow, 7 white) -> BBC physical colour (RGB order: 1 red,
# 2 green, 4 blue).
ZX_TO_BBC = [0, 4, 1, 5, 2, 6, 3, 7]
BBC_RGB = [((c & 1) * 255, (c >> 1 & 1) * 255, (c >> 2 & 1) * 255) for c in range(8)]
POP = [bin(i).count("1") for i in range(8)]
YELLOW = 3          # BBC physical
# The panel's rows (BBC physical colours of logical 1-3): the inks the
# original's panel shows, measured from its screen: row 0 green; row 1
# yellow, magenta, green; row 2 yellow, red, green; row 3 yellow, green,
# cyan. One change a row boundary (logical 2).
PANEL_ROWS = [(3, 5, 2), (3, 5, 2), (3, 1, 2), (3, 6, 2)]
# The pairs pick tries, in order (a tie keeps the first).
PAIRS = [(1, 1), (2, 2), (3, 3), (1, 2), (1, 3), (2, 3)]


def pick(pal, ink):
    """The logical pair (a, b) that shows Spectrum ink `ink` on a row whose
    logical 1-3 are BBC colours pal: a == b is solid, else a dither (a on
    even pixels of even lines). Ink 0 (black, which a lit pixel can't be)
    shows as white."""
    p = ZX_TO_BBC[ink] or 7
    best = None
    for a, b in PAIRS:
        qa, qb = pal[a - 1], pal[b - 1]
        score = 4 * POP[(qa | qb) ^ p]
        if a != b:
            score += 1 + 2 * POP[qa & qb]
        if best is None or score < best[0]:
            best = (score, a, b)
    return best[1], best[2]


def quality(pal, ink):
    """0: shown in its own colour; 1: dithered from two whose colours add
    up to it exactly; 2: anything else."""
    a, b = pick(pal, ink)
    p = ZX_TO_BBC[ink] or 7
    if a == b:
        return 0 if pal[a - 1] == p else 2
    return 1 if (pal[a - 1] | pal[b - 1]) == p and not pal[a - 1] & pal[b - 1] else 2


def mode1_byte(a, b, odd):
    """A MODE 1 byte, four pixels: a b a b on an even line, b a b a on an
    odd one (logical colours)."""
    def cbyte(c):
        return (c & 2) * 0x78 + (c & 1) * 0x0F
    if odd:
        a, b = b, a
    return (cbyte(a) & 0xAA) | (cbyte(b) & 0x55)


def scr_cell_byte(scr, y, cx):
    return scr[((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2) + cx]


def row_counts(scr, r):
    """Lit pixels by Spectrum ink in character row r of a SCREEN$."""
    c = collections.Counter()
    for cx in range(32):
        ink = scr[6144 + r * 32 + cx] & 7
        n =sum(bin(scr_cell_byte(scr, r * 8 + i, cx)).count("1") for i in range(8))
        if n:
            c[ink] += n
    return c


def plan_room(scr):
    """Logical 2 and 3's BBC colours for rows 4-23 of a room's SCREEN$:
    each row's inks shown best (own colour, then exact dither), at most
    one of the two changing from a row to the next, starting from the
    panel's last row. Returns 20 (l2, l3) pairs."""
    counts = [row_counts(scr, r) for r in range(4, 24)]
    colours = range(1, 8)
    states = [(a, b) for a in colours for b in colours if a != b]
    COST = (0, 1, 3)

    def cost(r, s):
        pal = (YELLOW,) + s
        # (ties: fewest changes come from the DP's order; prefer stable)
        return sum(n * COST[quality(pal, ink)] for ink, n in counts[r].items())
    start = PANEL_ROWS[3][1:]
    best = {}
    for s in states:
        if s == start or s[0] == start[0] or s[1] == start[1]:
            best[s] = (cost(0, s) * 4 + (s != start), None)
    trail = [best]
    for r in range(1, 20):
        nxt = {}
        for s in states:
            c_here = cost(r, s) * 4
            for p, (c, _) in best.items():
                if p != s and p[0] != s[0] and p[1] != s[1]:
                    continue
                c2 = c + c_here + (p != s)
                if s not in nxt or c2 < nxt[s][0]:
                    nxt[s] = (c2, p)
        best = nxt
        trail.append(best)
    s = min(best, key=lambda k: best[k][0])
    out = [None] * 20
    for r in range(19, -1, -1):
        out[r] = s
        s = trail[r][s][1]
    return out


def room_rows(plan):
    """All 24 rows' logical 1-3 colours for a room's plan."""
    return list(PANEL_ROWS) + [(YELLOW,) + tuple(p) for p in plan]


def pack_plan(plan):
    """A plan as ROOMDATA holds it: 20 nibbles, one per row 4-23, the
    change at the boundary above it: 0 none, else bit 3 the logical
    colour (0: 2, 1: 3) and bits 0-2 its BBC colour. Two a byte, the
    first in the high nibble."""
    prev = PANEL_ROWS[3][1:]
    nib = []
    for s in plan:
        if s == prev:
            nib.append(0)
        elif s[0] != prev[0]:
            assert s[1] == prev[1]
            nib.append(s[0])
        else:
            nib.append(8 | s[1])
        prev = s
    return bytes(nib[i] << 4 | nib[i + 1] for i in range(0, 20, 2))


def shares(scr, rows):
    """(own, dithered, lit) lit pixels of rows 4-23 by quality."""
    tot = [0, 0, 0]
    for r in range(4, 24):
        for ink, n in row_counts(scr, r).items():
            tot[quality(rows[r], ink)] += n
    return tot[0], tot[1], sum(tot)


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "build/zxrooms"
    tot = [0, 0, 0]
    splits = 0
    for room in range(128):
        scr = open(os.path.join(d, f"room_{room:02d}.scr"), "rb").read()
        plan = plan_room(scr)
        splits += sum(1 for n in pack_plan(plan) for k in (n >> 4, n & 15) if k)
        o, dd, lit = shares(scr, room_rows(plan))
        tot[0] += o
        tot[1] += dd
        tot[2] += lit
    print(f"rooms 0-127, rows 4-23: {tot[0]} of {tot[2]} lit pixels in their own colour "
          f"({100 * tot[0] / tot[2]:.2f}%), {tot[1]} dithered exactly, {tot[2] - tot[0] - tot[1]} nearest; "
          f"{splits} splits in all")


if __name__ == "__main__":
    main()
