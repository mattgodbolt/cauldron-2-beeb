#!/usr/bin/env python3
"""The original's frame timeline for a scenario: every wait for a frame
(HALT), pass by pass.

    .venv/bin/python tools/zxtimeline.py NAME [-o build/timeline/zx_NAME.json]

Runs the scenario as tools/zxpass.py does (its docstring), stepping each
instruction, and logs for every main-loop pass (arrivals at 52430) its
waits: where each HALT was (its address), the time since the frame began
when it was reached, the frame it ended in, counted from the pass's
start, and the time of the work before it (since the last wait or the
pass's start) charged to each routine (`zNNNNN`: CALLed or RST'd, or the
interrupt 57664) on the call stack, once each (`incl`). tools/timeline.mjs
logs the port's; tools/timecmp.py compares them. Times are microseconds
(T-states / 3.5).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zxpass import (ATTRACT, ENTRY_MENU, MAIN_LOOP, NEW_GAME, RAND_PTR,  # noqa: E402
                    RAND_RUN, SETUP_FRAMES, Runner, keys_at, parse_scenarios)
from skoolkit.simutils import SP, T  # noqa: E402

HALT = 0x76
INTERRUPT = 57664
# CALL nn and CALL cc,nn; the RSTs.
CALLS = {0xCD, 0xC4, 0xCC, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4, 0xFC}
RSTS = {0xC7, 0xCF, 0xD7, 0xDF, 0xE7, 0xEF, 0xF7, 0xFF}


def top(counts, n=30):
    return {k: round(v / 3.5) for k, v in sorted(counts.items(), key=lambda kv: -kv[1])[:n]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("-o", "--out")
    ap.add_argument("--scenarios", default="tests/scenarios.txt")
    ap.add_argument("--snap", default="build/c2.z80")
    ap.add_argument("--passes", type=int, help="fewer passes than the scenario's")
    args = ap.parse_args()
    sc = parse_scenarios(args.scenarios)[args.name]
    passes = args.passes or sc["passes"]
    out = args.out or f"build/timeline/zx_{sc['name']}.json"

    r = Runner(args.snap)
    spec, mem = r.spec, r.spec.mem
    sim = spec.sim
    regs = sim.registers
    frame = spec.frame
    for label, addr in (("menu", ENTRY_MENU), ("attract", ATTRACT)):
        if not r.run_to(addr, SETUP_FRAMES):
            sys.exit(f"zxtimeline: never reached the {label}")
        spec.key("1", label == "menu")
    spec.key("KF", True)
    if not r.run_to(NEW_GAME, SETUP_FRAMES):
        sys.exit("zxtimeline: fire didn't start a game")
    spec.kempston = 0
    for a in RAND_RUN:
        mem[a] = sc["start"]
    mem[RAND_PTR] = RAND_RUN[0] & 0xFF
    mem[RAND_PTR + 1] = RAND_RUN[0] >> 8

    log = {"side": "zx", "scenario": sc["name"], "passes": []}
    st = {"pass": None, "halt": None, "sp": (regs[SP] - 1) & 0xFFFF,"incl": {}, "work": 0}
    stack = []  # (routine, SP once it's called)

    # The simulator calls this after running the instruction at pc, which
    # began at t0.
    def tf(pc, _i, t0):
        if st["halt"] is None:
            dt = regs[T] - t0
            st["work"] += dt
            incl = st["incl"]
            for r in {f[0] for f in stack}:
                incl[r] = incl.get(r, 0) + dt
        # The call stack: a return pops the calls whose SP it passes.
        sp = (regs[SP] - 1) & 0xFFFF  # (the game's SP starts at 0: as the highest)
        while stack and sp > stack[-1][1]:
            stack.pop()
        if (mem[pc] in CALLS or mem[pc] in RSTS) and sp < st["sp"]:
            stack.append((f"z{regs[24]}", sp))
        elif pc == INTERRUPT:
            stack.append(("irq", sp + 2))  # (after PUSH AF)
        st["sp"] = sp
        if st["halt"] is not None:
            if pc == st["halt"][0]:
                return
            addr, t_in = st["halt"]
            st["halt"] = None
            if st["pass"] is not None:
                p = st["pass"]
                p["waits"].append({"at": addr, "phase": round((t_in % frame) / 3.5),
                                   "frame": t0 // frame - p["f0"], "work": round(st["work"] / 3.5),
                                   "incl": top(st["incl"])})
            st["incl"], st["work"] = {}, 0
        if pc == MAIN_LOOP:
            if st["pass"] is not None:
                p = st["pass"]
                p["frames"] = t0 // frame - p["f0"]
                p["tail"] = {"work": round(st["work"] / 3.5), "incl": top(st["incl"])}
                log["passes"].append({k: v for k, v in p.items() if k != "f0"})
                spec.kempston = keys_at(sc, len(log["passes"]) - 1)
            st["pass"] = {"pass": len(log["passes"]), "f0": t0 // frame,
                          "phase": round((t0 % frame) / 3.5), "waits": []}
            st["incl"], st["work"] = {}, 0
            stack.clear()
            if len(log["passes"]) >= passes:
                raise StopIteration
        if mem[pc] == HALT:
            st["halt"] = (pc, t0)

    try:
        while True:
            sim.trace(regs[24], None, 0, regs[T] + 50 * frame, 1, None, None, None,
                      lambda pc: None, tf)
    except StopIteration:
        pass
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w") as f:
        json.dump(log, f, separators=(",", ":"))
    print(f"zxtimeline {sc['name']}: {len(log['passes'])} passes -> {out}")


if __name__ == "__main__":
    sys.exit(main())
