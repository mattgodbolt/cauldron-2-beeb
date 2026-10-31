#!/usr/bin/env python3
"""The original's three tunes for src/sound.6502, read from its snapshot.

    python3 tools/mkmusic.py build/c2.z80 build/data/music.6502

Writes, under labels src/sound.6502 uses:

- each tune's two note streams as the original's bytes (signed semitones,
  64 the end), from where tools/zxmusic.py finds them;
- the original's period table (50312: half-periods in iterations of the
  96 T-state loop, indexed by note + 12; the 54th, 1, is the rest) and,
  for each entry, what sound.6502 plays for it (decision 12):
  - its SN76489 period, the beeper's pitch on the SN's 4MHz / 32 clock:
    f = 3500000 / (192 P) Hz, so N = 4000000 * 192 P / (32 * 3500000)
    = 48 P / 7, rounded;
  - where N is over the SN's ten bits (below its lowest note), the bass
    instead: a half-cycle in microseconds (P * 96 / 3.5) for the VIA
    timer that switches the channel's volume for as long as the note
    holds (decisions 12 and 18).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zxmusic  # noqa: E402

SN_MAX = 1023                   # the SN76489's ten bits
CLOCK = 3500000
# The tunes in the order sound.6502 indexes them: its X 0, 1, 2 are the
# players at 50100, 51400, 51850.
TUNES = (1, 2, 3)


def sn_period(p):
    return (48 * p + 3) // 7


def half_us(p):
    return (p * 96 * 1000000 + CLOCK // 2) // CLOCK


def equb(values, per=16):
    out = []
    for i in range(0, len(values), per):
        out.append("    EQUB " + ", ".join(str(v) for v in values[i:i + per]))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("snap")
    ap.add_argument("out")
    args = ap.parse_args()
    m = zxmusic.load(args.snap)
    lines = ["\\ Made by tools/mkmusic.py from the original's snapshot. Never edited.", ""]
    tunes = [zxmusic.Tune(m, n) for n in TUNES]
    table = tunes[0].table_bytes
    for t in tunes[1:]:
        assert t.table_bytes == table, "the three copies' tables are the same"
    lines.append(f"\\ The period table ({tunes[0].table}), by note + 12.")
    lines.append(".mus_periods")
    lines.append(equb(table, 18))
    sn, half = [], []
    for p in table:
        n = sn_period(p)
        if p == 1:
            sn.append(0)
            half.append(0)
        elif n > SN_MAX:
            sn.append(1)
            half.append(half_us(p))
        else:
            sn.append(n)
            half.append(0)
    lines.append("\\ What each entry plays: the SN's period (0 the rest, 1 the bass's),")
    lines.append("\\ the bass's half-cycle in microseconds.")
    for name, vals in (("mus_sn_lo", [v & 255 for v in sn]), ("mus_sn_hi", [v >> 8 for v in sn]),
                       ("mus_half_lo", [v & 255 for v in half]), ("mus_half_hi", [v >> 8 for v in half])):
        lines.append(f".{name}")
        lines.append(equb(vals, 18))
    lines.append(f"MUS_ENTRIES = {len(table)}")
    lines.append("")
    for i, t in enumerate(tunes):
        for c, ch in enumerate(t.channels):
            lines.append(f"\\ Tune {t.number} ({t.name}), channel {c + 1}: {ch['start']}-{ch['end']}, "
                         f"looping to {ch['loop']}.")
            lines.append(f".mus_t{t.number}_ch{c + 1}")
            lines.append(equb([b & 255 for b in ch["notes"]] + [zxmusic.END]))
    lines.append("")
    lines.append("\\ Each tune's streams, by sound.6502's X.")
    for c in (1, 2):
        lines.append(f".mus_start{c}_lo EQUB " + ", ".join(f"LO(mus_t{t.number}_ch{c})" for t in tunes))
        lines.append(f".mus_start{c}_hi EQUB " + ", ".join(f"HI(mus_t{t.number}_ch{c})" for t in tunes))
    with open(args.out, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
