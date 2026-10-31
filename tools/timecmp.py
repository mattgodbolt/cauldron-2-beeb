#!/usr/bin/env python3
"""Where the port loses frames to the original: tools/zxtimeline.py's and
tools/timeline.mjs's logs of one scenario, wait by wait.

    python3 tools/timecmp.py NAME [--dir build/timeline] [--show N] [--rows N]

Every wait for a frame (the original's HALT, our wait_vsync) of every pass
is put on one count of frames. A wait that ends more frames after the one
before it on the BBC than on the original is a frame lost: the work
between them ran past a VSync that the original's didn't. A wait that ends
fewer frames after is one gained back. It prints the totals, the first N
lost waits with both machines' times since the VSync, how the losses fall
by the number of still slots' busy waits (wait_us) in the work, and each
routine's time (inclusive) in the lost frames' work and over the whole
run on both machines. Times are microseconds.
"""
import argparse
import json
import os
from collections import Counter

STILL_US = 7607  # one still slot's 1024 DEC BC loops at 26 T-states (56299)
# Our names for the original's routines that aren't zNNNNN.
SAME = {"irq_handler": "irq"}


def flatten(passes):
    """Every wait on one count of frames; the first of a pass carries the
    work after the last pass's last wait (its tail) too."""
    out = []
    base = 0
    tail = None
    for p in passes:
        for i, w in enumerate(p["waits"]):
            if i == 0 and tail:
                w = dict(w, work=w["work"] + tail["work"],
                         incl=dict(Counter(w["incl"]) + Counter(tail["incl"])))
            out.append({"pass": p["pass"], "i": i, "frame": base + w["frame"], "w": w})
        base += p["frames"]
        tail = p.get("tail")
    return out


def incl(w):
    return Counter({SAME.get(k, k): v for k, v in w["incl"].items()})


def table(title, z, b, n):
    print(title)
    print(f"  {'routine':16s} {'zx':>9s} {'bbc':>9s}  bbc/zx")
    for r, _ in (z + b).most_common(n):
        ratio = f"{b[r] / z[r]:6.2f}" if z[r] else "     -"
        print(f"  {r:16s} {z[r]:9d} {b[r]:9d}  {ratio}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("--dir", default="build/timeline")
    ap.add_argument("--show", type=int, default=10)
    ap.add_argument("--rows", type=int, default=20)
    args = ap.parse_args()
    with open(os.path.join(args.dir, f"zx_{args.name}.json")) as f:
        zp = json.load(f)["passes"]
    with open(os.path.join(args.dir, f"bbc_{args.name}.json")) as f:
        bp = json.load(f)["passes"]
    m = min(len(zp), len(bp))
    for i in range(m):
        if len(zp[i]["waits"]) != len(bp[i]["waits"]):
            print(f"pass {i}: {len(zp[i]['waits'])} waits on the original, {len(bp[i]['waits'])} here; "
                  "compared up to it")
            m = i
            break
    zw, bw = flatten(zp[:m]), flatten(bp[:m])
    zf = sum(p["frames"] for p in zp[:m])
    bf = sum(p["frames"] for p in bp[:m])
    print(f"{args.name}: {m} passes, {len(zw)} waits; frames zx {zf} bbc {bf} ({bf / zf:.3f})")

    lost = gained = 0
    by_still = Counter()
    lz, lb, az, ab = Counter(), Counter(), Counter(), Counter()
    shown = 0
    for k in range(len(zw)):
        az += incl(zw[k]["w"])
        ab += incl(bw[k]["w"])
        if k == 0:
            continue
        zg = zw[k]["frame"] - zw[k - 1]["frame"]
        bg = bw[k]["frame"] - bw[k - 1]["frame"]
        if bg < zg:
            gained += zg - bg
        if bg <= zg:
            continue
        lost += bg - zg
        w = bw[k]["w"]
        still = round(w["incl"].get("wait_us", 0) / STILL_US)
        by_still[still] += bg - zg
        lz += incl(zw[k]["w"])
        lb += incl(w)
        if shown < args.show:
            shown += 1
            print(f"  pass {zw[k]['pass']} wait {zw[k]['i']}: frames since the last zx {zg} bbc {bg}; "
                  f"reached at zx {zw[k]['w']['phase']} bbc {w['phase']} after the VSync; "
                  f"work zx {zw[k]['w']['work']} bbc {w['work']}, {still} still")
    print(f"lost {lost} frames, gained {gained}")
    print("lost by still slots in the work:", dict(sorted(by_still.items())))
    table("the lost frames' work, inclusive:", lz, lb, args.rows)
    table("every wait's work, inclusive:", az, ab, args.rows)


if __name__ == "__main__":
    main()
