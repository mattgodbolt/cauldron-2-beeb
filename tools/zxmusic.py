#!/usr/bin/env python3
"""Decode Cauldron II's beeper tunes from the Spectrum snapshot.

    .venv/bin/python tools/zxmusic.py [--snap build/c2.z80] [--tune N] [--ticks] [--json]
    .venv/bin/python tools/zxmusic.py --check PORTLOG [--tune N]

The game has three copies of one two-channel beeper player (see
docs/research/sound.md), each with its own tune:

    1  title/menu   player 50100, IRQ entry 50113 (24002 = 1)
    2  win          player 51400, IRQ entry 51413 (24002 = 3)
    3  game over    player 51850, IRQ entry 51863 (24002 = 2)

A tune is two byte streams, one per channel, one byte per tick. A byte is a
signed semitone number n (-12..41); the period is table[n + 12] (the table is
the 54 bytes before the channel 1 data: its last entry, the byte just before
the data, is 1, so n = 41 gives period 1, which is the rest). 64 ends the
stream, which then restarts at its loop address. Each tick runs
(256 - tempo) * 256 iterations of a 96 T-state loop; each channel's speaker
bit flips every `period` iterations, so f = CLOCK / (2 * 96 * period).

The player runs once per tick from the IM 2 handler. A sounding tick takes
(256 - 250) * 256 * 96 T = 2.11 frames, so the next tick starts on the third
frame interrupt: one tick every 3 frames, sounding for 2.11 of them. A tick
where both channels rest runs a silent delay of 5 * 256 * 93 T = 1.70 frames
instead, so it lasts 2 frames.

Output: one event per line, `channel frequency_Hz duration_frames note`
(frequency 0 = rest). By default consecutive ticks on the same note are
merged into one event; --ticks prints every tick (the original re-strikes
the note every tick, with ~0.89 frames of silence between ticks). Channel
events are listed channel 1 first, then channel 2; each channel's durations
add up to the same total. The `loop` line gives the frame at which the
tune repeats from its loop point (here always its start).

--check reads a port log from `tools/zx.py --ports` that covers the tune
from its first tick (e.g. the menu from reset for tune 1) and compares every
burst of beeper writes with the decoded ticks: each channel's flip interval
in loop iterations, and the tick start times in frames.
"""
import argparse
import json
import math
import sys

from skoolkit.snapshot import Snapshot

CLOCK = 3500000      # 48K Spectrum CPU clock, Hz
FRAME = 69888        # T-states per frame
LOOP_T = 96          # T-states per iteration of the two-channel loop
REST_LOOP_T = 93     # ... and of the silent delay loop
END = 64             # end-of-stream marker
REST = 41            # note number whose period is 1

# Per tune: the player's init routine (LD HL,ch1-1 : LD (p1),HL : LD HL,ch2-1 : LD (p2),HL)
PLAYERS = {1: 50100, 2: 51400, 3: 51850}
NAMES = {1: "title/menu", 2: "win", 3: "game over"}
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def load(path):
    return [0] * 16384 + list(Snapshot.get(path).ram(-1))


def word(m, a):
    return m[a] | m[a + 1] << 8


class Tune:
    def __init__(self, m, number):
        init = PLAYERS[number]
        assert m[init] == 0x21 and m[init + 3] == 0x22 and m[init + 6] == 0x21 and m[init + 9] == 0x22
        self.number = number
        self.name = NAMES[number]
        ptr1, ptr2 = word(m, init + 4), word(m, init + 10)   # the pointer variables
        start1, start2 = word(m, init + 1) + 1, word(m, init + 7) + 1   # pre-incremented
        loop1, loop2 = word(m, ptr1 + 2), word(m, ptr2 + 2)
        self.base = ptr1 - 3                                  # note1, note2, border byte, ptr1...
        self.table = start1 - 1 - 53
        # Tempo is poked by 52235 (250), the snapshot's value is stale.
        self.tempo = 250
        self.border = 0
        self.table_bytes = m[self.table:self.table + 54]
        assert self.table_bytes[53] == 1, "the rest's period"
        self.channels = []
        for start, loop in ((start1, loop1), (start2, loop2)):
            notes = []
            a = start
            while m[a] != END:
                notes.append(m[a] - 256 if m[a] > 127 else m[a])
                a += 1
            self.channels.append({"start": start, "end": a, "loop": loop, "notes": notes})
        for ch in self.channels:
            assert ch["loop"] == ch["start"], "loops to its start"
        assert len(self.channels[0]["notes"]) == len(self.channels[1]["notes"])

    def period(self, n):
        return self.table_bytes[n + 12]

    def ticks(self):
        """(period1, period2, frames) per tick."""
        out = []
        for n1, n2 in zip(self.channels[0]["notes"], self.channels[1]["notes"]):
            p1, p2 = self.period(n1), self.period(n2)
            out.append((p1, p2, 2 if p1 == 1 and p2 == 1 else 3))
        return out


