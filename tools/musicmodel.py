#!/usr/bin/env python3
"""What src/sound.6502 should play, for tools/musiccheck.mjs.

    .venv/bin/python tools/musicmodel.py [--snap build/c2.z80]

From tools/zxmusic.py's decode of the original's tunes (itself checked
against the original's speaker, docs/research/sound.md), the notes each
SN channel should play when the tune starts on a frame and is stepped
once a frame (decisions 12 and 18):

- a tick every 3 frames, 2 when both channels rest;
- a channel's note held from the tick it starts until its stream changes
  (a run of the same note is one note; a rest is silence): a tone at the
  SN period tools/mkmusic.py gives it; or below the SN's lowest, the bass:
  period 1, its volume switched at each half-cycle (microseconds);
- and the effects' pulses: effect n's width in microseconds.

Prints JSON: per tune, per channel, the notes {frame, frames, period,
half} that start in the tune's first `frames` frames.
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
    held = [None, None]
    f = 0
    ticks = tune.ticks()
    i = 0
    while f < frames:
        p1, p2, length = ticks[i % len(ticks)]
        for c, p in enumerate((p1, p2)):
            if p == held[c]:
                if p != 1:
                    out[c][-1]["frames"] += length
                continue
            held[c] = p
            if p == 1:
                continue
            n = mkmusic.sn_period(p)
            if n > mkmusic.SN_MAX:
                out[c].append({"frame": f, "frames": length, "period": 1, "half": mkmusic.half_us(p)})
            else:
                out[c].append({"frame": f, "frames": length, "period": n, "half": 0})
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
