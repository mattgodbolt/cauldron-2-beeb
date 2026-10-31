#!/usr/bin/env python3
"""What src/sound.6502 should play, for tools/musiccheck.mjs.

    .venv/bin/python tools/musicmodel.py [--snap build/c2.z80]

From tools/zxmusic.py's decode of the original's tunes (itself checked
against the original's speaker, docs/research/sound.md), the notes each
SN channel should strike, tick by tick, when the tune starts on a frame
and is stepped once a frame (decision 12):

- a tick every 3 frames, 2 when both channels rest;
- a channel's note, unless it rests: a tone at the SN period
  tools/mkmusic.py gives it, sounding 2 frames; or below the SN's lowest,
  the bass: period 1, its volume on then switched at each half-cycle
  (microseconds), for the tick's half-cycles, ending off;
- and the effects' pulses: effect n's width in microseconds.

Prints JSON: per tune, per channel, the notes {frame, period, half,
edges} that start in the tune's first `frames` frames.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mkmusic  # noqa: E402
import zxmusic  # noqa: E402

# Frames the check plays each tune for: tune 1 a whole loop and its start
# again, the others twice round.
FRAMES = {1: 1536 + 60, 2: 2 * 229 + 30, 3: 2 * 77 + 30}
# The effects whose pulses the check times.
PULSES = [0, 20, 30, 50, 67, 83]


def notes(tune, frames):
    out = [[], []]
    f = 0
    ticks = tune.ticks()
    i = 0
    while f < frames:
        p1, p2, length = ticks[i % len(ticks)]
        for c, p in enumerate((p1, p2)):
            if p == 1:
                continue
            n = mkmusic.sn_period(p)
            if n > mkmusic.SN_MAX:
                # Its volume switches at each half-cycle's end but the
                # last, where it stops: after an even number it's off already.
                halves = mkmusic.TICK_T // (p * 96)
                out[c].append({"frame": f, "period": 1, "half": mkmusic.half_us(p),
                               "edges": halves - (1 - halves % 2)})
            else:
                out[c].append({"frame": f, "period": n, "half": 0, "edges": 1})
        f += length
        i += 1
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snap", default="build/c2.z80")
    args = ap.parse_args()
    m = zxmusic.load(args.snap)
    tunes = []
    for x, number in enumerate(mkmusic.TUNES):
        t = zxmusic.Tune(m, number)
        tunes.append({"tune": number, "req": x + 1, "frames": FRAMES[number],
                      "channels": notes(t, FRAMES[number])})
    widths = [zxmusic.word(m, 64027 + 2 * n) for n in range(84)]
    pulses = [{"effect": n, "us": 4 * widths[n] / 3.5} for n in PULSES]
    json.dump({"tunes": tunes, "pulses": pulses}, sys.stdout)
    print()


if __name__ == "__main__":
    main()
