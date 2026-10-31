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

## 2026-10-31: sound and the front end

- The music player's decisions on the SN76489: a tick every 3 frames (2
  for a double rest), each note sounding 2 frames, the notes below the
  SN's floor as software bass on the System VIA's timers (decision 12).
  The player's interrupt handler goes on IRQ1V only while the music
  plays and takes itself off when the steps stop, since the SN rings on
  where the beeper falls silent.
- `make music` compares every note of each tune with `zxmusic.py`'s
  decode, from the chip's bytes in jsbeeb. It found: `sound_init`
  clobbering X on the first call (tune 1 played tune 3's pointers), a
  period compare that lost the low byte, the bass's first half-cycle
  long by the edge interrupt's latency (now timed shorter), and T2's
  restart overhead.
- The effects as the beeper's own pulses: channel 2 at period 1, its
  volume on for the pulse's width (decision 13). Timed against 4v
  T-states.
- The menu in the BBC's idiom, the keys' names shown (decisions 14 and
  9). `make front` runs it on a test build with a stand-in printer:
  define keys, the defaults, the joystick, game over and the win.
- A palette program with no splits leaves the User VIA's T1 running from
  the screen before, so stale splits land mid-screen: the front end's
  palettes carry one split that changes nothing, until `set_palette`
  stops T1 itself.

## 2026-10-31: the layers merged

- Four agents transcribed in worktrees: drawing and data, the game and
  objects, the player and input, the front end and sound. Merging them
  found four routines written twice (53101, 56811, 57714, 53798), two
  names for the keys' table, and the front end's colours built but never
  shown. Decisions renumbered 12-15.
- With nothing stubbed the code no longer fitted under the title from
  `&1900`: decision 16 packs it with baron's zx02 transform, and the font
  moved to GAMEDATA. Main RAM is now full.
- A room took 43 frames to draw, every tile byte through the general
  Spectrum-address writer; drawn straight into its cell, 17.
- `make passes`: all nine scenarios agree with the original on every
  byte of 24000-25099 at every pass, on the B and the Master, once 24000
  (the explosion's frame count, the interrupt's) is left out. Eight
  fuzzed scenarios of 400 passes agree too.
- The BBC takes 1.4-1.7 times the original's frames a pass (2026-10-31):
  the sprites' pre-shift and XOR, under optimisation.
- `tools/fuzz.py --count 12 --seed 2 --passes 1500`: all agree (up to
  ten rooms crossed, down to one life). fuzz2_0 is kept as a scenario.

## 2026-10-31: the sprite drawing made fast

- `make passes` gives each pass's frame; the port took 1.36-1.70 times
  the original's frames over the scenarios (idle79 1.36, right56 1.70).
  A sampling profiler (PC every 397 cycles in play) put most of the
  compute in the pre-shift and the XOR's per-byte address translation.
- The XOR a run at a time (`xor_run`): a line's bytes along a cell row
  are ours 16 apart on one character row and line, so the address, the
  scenery-ink row and the pattern row are worked out once. The patterns
  are indexed row * 8 + ink, so a cell's ink indexes them directly. The
  clipped draw picks its run once per call, as the original's count down
  would. Then `xor_down`/`xor_lines`: the next line down in a character
  row reuses the line above's working; and the mixed case (an erase's,
  mostly) inline.
- The pre-shift in one pass: k one-bit passes of the stream and its
  carry turn a ring of 16 * words + 1 bits right by k, so each byte
  takes the low k bits of the one before, the first the last byte's
  ASLed (checked against the k passes in Python, then by `make
  sprites`). Then fused with the copy: the image shifted as it's copied,
  the stream's bytes past the buffer in place after. Frames of 128-255
  bytes reach 256 or so bytes past their buffer (the signed halving), on
  the original too.
- Room for it: the sprite routines that read GAMEDATA's tables run from
  GAMEDATA (decision 17).
- Every check identical throughout (`make sprites` also at 200 cases of
  seed 7). Frames per pass against the original's, 2026-10-31: fire56
  1.073, idle110 1.097, idle56 1.087, idle79 1.071, idle97 1.170, left56
  1.068, leftright97 1.063, right56 1.078, updown10 1.073.
- Not at 1 yet. With the XOR and the shift stubbed out (results then
  differ), idle56 ran at 0.77 of the original's frames but idle79 still
  at 1.00: there the still slots' busy waits set the pace, and our
  per-object work spills past a VSync where the original's doesn't. By
  instruction timings the XOR is still several times the Z80's per byte
  (colour costs a read, masks and a pattern); the pre-shift about the Z80's.

## 2026-10-31: where the frames go, and the interrupt

- `make timeline` (tools/zxtimeline.py, tools/timeline.mjs,
  tools/timecmp.py) logs every wait for a frame on both machines, pass
  by pass, with the work before each charged to the routines on the
  call stack; a wait that ends a frame later here than on the original
  is a frame lost. `make passes` ends with each scenario's frames
  against the original's (tools/framecmp.py).
- A frame is lost where the work since the last wait ran past a VSync
  the original's didn't: over the scenarios (2026-10-31) 1577 at the
  mover's HALT (56256), 186 at the heads' (53727, 53771), 146 at the
  room's (54509, its drawing) and 13 at 54225. In idle97 the original's
  15-19ms of work between two of the mover's waits is 21-26ms here.
  Against the original's time: the XOR (57058, 57194) 2.3-2.8 times,
  the heads (53651, their XOR) 1.4, the player's collision (54530 1.3,
  55095 1.5), the interrupt several times; the pre-shift (57415)
  0.7-0.9 and the still slots' waits the same. Lost frames with no
  still slot in their work (idle56, right56, fire56) are the XOR's
  alone.
- The interrupt took about 850us a frame against the original's 70:
  57664 saved and restored the registers' zero page every frame, and
  each screen carried a split that changed nothing so that split 0 landed
  at line 8. Now the tune is called without HL (nothing at VSync touches
  the registers), VSync's T1 count reaches the first split wherever it
  is (`split_count`), and a split reads one record: about 500us. Every
  displayed line's palette is unchanged (title, menu, game, all 128
  rooms, sampled mid-line in jsbeeb before and after).
- The hook now runs before VSync's palette writes: `make music`'s bass
  medians (5 half-cycles a note) had hung on where the tick's strike
  fell against the title's splits.
- 55095 tests a unit's two pixels in the one byte of ours they're in,
  the row's address worked out once.
- The still slot's wait (`wait_us`) measures 7626-7666us here, the
  original's 7608us plus its interrupt when one lands in the loop: as
  it should be.
