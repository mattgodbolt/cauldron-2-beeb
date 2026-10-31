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
- **The remote:** each step is pushed to GitHub as it lands (Matt's
  request, 2026-10-31); the disc at the root (`cauldron2.ssd`) is rebuilt with each change worth trying.

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

## 12. The music on the SN76489 (2026-10-31, provisional)

The original's three tunes are a two-channel beeper player run one tick
per frame interrupt (`docs/research/sound.md`). The port keeps its
decisions (`src/sound.6502`, the streams and period table copied from
the snapshot by `tools/mkmusic.py`):

- **Tempo:** a tick every 3 frames, 2 when both channels rest, as the
  original's 2.11-frame tick with the interrupts off makes it. 57664
  steps the tune every frame through the original's entries (50113,
  51863, 51413), which count the frames.
- **Articulation:** each note struck again every tick, sounding 2
  frames of its 3 (the original's 2.11 of 3; a frame is the step's
  grain). *Superseded by decision 18: each note held for its length.*
- **Pitch:** the beeper's, f = 3500000 / (192 P), as the SN's period
  48P / 7, rounded. Tune 2's notes all fit; tune 1's channel 2 has 80 of
  its 512 ticks below the SN's lowest note (122Hz; down to 94.9Hz) and
  tune 3 19 of its two channels' 52 (down to 71.5Hz).

The notes below the SN's floor, the options:

| | Pitch | Cost |
|---|---|---|
| **A. Software bass** (chosen) | exact | the channel at period 1 (inaudible), its volume switched each half-cycle by the System VIA's T1 (tune channel 2) or T2 (channel 1), as nm's bass (its decision 18); an interrupt per half-cycle (at most two channels, 71-122Hz: under 500 a second) |
| B. Each low note an octave up | an octave wrong | none; but tune 3's falling chromatic line jumps up an octave halfway down, and tune 1's bass line breaks |
| C. The whole tune an octave up | the tune's shape kept, an octave high | none; tune 1's bass loses its depth |
| D. Periodic noise clocked by channel 2 | depends on the chip's shift register (15 or 16 bits) | CE2's bass was silent on Matt's machine |

A's interrupt handler (`mus_irq`) goes onto IRQ1V ahead of
`irq_handler` while the music plays, and comes off by itself two VSyncs
after the steps stop (24002 = 0), silencing the music: the original's
beeper falls silent when its player isn't called, the SN's tones would
ring on. So in play nothing is added to the interrupt's path. An edge
waits while VSync's interrupt runs, so a half-cycle can be late by that
much; the next is timed from when it was due.

`make music` checks every note of each tune against `tools/zxmusic.py`'s
decode of the original, from the chip's bytes in jsbeeb: its frame, its
period, its two frames, a bass note's half-cycles and their spacing.

## 13. The effects as the beeper's pulses (2026-10-31, provisional)

Every effect in the original is a train of single speaker pulses
(52854): the sweeps (52791) one a main-loop pass, the explosion (57714)
one a frame, the cackle (53798) two a frame. The pitch heard is the
rate of the calls; the pulse's width (4 x the word at 64027 T-states,
1.2-15ms) sets the timbre.

| | |
|---|---|
| **A. The same pulse on the SN** (chosen) | channel 2 at period 1, its volume on for the pulse's width and off: the beeper's waveform, the calls' rate the pitch, the width timed by a loop as the original's (an interrupt lengthens it as one did) |
| B. A tone burst at the pulse's pitch, 1 / (2 x width) | 33-430Hz: mostly below the SN's lowest note, and a different sound: a tone where the original clicks |
| C. A noise burst for the width | nothing of the original's timbre |

