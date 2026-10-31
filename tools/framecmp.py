#!/usr/bin/env python3
"""Frames per main-loop pass, the port's against the original's.

    python3 tools/framecmp.py [build/passes] [--detail NAME]

Reads the pairs `make passes` leaves (zx_NAME.json from tools/zxpass.py,
bbc_NAME.json from tools/beepass.mjs) and prints, per scenario, the frames
each took over the passes both logged and their ratio, and how many passes
took more (or fewer) frames on the BBC. --detail NAME lists the passes of
one scenario whose frame counts differ.
"""
import argparse
import glob
import json
import os


def load(path):
    with open(path) as f:
        return json.load(f)["passes"]


def deltas(passes, m):
    return [passes[i + 1]["frame"] - passes[i]["frame"] for i in range(m - 1)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", nargs="?", default="build/passes")
    ap.add_argument("--detail")
    args = ap.parse_args()
    tz = tb = 0
    for z in sorted(glob.glob(os.path.join(args.dir, "zx_*.json"))):
        name = os.path.basename(z)[3:-5]
        b = os.path.join(args.dir, f"bbc_{name}.json")
        if not os.path.exists(b):
            continue
        zp, bp = load(z), load(b)
        m = min(len(zp), len(bp))
        zd, bd = deltas(zp, m), deltas(bp, m)
        zf, bf = sum(zd), sum(bd)
        tz += zf
        tb += bf
        more = sum(c > a for a, c in zip(zd, bd))
        fewer = sum(c < a for a, c in zip(zd, bd))
        print(f"{name:12s} zx {zf:6d}  bbc {bf:6d}  {bf / zf:.3f}"
              f"   passes longer {more:4d} shorter {fewer:4d} of {m - 1}")
        if args.detail == name:
            for i, (a, c) in enumerate(zip(zd, bd)):
                if a != c:
                    print(f"    pass {i}: zx {a} bbc {c}")
    if tz:
        print(f"{'all':12s} zx {tz:6d}  bbc {tb:6d}  {tb / tz:.3f}")


if __name__ == "__main__":
    main()
