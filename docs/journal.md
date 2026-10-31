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

## 2026-10-31: sound and the front end

- The music player's decisions on the SN76489: a tick every 3 frames (2
  for a double rest), each note sounding 2 frames, the notes below the
  SN's floor as software bass on the System VIA's timers (decision 6).
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
  volume on for the pulse's width (decision 7). Timed against 4v
  T-states.
- The menu in the BBC's idiom, the keys' names shown (decisions 8 and
  9). `make front` runs it on a test build with a stand-in printer:
  define keys, the defaults, the joystick, game over and the win.
- A palette program with no splits leaves the User VIA's T1 running from
  the screen before, so stale splits land mid-screen: the front end's
  palettes carry one split that changes nothing, until `set_palette`
  stops T1 itself.