Effects and music don't share a channel. The chip's writes from the main
program are single volume bytes with the interrupts off, so an
interrupt's write never comes between a latch and its data. A pulse from
the main program holds `sfx_busy`; the interrupt's explosion pulse then
skips its writes but keeps its time (the original's would end the main
program's pulse early). `make music` times pulses of six effects against
4v T-states.

## 14. The menu and the keys in the BBC's idiom (2026-10-31, provisional)

The original's menu (52481) offers its machine's controls: 1 Kempston,
2 Interface II (fixed keys 6-0), 3 keyboard (define six), 4 play. The
port keeps its look (title, attributes, layout) and its decision, a
choice of controls before the credits, in the BBC's terms
(`src/frontend.6502`):

| Port | Original's | Does |
|---|---|---|
| 1 KEYBOARD | 2 INTERFACE II | the fixed default keys: `:` up, `/` down, Z left, X right, RETURN fire, ESCAPE abort |
| 2 JOYSTICK | 1 KEMPSTON | the analogue joystick (`use_joystick`); abort stays a key |
| 3 DEFINE KEYS | 3 KEYBOARD | six keys of the player's |
| 4 PLAY GAME | 4 PLAY GAME | as it is |

Defining keys keeps the original's wait (52610: a key held 256 reads in a
row, then released 256 in a row, any key, one already chosen too) and
its prompts (58784), but each prompt on a row of its own with the BBC's
name for the key chosen beside it, where the original overwrote one
row: so the player sees what each key is, which the original's
half-row bits never needed. Keys are internal key numbers in
`key_table` (up, down, left, right, fire, abort), read from the System
VIA. The names are the printer's characters: digits, capitals, space,
`-` `/` `^`, and words for the rest (COLON, RETURN, SHIFT LOCK).

## 15. The front end's colours (2026-10-31, provisional)

The original's front-end screens are text on black paper with at most
three inks each: the menu, keys and credits yellow, cyan and bright red;
game over and the win magenta and red. Each gets a palette with those
three (no splits needed), and the printer lights each glyph in the
logical colour its attribute's ink shows as (`ink_logical`, the nearest
the palette has to the inks the screen doesn't use). The attributes
themselves stay the original's.

## 16. C2's code is packed, and the low pages hold the palette's workspace (2026-10-31, provisional)

