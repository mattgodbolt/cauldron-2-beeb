#!/usr/bin/env python3
"""The transcription's symbols (docs/how-it-works.md, "Conventions").

    python3 tools/mksyms.py build/syms.6502 build/stubs.6502 src/*.6502 build/data/*.6502

The port names things by the original's decimal addresses:

- zNNNNN: the 6502 transcription of the Z80 code at NNNNN (a routine or
  an entry point inside one). Every one referenced but not yet written
  gets a stub in stubs.6502 that stops the machine at `unwritten` with
  the address in zero page (so a run that reaches one says which), and
  the build prints how many there are.
- aNNNNN: where the original's byte at NNNNN lives on the BBC. The
  regions below say where each range went; syms.6502 defines every aNNNNN
  the sources use, as its region's label plus the offset.

Regions: (first, last, label). A label is defined by the source that
places the region (main.6502 for vars and attrs, the data files from
tools/mkdata.py for the rest).
"""
import re
import sys

REGIONS = [
    (22528, 23295, "attrs"),        # the attribute file's shadow (decision 5)
    (24000, 25099, "vars"),         # the game's variables, slots and buffers
    (25900, 34525, "r_sprites"),    # sprite graphics (sideways, GAMEDATA)
    (34526, 49510, "r_rooms"),      # tiles, blocks, layouts, tile attributes (ROOMDATA)
    (49511, 50022, "r_font"),       # the font (main RAM)
    (57726, 64194, "r_tables"),     # tables, texts, the tone table (GAMEDATA; nothing reads past 64194)
]

CODE = re.compile(r"\bz(\d{5})\b")
DATA = re.compile(r"\ba(\d{5})\b")
DEF = re.compile(r"^\s*\.z(\d{5})\b|^\s*z(\d{5})\s*=", re.M)


def strip(text):
    # Drop comments (\ and ;) but keep strings' contents out of it simply:
    # the sources don't put z/a names in strings.
    return "\n".join(re.split(r"[\\;]", line, maxsplit=1)[0] for line in text.split("\n"))


def main():
    args = sys.argv[1:]
    # --soft: stubs just return (to try what's written past what isn't).
    soft = "--soft" in args
    args = [a for a in args if a != "--soft"]
    syms_out, stubs_out, *files = args
    used_code, defined, used_data = set(), set(), set()
    for f in files:
        if f in (syms_out, stubs_out):
            continue
        t = strip(open(f, encoding="latin1").read())
        used_code |= {int(n) for n in CODE.findall(t)}
        used_data |= {int(n) for n in DATA.findall(t)}
        for a, b in DEF.findall(t):
            defined.add(int(a or b))
    with open(syms_out, "w") as f:
        f.write("\\ Made by tools/mksyms.py: where the original's addresses live. Never edited.\n")
        for n in sorted(used_data):
            for lo, hi, label in REGIONS:
                if lo <= n <= hi:
                    f.write(f"a{n} = {label} + {n - lo}\n")
                    break
            else:
                sys.exit(f"mksyms: a{n} is in no region (tools/mksyms.py REGIONS)")
    missing = sorted(used_code - defined)
    with open(stubs_out, "w") as f:
        f.write("\\ Made by tools/mksyms.py: the original's routines not yet transcribed.\n")
        for n in missing:
            f.write(f".z{n} RTS\n" if soft else f".z{n} LDA #LO({n}) : LDX #HI({n}) : JMP unwritten\n")
    if missing:
        print(f"mksyms: {len(missing)} routines not yet transcribed: "
              + " ".join(str(n) for n in missing[:20]) + (" ..." if len(missing) > 20 else ""))


if __name__ == "__main__":
    main()