def freq(period):
    return 0.0 if period == 1 else CLOCK / (2 * LOOP_T * period)


def note_name(f):
    if not f:
        return "rest"
    midi = 69 + 12 * math.log2(f / 440.0)
    r = round(midi)
    return f"{NOTE_NAMES[r % 12]}{r // 12 - 1}{midi - r:+.2f}"


def events(tune, merge=True):
    ticks = tune.ticks()
    evs = []
    for ch in (0, 1):
        cur = None
        for t in ticks:
            p, frames = t[ch], t[2]
            if merge and cur and cur[1] == p:
                cur[2] += frames
            else:
                cur = [ch + 1, p, frames]
                evs.append(cur)
    return [(c, round(freq(p), 2), d, note_name(freq(p))) for c, p, d in evs], sum(t[2] for t in ticks)


def bursts_from_log(path, gap=2000):
    outs = []
    for line in open(path):
        f = line.split()
        if len(f) >= 3 and f[1] == "FE":
            outs.append((int(f[0]), int(f[2])))
    groups, cur = [], []
    for t, v in outs:
        if cur and t - cur[-1][0] > gap:
            groups.append(cur)
            cur = []
        cur.append((t, v))
    if cur:
        groups.append(cur)
    # The player's bursts are thousands of writes; lone writes are other sounds.
    return [g for g in groups if len(g) > 100]


def flip_interval(stream):
    """The modal number of writes between speaker-bit flips (ignoring the first)."""
    flips = [i for i in range(1, len(stream)) if (stream[i] ^ stream[i - 1]) & 16]
    if len(flips) < 2:
        return None
    gaps = [b - a for a, b in zip(flips, flips[1:])]
    return max(set(gaps), key=gaps.count)


def check(tune, path, skip=0):
    bursts = bursts_from_log(path)[skip:]
    ticks = tune.ticks()
    bad = n = i = 0
    prev_start = prev_frames = None
    for k, b in enumerate(bursts):
        # Drop stray writes just before the burst (52213's border OUT, 52904's click):
        # the player's writes are at most one 96 T loop apart.
        while len(b) > 1 and b[1][0] - b[0][0] > LOOP_T:
            b = b[1:]
        frames_between = 0
        while ticks[i % len(ticks)][0] == 1 and ticks[i % len(ticks)][1] == 1:
            frames_between += ticks[i % len(ticks)][2]
            i += 1
        p1, p2, frames = ticks[i % len(ticks)]
        vals = [v for _, v in b]
        # Writes alternate channel 1, channel 2 (50237, then 50249 or 50271).
        m1, m2 = flip_interval(vals[0::2]), flip_interval(vals[1::2])
        start = b[0][0] / FRAME
        ok = m1 == p1 and m2 == p2
        msg = ""
        # The first tick is played by 52272's call, outside the interrupt, so its
        # start isn't on a frame; time the ones after it.
        if prev_start is not None and k > 1:
            gap = start - prev_start
            want = prev_frames + frames_between
            if abs(gap - want) > 0.1:
                ok = False
                msg = f"; {gap:.2f} frames after the last, model {want}"
        if not ok:
            bad += 1
            if bad <= 10:
                print(f"tick {i}: model p={p1},{p2}; log p={m1},{m2}{msg}")
        prev_start, prev_frames = start, frames
        n += 1
        i += 1
    print(f"tune {tune.number}: {n} bursts compared, {bad} mismatches "
          f"({i // len(ticks)} full passes + {i % len(ticks)} ticks)")
    return bad == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snap", default="build/c2.z80")
    ap.add_argument("--tune", type=int, choices=(1, 2, 3))
    ap.add_argument("--ticks", action="store_true", help="one event per tick, not merged")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", metavar="PORTLOG")
    ap.add_argument("--skip", type=int, default=0, help="--check: bursts to skip before the tune's first tick")
    args = ap.parse_args()
    m = load(args.snap)
    if args.check:
        return 0 if check(Tune(m, args.tune or 1), args.check, args.skip) else 1
    out = {}
    for number in ([args.tune] if args.tune else [1, 2, 3]):
        tune = Tune(m, number)
        evs, total = events(tune, merge=not args.ticks)
        if args.json:
            out[number] = {"name": tune.name, "loop_frames": total,
                           "events": [{"channel": c, "hz": f, "frames": d, "note": nn} for c, f, d, nn in evs]}
            continue
        print(f"# tune {number} ({tune.name}): {len(tune.channels[0]['notes'])} ticks, "
              f"data {tune.channels[0]['start']}-{tune.channels[0]['end']} and "
              f"{tune.channels[1]['start']}-{tune.channels[1]['end']}, table {tune.table}")
        for c, f, d, nn in evs:
            print(c, f, d, nn)
        print("loop", total)
    if args.json:
        json.dump(out, sys.stdout, indent=1)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
