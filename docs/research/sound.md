# Sound

Research on the original's sound (ZX Spectrum 48K, beeper only). Control
file: `disasm/sound.ctl`; decoder: `tools/zxmusic.py`. Addresses are
decimal, as the original's. Every claim here was checked by running the
original on SkoolKit's simulator (scripts under `build/research/fe/`)
unless it says otherwise.

## Summary

- **Music**: three copies of one two-channel beeper player, one per tune,
  played one *tick* per frame interrupt while `24002` (the front-end
  mode) is non-zero. Tune 1 on the title, menu and credits; tune 3 on
  game over; tune 2 on the win screen. No music in play.
- **Effects**: one routine, `52854`, that makes a single speaker pulse
  of a width taken from a table. Every effect is a train of these
  pulses, one per main-loop pass or per frame: the bounce, collecting,
  the explosion, and the witches' cackle on a room change.
- The only `OUT (254)`s in the game: the three players (`50237`, `50249`,
  `50271` and their copies), the pulse (`52904`), the border (`52213`,
  `53545`, both black).

## The music player

Copies at 50100 (tune 1), 51400 (tune 2) and 51850 (tune 3). They are the
same code relocated (each even carries the programmer's mark `"adam"`,
at 50260/51560/52010); only copy 1 is commented in `sound.ctl`. For copy
1:

| Address | Label | What |
|---|---|---|
| 50100 | `mus1_start` | Pointers to the start, `DI`, play one tick, then the tail below. Called by 52235 (warm start). |
| 50113 | `mus1_tick` | The IRQ handler's entry: play one tick, `CALL 654` (ROM KEY-SCAN), `INC E`, `LD A,247`, `EI`, `RET`. |
| 50136 | `mus1_next` | HL = address of a channel pointer: pre-increment it, fetch the note; on 64 reload from the loop address (`50163`). Returns A = note. |
| 50149 | `mus1_period` | HL = address of a note: H = `table[note+12]`, L = 1, E = note+12. |
| 50171 | `mus1_play` | One tick (below). |
| 50282 | `mus1_rest` | The silent tick, when both channels have period 1. |
| 50312 | `mus1_periods` | Period table, 53 bytes, plus the 1 at 50365. |

Copy 2 is the same at +1300 (51400...), copy 3 at +1750 (51850...).

**The disabled loop.** At 50116 the code scans the keyboard and does
`INC E` (Z if no key), then has the bytes `62,247` (`LD A,247`). As
`40,247` they would be `JR Z,50113`: play ticks until a key is pressed.
So the player was written to loop by itself and was turned into a
one-tick-per-call routine for the interrupt. Copies 2 and 3 have six
`NOP`s there instead. Nothing writes 50120.

**`JP C,50366` at 50197** (and copies) jumps into the tune data if bit 7
of `note+12` is set. Notes are -12..41, so it never happens.

### Variables (per copy; copy 1 shown, copies at 51424 and 51874)

| Address | Size | Name | Meaning |
|---|---|---|---|
| 50124 | 1 | note1 | Channel 1's current note |
| 50125 | 1 | note2 | Channel 2's current note |
| 50126 | 1 | border | Byte OUT with the speaker bit clear; set to 0 by 52235 |
| 50127 | 2 | ptr1 | Channel 1 pointer (pre-incremented: starts one byte before the data) |
| 50129 | 2 | loop1 | Channel 1 loop address (the first note: 50366) |
| 50131 | 2 | ptr2 | Channel 2 pointer |
| 50133 | 2 | loop2 | Channel 2 loop address (50880) |
| 50135 | 1 | tempo | Set to 250 by 52235; the snapshot's values (238 etc.) are stale |

### One tick (`50171`)

1. Fetch each channel's next note; periods `P1`, `P2` from the table.
2. If both are 1 (rest), run the silent delay `50282`:
   `(255 - tempo) * 256` passes of a 93 T-state loop, no `OUT`
   (`SRA (HL)` on HL = 0 is a ROM write, for timing). 5 * 256 * 93 =
   119040 T = 1.70 frames.
3. Otherwise `(256 - tempo) * 256` iterations (6 * 256 = 1536) of the
   two-channel loop. Every path through it is **96 T-states** (counted by
   hand, then confirmed: 3072 `OUT`s per tick, 147456 T = 2.11 frames).
   Each iteration does one `OUT (254)` for channel 1 (its byte in A',
   counter E, reload IXh) and one for channel 2 (A, counter L, reload H).
   A channel's speaker bit (bit 4, `D = 16`) flips when its counter hits
   0, so

       f = 3500000 / (2 * 96 * P) Hz       (18229 / P)

   The two channels alternate `OUT`s within the loop, which mixes them on
   the one-bit speaker. A channel with period 1 flips every iteration
   (18 kHz): in practice silent. `zxmusic.py` lists it as a rest.

