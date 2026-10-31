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
