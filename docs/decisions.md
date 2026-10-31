# Decisions

Every call the port makes that the original didn't, numbered, with the
date and the reason. Nothing is changed from the original quietly.
**Provisional** marks a call made while Matt was away, for their review:
it stands until they say otherwise, and the options are kept beside it.

## 1. The specification and the questions BRIEF.md asks (2026-10-31, provisional)

Matt asked for the port to run on its own, so BRIEF.md's questions take
Cauldron 1's answers until Matt says otherwise:

- **The specification** is Palace's 48K Spectrum release, the TAP of ZXDB
  entry 851 (`tools/fetch_original.sh`, checked by `tools/SHA256SUMS`).
  The C64 version, though first and 6502, isn't used: the Spectrum's is
  the one the harness runs headless.
- **Targets:** a Model B with sideways RAM and the Master 128, from one
  disc. How much sideways RAM is measured once the data's converted.
- **Colour:** no clash (cauldron-beeb's decision 5).
- **Keys:** the BBC's usual ones (decision 6).
- **Rights:** unofficial; the original is fetched, never committed.
- **The remote:** commits stay local until Matt pushes; the disc at the
  root (`cauldron2.ssd`) is rebuilt with each change worth trying.

## 2. MODE 1 in the Spectrum's geometry (2026-10-31, provisional)

As cauldron-beeb's decision 2, CE2 and nm: MODE 1's pixels with the CRTC
narrowed to 256 x 192, 12K at the top of main RAM, a character row 512
bytes. The art is the same artist's fine single-pixel detail as
Cauldron 1's; MODE 2 would halve it.

## 3. Colour: a palette program per screen (2026-10-31, provisional)

MODE 1 shows black and three inks; the original shows up to seven. Each
screen gets a palette program (`irq.6502`'s `set_palette`): the palette
at VSync, then splits down the screen, each changing one logical colour
in a horizontal blank, at least two lines apart (the interrupt latches
the period of the split after next). `tools/mkscreen.py` chooses them
from the original's pixels: the most lit pixels in their own colour,
then the fewest splits. A lit pixel whose colour its line hasn't got
shows in the nearest the line has; lit pixels stay lit.

The split timing (`SPLIT_ADJ`) is cauldron-beeb's sweep (its decision 4,
the same geometry and handler), to sweep again here.

The title (the tape's SCREEN$): nine splits, 6705 of its 6802 lit pixels
in their own colour (2026-10-31). The rest are on lines that show five
colours.

## 6. Controls (2026-10-31, provisional)

The original reads a Kempston joystick (52658) or six keys (52695, the
Interface II's 6-0 and A to abort by default, redefinable), through the
vector at 57726 that its menu sets. The port keeps the vector and both
readers, each making the original's controls byte (1 up, 2 down, 4 left,
8 right, 16 fire/bounce, 64 abort; opposite directions cancel):

- **Keys** (52695): the BBC's usual ones, as cauldron-beeb's decision 9
  and CE2: **Z** left, **X** right, **:** up, **/** down, **RETURN**
  fire/bounce, **ESCAPE** abort. They are a table of internal key
  numbers (`input.6502`'s `keys`, with `keys_default` and `reset_keys`)
  in the original's order, for the front end's redefine screen.
  Read from the System VIA's matrix, ESCAPE included: the game owns the
  machine, and the OS never sees it.
- **Joystick** (52658, the Kempston's place): the analogue port, X and Y
  from the ADC polled one channel a read (thresholds a quarter from
  each end), fire from the System VIA's PB4, mapped through the
  original's KEMPSTON_MAP. The ADC is at &FEC0 on the B and &FE18 on the
  Master: `joy_init` picks by OSBYTE 0 and has to run before the game
  takes the machine over. The original's Kempston abort is the A key
  alone in its half-row; the port's is the key table's abort key.
- **Abort** (52767/52775): the original pushes 52775 as the reader's
  return, so any read with the abort bit restarts at 52235, which
  resets the stack. The port calls the reader, then 52775 tests the bit
  and jumps to 52235, which must reset the 6502's stack likewise.

Options kept: an OS-style ESCAPE (it would need the OS's keyboard
interrupt, which the game turns off); a digital (user port) joystick
in place of the analogue one.

## 7. The random pointer walks main RAM, seeded from the VSync count (2026-10-31, provisional)

The original's only randomness is the start room: the byte at the
pointer 61248, which the interrupt and the attract loop step and 52235
seeds from R. The port keeps the pointer and its stepping, but:

- R doesn't exist: the low byte is seeded from `vsyncs`, which, as R,
  depends on how long the menu took.
- The byte read at 52372 is at the pointer with bit 15 cleared, in main
  RAM: the Spectrum's bytes at 57600 onwards (code, then tables, then
  the ROM) aren't the BBC's, and a read from the I/O pages can
  acknowledge an interrupt.

Options kept: a seeded generator of the port's own; or reading the
original's tables only (the pointer taken modulo their length). The
oracle forces the start on both machines (`tests/scenarios.txt`), so
none of this shows there.

## 8. The original's DI ... EI pauses the frame interrupt's work, not the interrupt (2026-10-31, provisional)

The original turns interrupts off around starting a tune (53101, 56811)
and printing a credits page (52316), so its interrupt (57664) neither
steps the random pointer nor plays the tune meanwhile. The BBC's
interrupt also runs the palette program, which must go on, so `DI`
sets `hook_off` (game.6502) and the 57664 hook does nothing while it
is set; `EI` clears it. It starts set, until 52235's `EI`.

## 9. Memory: two sideways RAM banks (2026-10-31, provisional)

The original's data goes where docs/how-it-works.md's table says, as
`tools/mkdata.py` writes it (the original's bytes, every pointer word
relocated):

| | Holds | Size (2026-10-31) |
|---|---|---|
| GAMEDATA, sideways | sprites 25900-34525, tables 57726-64998 | 15899 bytes, 485 free |
| ROOMDATA, sideways | tiles, blocks, layouts, tile attributes 34526-49510; the rooms' colour plans (decision 11) | 16265 bytes, 119 free |
| main RAM | the font 49511-50022, the code, the tables the drawing makes | code to &3732, workspace to &4600, 2560 bytes free below the screen |

`LOADER` (run by `!BOOT`) loads each file at &1900 and copies it to the
highest sideways RAM bank that had no ROM at start-up and holds a
flipped byte, leaving the banks' numbers in `game_bank` and
`room_bank`; with fewer than two it says "Cauldron II needs 32K of
sideways RAM" and stops. GAMEDATA stays paged in; the room drawing
pages ROOMDATA in for its tile loop only (`page_rooms`, `page_game`).
The frame interrupt keeps whichever is in (57664, game.6502).

So the targets are a Model B with 32K of sideways RAM and the Master
128 (measured on jsbeeb's B-DFS1.2 and Master: banks 7 and 6 there).
Fitting 16K is later work: the rooms' data alone is most of a bank.

One change of layout: the room's tile-bank list (62954-63497) is in
GAMEDATA with the other tables, and the room drawing needs it while
ROOMDATA is paged in. A copy of all the lists in ROOMDATA doesn't fit
(544 bytes, 119 free), so room entry copies the one room's list
(`bank_list`, at most `BANK_LIST_MAX` bytes) to main RAM first. Likewise
54464 makes the character-row table's (58883) address by arithmetic,
the same values, as it runs with ROOMDATA in.

## 10. Colour: a sprite's own colour, and the scenery's coming back (2026-10-31, provisional)

The lit pixels are exactly the original's; their colour is the port's
(as cauldron-beeb's decision 5: no clash). Each character row has a
palette (decision 11), and each Spectrum ink a pattern on each row
(`make_patterns`, room.6502, the same rule as `tools/colours.py`'s
`pick`): the ink's own colour if the row has it; else an ordered dither
(a b a b, b a b a on the next line) of two of the row's colours that
add up to it, magenta from red and blue; else the nearest. Black ink,
which a lit pixel can't be, shows as white. BRIGHT is ignored; the one
non-black paper (room 111's three cells of attribute 12, green on
blue) shows black, since an unlit pixel must stay unlit.

Scenery (54464: tiles and text) is drawn in its cell's ink, kept per
cell (`scen_ink`). A sprite's XOR lights pixels in:

- drawing (`xor_erase` 0): the colour the original shows the frame in
  over the room's empty cells (attribute 70), its frame attribute (60422)
  EOR 70: 69 shows magenta, 67 cyan, 65 and 1 white, 68 and 4 red. A
  frame without an attribute shows its cell's colour on the Spectrum,
  so here too: its cell's scenery ink; except the pumpkin (slot 0),
  which is yellow, as on the Spectrum over the empty room.
- erasing (`xor_erase` non-zero: the mover's XOR of the old image):
  the scenery ink of each cell, so what was under the sprite comes back
  in its colour.

A lit pixel the XOR leaves lit keeps its colour; one it clears is black.
The attribute shadow is exactly the original's (57194 XORs the frame
attribute into it). Options kept: the frame attribute's own ink (69
cyan rather than magenta), which is what the original's data says but
not what it shows.

`make sprites` checks it: 40 cases of 4-12 random calls (any frame;
57058 in every slot, so the clipped draw at all four edges and the
sink; 57194 straight, panel rows too; drawn and erased) on the original
and the viewer, from the room as each draws it: lit pixels, attributes,
every screen byte's colour against the rule, and the pre-shift's bytes
24223-24899, all identical (2026-10-31; 200 cases of another seed
likewise).

## 11. Colour: a palette a character row, planned per room (2026-10-31, provisional)

MODE 1 shows black and three colours a line. The panel's rows (0-3)
have a fixed palette: yellow, magenta, green, with logical 2 red on row
2 and cyan on row 3: exactly the inks the panel shows. In rows 4-23
logical 1 is yellow everywhere (the pumpkin's colour, and the empty
cells' ink, 70); logical 2 and 3 are the room's, and at most one of the
two changes at each row boundary, a palette split (irq.6502) at the
boundary. `tools/colours.py` plans each room from the original's own
drawing of it (tools/zxrooms.py): a dynamic programme over the rows,
lit pixels in their own colour first, exact dithers next, fewest
splits last. The plans are 10 bytes a room in ROOMDATA (`room_plans`);
room entry makes the palette program (`make_program`) and the patterns
from it.

Measured over all 128 rooms (rows 4-23, 2026-10-31):

| | Lit pixels in their own colour |
|---|---|
| This plan (yellow kept, one change a boundary) | 729337 of 732241, 99.60%; 660 dithered exactly, 2244 the nearest; 297 splits |
| Yellow kept, any changes at a boundary | 99.63% |
| Three free colours a row | 99.98% |

`make rooms` draws every room in the viewer and finds the lit pixels,
the attributes (panel included) and every byte's colour identical to
the original's drawing through this plan.

The original hides a room while it draws by zeroing its attributes
(54213) and shows it by copying them after a HALT (54499). Here 54213
sets the CRTC to show only rows 0-3 (R6 = 4), and 54499, after a
VSync, installs the room's palette program and shows all 24 rows. The
palette can't blank the play area cleanly: three logical colours would
need three splits at one boundary.
