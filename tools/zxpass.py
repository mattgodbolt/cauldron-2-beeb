#!/usr/bin/env python3
"""The original's state at every main-loop pass, for a scenario.

    .venv/bin/python tools/zxpass.py NAME [-o build/passes/zx_NAME.json]
        [--scenarios tests/scenarios.txt] [--snap build/c2.z80]
    .venv/bin/python tools/zxpass.py --list

The Spectrum half of the pass-by-pass oracle (tools/beepass.mjs is the
BBC's, tools/passcmp.py compares them; `make passes` runs all three).

From the entry snapshot it takes the menu (1: Kempston) and starts a game
from the attract loop with fire. At the new game (52372) it fixes the
start room: the random pointer 61248 is pointed at a run of bytes holding
the scenario's start (0-7), so StartRooms 61240[k] is the room on both
machines whatever the attract loop's timing. Then at each arrival at the
main loop (52430) it records the state and sets the Kempston bits the
scenario holds for that pass. It stops after the scenario's passes, at
game over (53101, which waits for fire outside the main loop), or when
the game restarts (52235: the win, abort).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zx import Spectrum  # noqa: E402
from skoolkit.simutils import PC, T  # noqa: E402

ENTRY_MENU = 52481
ATTRACT = 52290
NEW_GAME = 52372
MAIN_LOOP = 52430
RESTART = 52235
GAME_OVER = 53101
RAND_PTR = 61248

# The random pointer is aimed at the top of the variables, which the new
# game's reset (53858 zeroes 24000-25058) leaves alone; both machines log
# them, so they must hold the same. The interrupt steps the pointer each
# frame, hence a run of bytes, not one.
RAND_RUN = range(25092, 25100)

VARS = (24000, 25100)
# Bytes outside the variables the game writes in play: 59450 and 59582
# (movement scripts' directions, poked by handlers), 61521-61572 (magic
# rooms, bit 7 once taken), and the score and magic digits.
EXTRA = [59450, 59582, *range(61521, 61573), *range(58804, 58811), 58813, 58814]

KEMPSTON = {"R": 1, "L": 2, "D": 4, "U": 8, "F": 16}

# Emulated time allowed: the front end to the new game, and one pass
# (generous, so the slowest pass, room entry or the trip outside, is
# never taken for a stop).
SETUP_FRAMES = 60 * 50
PASS_FRAMES = 30 * 50
CHUNK_FRAMES = 50


def parse_scenarios(path):
    """Each line: name start=k passes=N then pass:keys changes (see the
    file's header). Returns {name: {start, passes, keys: [(pass, bits)]}}."""
    out = {}
    with open(path) as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.split("#", 1)[0].split()
            if not line:
                continue
            name, *fields = line
            sc = {"name": name, "start": 0, "passes": 100, "keys": []}
            for fld in fields:
                if fld.startswith("start="):
                    sc["start"] = int(fld[6:])
                elif fld.startswith("passes="):
                    sc["passes"] = int(fld[7:])
                elif ":" in fld:
                    p, keys = fld.split(":", 1)
                    bits = 0
                    for k in keys.replace("+", ""):
                        if k == "-":
                            continue
                        if k not in KEMPSTON:
                            sys.exit(f"{path}:{lineno}: unknown key {k!r} in {fld}")
                        bits |= KEMPSTON[k]
                    sc["keys"].append((int(p), bits))
                else:
                    sys.exit(f"{path}:{lineno}: can't read {fld!r}")
            if not 0 <= sc["start"] <= 7:
                sys.exit(f"{path}:{lineno}: start must be 0-7")
            sc["keys"].sort()
            out[name] = sc
    return out


def keys_at(sc, n):
    bits = 0
    for p, b in sc["keys"]:
        if p <= n:
            bits = b
    return bits


class Runner:
    def __init__(self, snap):
        self.exec = set()
        self.spec = Spectrum(snap, self.exec)

    def run_to(self, addr, frames):
        """Run until PC reaches addr; False if frames ran out or the game
        restarted first (checked between chunks)."""
        spec = self.spec
        regs = spec.sim.registers
        end = regs[T] + frames * spec.frame
        self.exec.clear()
        while regs[T] < end:
            n = min(CHUNK_FRAMES * spec.frame, end - regs[T])
            if spec.run_tstates(n, stop=addr) == addr:
                return True
            if addr != RESTART and RESTART in self.exec:
                return False
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", nargs="?")
    ap.add_argument("-o", "--out")
    ap.add_argument("--scenarios", default="tests/scenarios.txt")
    ap.add_argument("--snap", default="build/c2.z80")
    ap.add_argument("--list", action="store_true", help="print the scenarios' names")
    args = ap.parse_args()
    scenarios = parse_scenarios(args.scenarios)
    if args.list:
        print("\n".join(scenarios))
        return 0
    if args.name not in scenarios:
        sys.exit(f"zxpass: no scenario {args.name!r} in {args.scenarios}")
    sc = scenarios[args.name]
    out = args.out or f"build/passes/zx_{sc['name']}.json"

    r = Runner(args.snap)
    spec, mem = r.spec, r.spec.mem
    regs = spec.sim.registers
    log = {"side": "zx", "scenario": sc["name"], "start": sc["start"], "passes": []}

    def fail(msg):
        log["stopped"] = msg
        print(f"zxpass {sc['name']}: {msg}", file=sys.stderr)
        write(out, log)
        return 1

    # The menu returns on 1 (Kempston); the attract loop starts on fire.
    if not r.run_to(ENTRY_MENU, SETUP_FRAMES):
        return fail("never reached the menu (52481)")
    spec.key("1", True)
    if not r.run_to(ATTRACT, SETUP_FRAMES):
        return fail("the menu didn't return to the attract loop (52290)")
    spec.key("1", False)
    spec.key("KF", True)
    if not r.run_to(NEW_GAME, SETUP_FRAMES):
        return fail("fire didn't start a game (52372)")
    spec.kempston = 0

    for a in RAND_RUN:
        mem[a] = sc["start"]
    mem[RAND_PTR] = RAND_RUN[0] & 0xFF
    mem[RAND_PTR + 1] = RAND_RUN[0] >> 8
    t0 = regs[T]

    for n in range(sc["passes"]):
        if not r.run_to(MAIN_LOOP, PASS_FRAMES):
            if RESTART in r.exec:
                log["stopped"] = f"restart (52235) before pass {n}"
            elif GAME_OVER in r.exec:
                log["stopped"] = f"game over (53101) before pass {n}"
            else:
                log["stopped"] = f"no pass {n} within {PASS_FRAMES} frames (PC {regs[PC]})"
            break
        log["passes"].append({
            "pass": n,
            "frame": (regs[T] - t0) // spec.frame,
            "vars": list(mem[VARS[0]:VARS[1]]),
            "extra": {str(a): mem[a] for a in EXTRA},
        })
        spec.kempston = keys_at(sc, n)
    else:
        log["stopped"] = "done"
    if "passes" in log and log["passes"]:
        room = log["passes"][0]["vars"][24030 - VARS[0]]
        print(f"zxpass {sc['name']}: room {room}, {len(log['passes'])} passes, {log['stopped']}")
    write(out, log)
    return 0


def write(path, log):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        json.dump(log, f, separators=(",", ":"))


if __name__ == "__main__":
    sys.exit(main())
