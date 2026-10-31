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

## 2026-10-31: the player and the input

- The controls byte's bits checked against the code, not the notes:
  KEMPSTON_MAP (57744) turns R=1 L=2 D=4 U=8 into 8, 4, 2, 1, the
  Interface II table (57760) gives 9, 8, 6, 7 (Sinclair's up, down,
  left, right) the bits 1, 2, 4, 8, and MOVE_UP runs on direction bit 0.
  So bit 0 is up, 1 down, 2 left, 3 right: player.md has it right,
  core.md's "bit 0 right, 1 left, 2 down, 3 up" is the Kempston port's
  own order.
- The readers are the original's two (decision 6) behind its vector at
  57726; 52775's abort follows the call, as the pushed return did.
- The player (53149, 53163, 53221, 54513-55284) transcribed with (IX+n)
  as `a24077+n`, since IX is always the player there. The row loops'
  PUSH/POP around TEST_ROW became a save and a restore that keeps the
  flags (PLA would lose them).
- `tools/playertest.py` runs the original on the simulator and the port
  on py65 from the same state each pass (the screen's lit pixels laid
  out as ours, the attributes, variables and tables), compares the
  player's variables and the calls made, and perturbs the state now and
  then (odd directions, a stale deadly 24014, random pixels with a solid
  attribute under the pumpkin) until every instruction of the original's
  player code has run. The readers are compared for every input. No
  differences. The routines others own that the player calls (57307,
  57326, 57355) are the test's own Python, from the original's code.

## 2026-10-31: the data and the drawing

- `tools/mkdata.py` writes the original's regions with every pointer
  word relocated (the tables found from the code's word lookups: the
  frame table, the bank and monster lists, the scripts, the handlers,
  the texts, the controls vector, the interrupt's tunes; the clipped
  draw's sink 24995 among the screen lines). Two sideways banks,
  GAMEDATA and ROOMDATA, filled by a LOADER after cauldron-beeb's
  (decision 9). ROOMDATA had no room for a copy of all the bank lists,
  so room entry copies the room's one.
- Colour, planned before writing any 6502 (decisions 10 and 11): the
  rooms' rows show at most three inks in 1916 of 1920 rows, but keeping
  yellow on every play row for the pumpkin leaves two, which 49 rows
  outrun. A dynamic programme over the rows with one change a boundary
  shows 99.60% of lit pixels in their own colour, within 0.03% of
  changing freely; dithers cover most of the rest.
- What the original shows a monster in isn't its frame attribute: the
  attribute is XORed onto the room's 70, so 69 (cyan) shows magenta.
  The port's sprite colour is what the original shows over the empty
  room.
- The drawing transcribed (draw.6502, room.6502). The pre-shift's stack
  trick became a ROR stream over the same bytes; reading it for that
  showed the stream runs 256 bytes long for frames of 128 bytes or more
  (research correction in core.md).
- The room hides while it draws by the CRTC's R6 (rows displayed), the
  palette not having enough splits to blank three colours at once.
- `make rooms`: every room (and the panel) identical to the original's
  drawing: lit pixels, attributes and the planned colours, on the B and
  the Master. `make sprites`: random calls of 57058 and 57194 on both
  machines, identical (lit pixels, attributes, colours, the pre-shift's
  bytes).
