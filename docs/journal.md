# Journal

How the port got here, in order: what worked and what didn't.

## 2026-10-31: the start

- Read BRIEF.md, `../porting-to-the-beeb.md` and the siblings. Matt asked
  for the port to run on its own; BRIEF.md's questions took Cauldron 1's
  answers, provisionally (decision 1).
- Fetched the TAP (ZXDB 851). `tap2sna.py --press 7:SPACE -s 52180` makes
  the entry snapshot; `tools/zx.py` (cauldron-beeb's) runs it unchanged.
  A game starts with Kempston: menu 1, 4, then fire.
- An executed-code map from a short fuzzed play, through `sna2ctl.py -m`,
  gave a first control file: code at 50100-50336 and 52180-57725, and a
  call graph that split the research four ways (core and drawing, the
  player, monsters and objects, the front end and sound), one agent each.
- The screen layer: MODE 1 in the Spectrum's geometry, the tape's SCREEN$
  as the title, with cauldron-beeb's per-line palette planner
  (`tools/mkscreen.py`). The planner put two splits on adjacent lines,
  which the interrupt can't do; it now carries the lines since the last
  split in its state and never does.

## 2026-10-31: the game logic and the objects

- Transcribed the game (52180-53858, 56700-57616, the interrupt's work
  57664) and the objects (54229, 54264, 55285-56966) into
  `src/game.6502` and `src/objects.6502`, by z-name, from a raw
  disassembly of 52180-57725 (the control files leave 52180 and
  52372-52478 as data).
- The mover's `EI : HALT` is `wait_vsync`; its still-slot loop is
  `wait_us` for the loop's T-states (`dec_bc_us`). It tells the
  drawing's XOR which image it is drawing through `xor_erase`.
- The interrupt's DI/EI became a flag (decision 8); the random pointer
  walks main RAM (decision 7).
- The pass-by-pass oracle: `tools/zxpass.py` runs the original through a
  scenario (`tests/scenarios.txt`) logging 24000-25099 and the
  self-modified table bytes at each pass, `tools/beepass.mjs` the same
  on the disc, `tools/passcmp.py` names the first difference;
  `make passes` runs them all. The Spectrum side runs every scenario;
  the BBC side stops at the first unwritten routine (the title tune,
  50100) until the other layers land.
- Research correction: Spawn (55363) doesn't keep BC.
