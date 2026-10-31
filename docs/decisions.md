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

## 6. The music on the SN76489 (2026-10-31, provisional)

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
  grain).
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

## 7. The effects as the beeper's pulses (2026-10-31, provisional)

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

## 8. The menu and the keys in the BBC's idiom (2026-10-31, provisional)

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

## 9. The front end's colours (2026-10-31, provisional)

The original's front-end screens are text on black paper with at most
three inks each: the menu, keys and credits yellow, cyan and bright red;
game over and the win magenta and red. Each gets a palette with those
three (no splits needed), and the printer lights each glyph in the
logical colour its attribute's ink shows as (`ink_logical`, the nearest
the palette has to the inks the screen doesn't use). The attributes
themselves stay the original's.
