#!/usr/bin/env python3
"""Random scenarios on both machines, compared pass by pass.

    python3 tools/fuzz.py [--count 8] [--seed 1] [--passes 400] [--jobs 4]

Writes build/fuzz/scenarios.txt (tests/scenarios.txt's format: a random
start room and random keys held for random spells), runs each through
tools/zxpass.py, tools/beepass.mjs and tools/passcmp.py as `make passes`
does, and lists the ones that differ. A failing line goes into
tests/scenarios.txt as it is, to stay fixed. Exits non-zero if any differ.
"""
import argparse
import concurrent.futures
import os
import random
import subprocess
import sys

COMBOS = ["-", "R", "L", "U", "D", "F", "R+F", "L+F", "R+U", "L+D", "U+F", "D+F"]


def scenario(rng, name, passes):
    keys = []
    p = 0
    while p < passes:
        keys.append(f"{p}:{rng.choice(COMBOS)}")
        p += rng.randint(2, 40)
    return f"{name}  start={rng.randint(0, 7)}  passes={passes}  " + "  ".join(keys)


def run(name, scen, env):
    out = []
    for cmd in ([".venv/bin/python", "tools/zxpass.py", name, "--scenarios", scen, "-o", f"build/fuzz/zx_{name}.json"],
                ["node", "tools/beepass.mjs", name, "--scenarios", scen, "-o", f"build/fuzz/bbc_{name}.json"],
                ["python3", "tools/passcmp.py", f"build/fuzz/zx_{name}.json", f"build/fuzz/bbc_{name}.json"]):
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        out.append(r.stdout.strip().split("\n")[-6:])
        if r.returncode:
            return name, False, "\n".join("\n".join(o) for o in out)
    return name, True, out[-1][-1] if out[-1] else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--count", type=int, default=8)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--passes", type=int, default=400)
    ap.add_argument("--jobs", type=int, default=4)
    args = ap.parse_args()
    os.makedirs("build/fuzz", exist_ok=True)
    rng = random.Random(args.seed)
    lines = [scenario(rng, f"fuzz{args.seed}_{i}", args.passes) for i in range(args.count)]
    scen = "build/fuzz/scenarios.txt"
    with open(scen, "w") as f:
        f.write("\n".join(lines) + "\n")
    bad = []
    with concurrent.futures.ThreadPoolExecutor(args.jobs) as ex:
        for name, ok, msg in ex.map(lambda l: run(l.split()[0], scen, os.environ.copy()), lines):
            print(f"{name}: {'agree' if ok else 'DIFFER'}  {msg if ok else ''}")
            if not ok:
                print(msg)
                bad.append(next(l for l in lines if l.split()[0] == name))
    if bad:
        print("\nFailing scenarios (copy into tests/scenarios.txt):")
        print("\n".join(bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