Registers: `50136`/`50149` need HL in, return A or H/L/E; `50171` uses
every main register, A', and IXh; it preserves nothing. The IRQ handler
saves everything but A' and F', which nothing else uses.

Contention isn't modelled by the simulator. The code is in uncontended
memory but `OUT (254)` is contended on a real 48K while the screen is
drawn, so real ticks may be slightly longer and lower than these figures.
Unmeasured.

### The tempo comes from the interrupt

The player is not called in a loop. The IM 2 handler (`57664`) checks
`24002` and, if it is 1-3, jumps through the table at `64019` to that
tune's tick entry (50113, 51863, 51413), returning to `57696`:

| 24002 | Who sets it | Entry | Tune |
|---|---|---|---|
| 0 | 52372 (game starts) | - | none |
| 1 | 52275 (warm start) | 50113 | tune 1, title/menu/credits |
| 2 | 53107 (game over) | 51863 | tune 3 |
| 3 | 56829 (win) | 51413 | tune 2 |

The table's entry 0 (64019, value 65290) is never used; its bytes are the
tail of the collect sweep's descriptor (64014).

A sounding tick lasts 2.11 frames with interrupts off, so the two
interrupts in between are lost and the next tick starts on the third:
**one tick every 3 frames, sounding for 2.11 of them, silent for the other
0.89** (the speaker holds still). A rest tick (1.70 frames) gives a
**2-frame** tick. Every note is re-struck each tick, so a held note is a
string of 2.11-frame bursts at 16.7 Hz. The main program (menu, credits,
key waits) runs in the gaps.

Measured from `tools/zx.py --ports` logs with `zxmusic.py --check`:
tune 1 from reset for 40 s (667 ticks, 0 mismatches in period or
timing), tune 2 and 3 by poking 24002 and the pointers in the menu
(216 and 325 ticks), and tune 3 in a real game over (61 ticks): every
tick's two periods match the decoded data and every tick starts 3 frames
(2 for rests) after the last. The first tick of each tune is played by a
direct call (52272, 53102, 56824), not on the frame, and lasts until the
next interrupt.

### The tune data

Per channel, one byte per tick: a signed semitone number -12..41 (bytes
over 127 are negative). The period is `table[n + 12]`. The 54th table
entry is the byte just before channel 1's data, which is 1: so note 41 is
a rest. 64 ends the stream; it then restarts from its loop address,
which in all six streams is its first note. Both channels of a tune have
the same length, so they stay in step.

| Tune | When | Ch 1 | Ch 2 | Ticks | Loop (frames) | Range |
|---|---|---|---|---|---|---|
| 1 | title, menu, credits | 50366-50877 | 50880-51391 | 512 | 1536 | 94.9-1519 Hz |
| 2 | win | 51666-51755 | 51758-51847 | 90 | 229 | 480-959 Hz |
| 3 | game over | 52116-52141 | 52144-52169 | 26 | 77 | 71.5-299 Hz |

The periods are a rounded equal-tempered scale from 255 (71.5 Hz) to 12
(1519 Hz). Against A = 440 Hz most notes sit 0.4-0.5 of a semitone sharp;
the rounding scatters a few (G5 +0.19, D#5 -0.41).

- **Tune 1**: channel 2 is a bass/rhythm line in pairs of ticks (note,
  rest) down to -7 (94.9 Hz); channel 1 has long held notes and fast
  two-note trills and chromatic runs.
- **Tune 2**: a fanfare in fourths; both channels rest together often.
- **Tune 3**: both channels fall chromatically a semitone apart, from
  285/299 Hz down to 71.5/76 Hz, then rest, and loop until fire.

For the SN76489: tunes 1 and 3 go below its lowest tone (about 122 Hz on
the BBC): tune 1 to 94.9 Hz, tune 3 to 71.5 Hz.

### `tools/zxmusic.py`

    .venv/bin/python tools/zxmusic.py [--tune N] [--ticks] [--json]
    .venv/bin/python tools/zxmusic.py --check PORTLOG [--tune N] [--skip K]

Reads `build/c2.z80`, finds each tune from its player's code (pointer
initialisers, loop words, table), and prints `channel Hz frames note`
events (0 Hz = rest), merging repeated ticks unless `--ticks`. `--json`
gives the same per tune with the loop length. `--check` compares a
`tools/zx.py --ports` log against the decoded ticks, burst by burst:
each channel's flip interval and the frames between ticks. `--skip`
skips bursts before the tune's first tick (e.g. a partial tick at the
log's start).