The game's code, from `&0E00`, now runs past `&5000 - &1900`, the most
that loads at `&1900` (the DFS's PAGE) below the title in the screen. So
C2 carries it packed by baron's `zx02` section transform (`src/lib`,
baron's example compressor and dmsc's unpacker): the loader loads TITLE,
moves the packed bytes up to end at the screen's start, and unpacks them
down to `&0E00` from page 4, where the unpacker is copied (the
attributes' page, not yet in use).

Main RAM is full, so: the font moved into GAMEDATA, whose tables end at
64194 (nothing reads the original's bytes after the tone table); the
palette's workspace sits after the variables, below page `&0D`;
`MAX_SPLITS` is a split per character row; `lit_hi` is `lit_lo` shifted.
The build's `PRINT`s give what's left. Fitting more will take moving
code into sideways RAM or packing the rooms (decision 9's 16K work).

## 17. Most of the sprite drawing lives in GAMEDATA (2026-10-31, provisional)

The sprite routines read GAMEDATA's tables (the frame attributes 60422,
the frame table 59798 and the frames, the line table 58931), so they
only run with GAMEDATA paged in, which it is whenever they're called.
Making the XOR and the pre-shift fast takes more code than main RAM had,
so `draw.6502` reopens the `GameData` section for the XOR (`xor_down`,
`xor_lines`), `sprite_ink`, 57058, 57182 and 57194; the clipped draw
57074 and the pre-shift 57415 stay in main RAM, as GAMEDATA hasn't room
for them too. The patterns take 8 bytes a row a parity (`pat_even`,
`pat_odd`), and the tile-bank list and the viewer's variables sit in the
rest of their two pages. The builds' `PRINT`s give what's left. The room
drawing's tile loop, which runs with ROOMDATA in, calls none of these.

What `xor_down` keeps from one call to the next (a run's address, its
row, whether it stayed on its cell row) is fixed zero page (`xr_cache`),
as it outlives any call.

Later the same day: `xor_down` and `xr_cache` gave way to `xor_seg`
(and `xor_line`), which take a character row's lines in one call, so
nothing outlives a call; the XOR's routines in GAMEDATA are now
`xor_lines`, `xor_line` and `xor_seg` (journal, "the XOR a character row
at a time").

## 18. The music as it's written, not as the beeper plays it (2026-10-31, provisional)

Matt asked for the tunes "as intended": the voices on the SN's own
channels, sounding as the composer wrote them, rather than the beeper's
time-slicing of them. This supersedes decision 12's articulation; its
tempo, pitch and software bass stand, the bass now held.

**What the streams say.** The player has no durations: a stream is a
note a tick, so a held note is written as the same note tick after tick
(tune 1's channel 1 holds F#4 for 64 ticks, 192 frames), and a repeated
note is written with a rest between (tune 2's fanfare: note, rest, note,
each a tick). Nothing in the data marks a re-strike without a rest; the
strike every tick is the beeper player's (it plays 2.11 frames of each
tick with the interrupts off, then lets the speaker sit), not the tune's.
So:

- **Articulation:** a run of one note in a stream is one note, held
  legato from the tick it starts to the tick the stream changes; a rest
  is silence; a different note follows without a gap. The two voices are
  independent, each on its own channel.
- **Tempo:** decision 12's: a tick every 3 frames, 2 when both voices
  rest, so every note's start and length is the original's, in frames.
- **Volume:** struck at full (attenuation 0) and settling 2dB a frame to
  attenuation 3 (`MUS_SUSTAIN`), held there: the attack-then-sustain of
  an `ENVELOPE`, so a note's start is heard against a long held one, and
  the voices sit under the effects' pulses (which stay at full). Kept
  simple: one shape for every note, the bass's included.

| | What it sounds like | Cost |
|---|---|---|
| **A. Legato with a strike-and-settle** (chosen) | the tunes' long notes long; a note's start audible | a level a channel, a step a frame in the step that runs anyway |
| B. Legato at one level | an organ: tune 1's two-note trills and its held notes run together | the least |
| C. Decision 12's re-strike every tick, 2 frames of 3 | the beeper's chop: every held note a 16.7Hz pulse train | none (as was) |

**Channels:** unchanged. The tunes' channel 1 on SN 0, channel 2 on
SN 1, the effects' pulses on SN 2 (decision 13), the noise channel
unused. The music still takes only the two channels the original wrote.

**The bass** (below the SN's lowest tone, 4MHz / 32 / 1023 = 122Hz):
tune 1's channel 2 has 80 of its 512 ticks there (F#2, 94.9Hz); tune 3
has 10 ticks of channel 1 and 9 of channel 2, 9 of them both channels at
once (down to 71.5Hz), its two voices falling a semitone apart.

| | Pitch | Cost |
|---|---|---|
| **A. Software bass** (kept, decision 12) | exact: a square wave, the channel at period 1 (inaudible) and its volume switched each half-cycle by a System VIA timer | an interrupt a half-cycle: at most two voices at 71-122Hz, under 500 a second, front end only; an edge due while VSync's interrupt runs waits for it, and the next is timed from when it was due |
| B. Periodic noise clocked by SN 2, at 1/15 of its tone | within 10 cents (SN 2 at period 69-117 for 120.7-71.5Hz; F#2 -4.5 cents) | one voice only, and tune 3 needs two at once; SN 2 is the effects' channel (decision 13), so a pulse would stop the bass; its waveform a 1-in-15 pulse, thin; and decision 12's D: CE2's was silent on Matt's machine |
| C. Each low note an octave up | an octave out | tune 1's F#2 lands on its own F#3 (the octave pattern becomes a unison); tune 3's falling lines jump up an octave halfway down |

A is kept: the only one exact for both of tune 3's voices, and it leaves
the effects their channel. Held, a bass note's volume switches until its
note ends (`bass_stop` on the next tick's change), rather than for a
tick's half-cycles: the per-note count goes (`mus_edges`).

`make music` checks, for every note of each tune against
`tools/musicmodel.py`'s merge of the original's ticks into notes: its
start, its SN period (or a bass note's half-cycles and their spacing),
its length held at that period, its volumes (struck once, never louder
until it ends), and silence in each rest.

## 19. A pre-shift pair's first tail is shifted by the second call (2026-10-31, provisional)

Three places pre-shift two images back to back, the new into 24225 and
then the old into 24427: a mover's redraw (56214), the heads' eyes
(53823) and their cackle (53651). A frame of 128 bytes or more drags
about 256 bytes of tail past its image (the original's signed halving),
so the first call's tail runs over the second's buffer, which the second
call then writes over. Those first calls go through `preshift_pair`: its
tail is left to the second call, which shifts it first, as the original
would have, but for the bytes from 24425 to the end of its own image.
The bytes are the original's again by the second call's end; between
the two calls only the callers' register saves run. `preshift_pair`
assumes those two buffers, the only pair the original has.
