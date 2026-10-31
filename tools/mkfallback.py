#!/usr/bin/env python3
"""What the front end and the sound use from other parts of the port,
until those parts provide it: build/data/fallback.6502.

    python3 tools/mkfallback.py build/c2.z80 build/data/fallback.6502 src/*.6502

The front end and the sound were written beside the drawing, the data
and the input, by assumption about their interfaces. So that this part
builds and runs on its own, this writes each thing it assumes that no
source defines yet, and nothing that one does:

- `r_tables`: the original's 57726-64998 in main RAM (tools/mkdata.py's
  job, with every pointer relocated; here only the pointer tables the
  front end reads, 58776 and 58784);
- `r_font`: the original's font (49511-50022);
- `key_table` (six internal key numbers: up, down, left, right, fire,
  abort) and `use_joystick`: the input's;
- `ink_logical`: the logical colour (0-3) the text printer (54363) lights
  a glyph in, by the attribute's ink (0-7): the drawing's.

Once every one is defined elsewhere the file is empty.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zxmusic  # noqa: E402

TABLES = (57726, 64998)
FONT = (49511, 50022)
POINTERS = [(58776, 2), (58784, 6)]     # word tables the front end reads


def defined(name, texts):
    pat = re.compile(rf"^\s*\.{name}\b|^\s*{name}\s*=", re.M)
    return any(pat.search(t) for t in texts)


def equb(values, per=32):
    return "\n".join("    EQUB " + ", ".join(str(v) for v in values[i:i + per])
                     for i in range(0, len(values), per))


def main():
    snap, out, *sources = sys.argv[1:]
    texts = [open(f, encoding="latin1").read() for f in sources if os.path.abspath(f) != os.path.abspath(out)]
    m = zxmusic.load(snap)
    lines = ["\\ Made by tools/mkfallback.py: what no source defines yet. Never edited.", ""]
    if not defined("r_tables", texts) and not os.path.exists(os.path.join(os.path.dirname(__file__), "mkdata.py")):
        lo, hi = TABLES
        data = list(m[lo:hi + 1])
        lines.append(f"\\ The original's {lo}-{hi}.")
        lines.append(".r_tables")
        words = {}
        for at, n in POINTERS:
            for i in range(n):
                words[at + 2 * i] = zxmusic.word(m, at + 2 * i)
        a = lo
        while a <= hi:
            if a in words:
                target = words[a]
                if lo <= target <= hi:
                    lines.append(f"    EQUW r_tables + {target - lo}")
                else:
                    lines.append(f"    EQUW {target}")
                a += 2
                continue
            run = []
            while a <= hi and a not in words and len(run) < 32:
                run.append(m[a])
                a += 1
            lines.append("    EQUB " + ", ".join(str(v) for v in run))
    if not defined("r_font", texts):
        lo, hi = FONT
        lines.append(f"\\ The original's font, {lo}-{hi}.")
        lines.append(".r_font")
        lines.append(equb(list(m[lo:hi + 1])))
    if not defined("key_table", texts):
        lines.append("\\ The input's keys: up, down, left, right, fire, abort (the defaults).")
        lines.append(".key_table EQUB &48, &68, &61, &42, &49, &70")
    if not defined("use_joystick", texts):
        lines.append(".use_joystick EQUB 0")
    if not defined("ink_logical", texts):
        lines.append("\\ The text printer's logical colour by ink.")
        lines.append(".ink_logical SKIP 8")
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