## Effects

### The pulse (`52854`, `sfx_pulse`)

A = effect number. `HL = table[A]` from `64027` (84 words, `v`). It
raises the speaker bit, waits, lowers it, and returns: one pulse about
`4 * v` T-states wide (measured 1.007-1.026 times `4 * v`). The delay is
`L/4 + 2` short loops, `H` passes of 63, and `v AND 3` NOPs, reached by
**jumping into the NOPs at 52888 through IX** (self-modifying flow, no
self-modified bytes). The `OUT` byte carries the border colour from
`(24006) AND 56 >> 3` (always 0) and the MIC bit (8). Preserves HL;
destroys A, BC, IX, flags.

The table runs in seven groups of 12, each falling about a semitone per
entry; `v` from 13378 (53.5k T, 15 ms) to 1012 (4 kT, 1.2 ms).

Since each call is one pulse, the pitch heard is the rate of the calls
(the main-loop pass, about 0.6-0.7 frames in play, or the frame), and the
width shapes the sound.

### The sweep sequencer (`52781`, `52791`)

`52781` (HL = descriptor) starts a sweep: `24003-24004` = record pointer,
`24005` = first effect number. `52791`, called once per main-loop pass
from 55783, plays effect `(24005)`, then adds the record's step; while
the number stays within the record's first..last (unsigned compares) the
sweep goes on; when it leaves, the next 3-byte record starts, or the
sweep ends if the byte after the record is 255. A new trigger restarts
it.

| Descriptor | Effects | Triggered by |
|---|---|---|
| 64010 `20,30,2,255` | 20 22 24 26 28 30 | the bounce: 53288, 54780, 54860, 54899 |
| 64014 `50,10,246, 10,50,10, 255` | 50, 10 20 30 40 50 | collecting / scoring: 56514, 56894 |

Measured in random play: the bounce sweep, one pulse per pass (0.6-1.1
frames apart), often twice in a row as the pumpkin bounces again.

### The explosion (`57714`, `sfx_explode`)

`24000` counts down; each frame interrupt while it is non-zero plays
effect `50 + (count AND 31)`: from 50, effects 67..50 then 81..50, one
pulse a frame. 55624 (spawn) sets it to 50 when it spawns type 5, the
explosion: when the pumpkin dies (56571), or a monster is destroyed
(56396, 56453). 50 pulses over 50 frames (more if interrupts are missed
while the main loop has them off).

**At power-on** `24000` holds a byte left over from loading (101; the
new-game reset `53858` zeroes it later). So the title screen opens with
101 of these pulses, one after each music tick. Deterministic, since the
byte comes from the tape block.

### The cackle (`53798`, `sfx_witch`)

On a room change (53310) the witches' mouths animate (`53651`, see
frontend.md): 15 steps, each with four calls of `53798`, which plays
effect `(24001 - 1) AND 31` counting down: 31, 30, ..., 0, 31, ..., 4
(60 pulses), two per frame (HALTs between).

### Variables

| Address | Size | Name | Meaning |
|---|---|---|---|
| 24000 | 1 | explode_count | Explosion pulses left (one per frame) |
| 24001 | 1 | cackle_fx | Cackle effect number (counts down, AND 31) |
| 24002 | 1 | fe_mode | 0 play, 1 title music, 2 game-over music, 3 win music |
| 24003 | 2 | sfx_rec | Current sweep record (0 = none) |
| 24005 | 1 | sfx_num | Current sweep effect number |
| 24006 | 1 | border | Border colour for OUTs (always 0) |
| 61248 | 2 | rnd_ptr | Advanced every frame by the IRQ (and every credits pass); seeded from R |

## For the port

- The music is a list of two-channel ticks on a 3-frame clock (2 for
  double rests), with a 2.11/0.89-frame on/off articulation per tick.
  `zxmusic.py --ticks --json` gives the data.
- The interrupt-driven player starves the main program of 2.11 of every
  3 frames while music plays; the credits' page time (frontend.md)
  depends on it.
- Effects are pulse trains whose rate is the caller's: one per main-loop
  pass (bounce, collect), per frame (explosion), two per frame (cackle).
