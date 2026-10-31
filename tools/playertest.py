#!/usr/bin/env python3
"""Check the player's and the input's transcription against the original.

    .venv/bin/python tools/playertest.py [--passes N] [--seed S] [-v]

The original plays on SkoolKit's simulator (tools/zx.py's Spectrum) with
random Kempston controls (and firing enabled now and then, 24017). At each
main-loop pass, from the state before the controls are read (52444), the
original runs its controls, TICK_REVERSE, FIRE and PLAYER (to 52466); the
port's z53149, z53163 and z54530 run on py65 from the same state: the
variables (24000-25099), attributes, the screen (its lit pixels, laid out
as our MODE 1 screen, which zx_read reads) and the tables (57726-64998, at
r_tables). The routines the player calls that others own are emulated
here from the original's code (57307, 57326, 57355) or only logged with
their arguments (55624, 55363, 57568, 52781, 56571), and the logs and the
player's variables are compared.

Then the input: the keyboard reader (52695) for every set of the six keys
against the original's with the Interface II keys, the joystick reader
(52658) for every Kempston nibble and fire against the original's, and
52767's abort (reaching 52235).

The port is assembled for the test into build/playertest/ (with r_tables
at &8000 if no source places it yet).
"""
import argparse
import json
import os
import random
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from zx import Spectrum  # noqa: E402
from skoolkit.simutils import A, B, C, D, E, F, H, L, PC, SP  # noqa: E402
from py65.devices.mpu6502 import MPU  # noqa: E402
from py65.memory import ObservableMemory  # noqa: E402

IXH, IXL = 8, 9
OUT = "build/playertest"
BARON = os.environ.get("BARON", "../baron/build/src/baron")
SENTINEL = 0xFFF0

# The player's variables compared after each pass (object 0 is 24077).
COMPARED = [24009, 24010, 24014, 24015, 24016, 24026, 24027, 24028, 24029, 24031,
            24040, 24041, 59450] + [24077 + n for n in (3, 5, 6, 7, 12, 13, 14, 19)]
LOGGED = {55624: "SetAnim", 55363: "Spawn", 57568: "Magic", 52781: "SfxStart", 56571: "Kill"}


def build():
    os.makedirs(OUT, exist_ok=True)
    subprocess.run(["python3", "tools/mksyms.py", f"{OUT}/syms.6502", f"{OUT}/stubs.6502"]
                   + sorted(f"src/{f}" for f in os.listdir("src") if f.endswith(".6502"))
                   + sorted(f"build/data/{f}" for f in os.listdir("build/data") if f.endswith(".6502")),
                   check=True, stdout=subprocess.DEVNULL)
    # A copy of main.6502 beside them, using our syms and stubs.
    src = os.path.relpath("src", OUT)
    main = open("src/main.6502").read()
    main = re.sub(r'^(\s*(?:INCLUDE|INCBIN)\s+")', lambda m: m.group(1) + src + "/", main, flags=re.M)
    main = main.replace(src + "/../build/syms.6502", "syms.6502") \
        .replace(src + "/../build/stubs.6502", "stubs.6502")
    srcs = "".join(open(f"src/{f}").read() for f in os.listdir("src")) + \
        "".join(open(f"build/data/{f}").read() for f in os.listdir("build/data") if f.endswith(".6502"))
    defines = [] if re.search(r"^\s*\.r_tables\b|^\s*r_tables\s*=", srcs, re.M) else ["-D", "r_tables=&8000"]
    open(f"{OUT}/main.6502", "w").write(main)
    subprocess.run([BARON] + defines + ["-p", OUT, "--symbols", f"{OUT}/syms.json", f"{OUT}/main.6502"],
                   check=True)
    syms = {}
    for asm in json.load(open(f"{OUT}/syms.json"))["assemblies"]:
        for sec in asm["sections"]:
            for kind in sec.values():
                if isinstance(kind, dict):
                    for k, v in kind.items():
                        if "@" not in k and isinstance(v, dict) and "value" in v:
                            syms[k] = v["value"]
    return syms


class Beeb:
    """The port's code on py65, with the original's routines that others
    own emulated or logged."""

    def __init__(self, syms):
        self.s = syms
        self.mem = ObservableMemory()
        code = open(f"{OUT}/C2", "rb").read()[: syms["code_end"] - syms["code_start"]]
        self.mem[syms["code_start"]: syms["code_start"] + len(code)] = list(code)
        self.cpu = MPU(self.mem)
        self.log = []
        self.keys = set()           # internal key numbers held
        self.key_sel = 0
        self.adc = [0x80, 0x80]
        self.adc_ch = 0
        self.fire_button = False
        self.mem.subscribe_to_write([0xFE4F], self._key_write)
        self.mem.subscribe_to_read([0xFE4F], self._key_read)
        self.mem.subscribe_to_write([0xFEC0], self._adc_start)
        self.mem.subscribe_to_read([0xFEC0], lambda a: self.adc_ch)        # converted at once
        self.mem.subscribe_to_read([0xFEC1], lambda a: self.adc[self.adc_ch])
        self.mem.subscribe_to_read([0xFE40], lambda a: 0xFF ^ (0x10 if self.fire_button else 0))
        self.call(syms["init_zxscreen"])
        self.hooks = {syms[f"z{n}"]: n for n in (57307, 57326, 57355) + tuple(LOGGED)}

    def _key_write(self, a, v):
        self.key_sel = v & 0x7F

    def _key_read(self, a):
        return self.key_sel | (0x80 if self.key_sel in self.keys else 0)

    def _adc_start(self, a, v):
        self.adc_ch = v & 3

    def a(self, n):
        """Our address of the original's byte n."""
        for lo, hi, base in ((22528, 23295, "attrs"), (24000, 25099, "vars"), (57726, 64998, "r_tables")):
            if lo <= n <= hi:
                return self.s[base] + n - lo
        raise ValueError(n)

    def z80(self, addr):
        """The original's address of our r_tables address."""
        return addr - self.s["r_tables"] + 57726

    def load(self, zmem):
        m = self.mem._subject
        for lo, hi in ((22528, 23295), (24000, 25099), (57726, 64998)):
            base = self.a(lo)
            m[base: base + hi - lo + 1] = zmem[lo: hi + 1]
        scr = self.s["screen"]
        for y in range(192):
            row = 16384 + ((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2)
            ours = scr + (y >> 3) * 512 + (y & 7)
            for x in range(32):
                b = zmem[row + x]
                m[ours + x * 16] = b >> 4          # logical colour 1, the lit pixels
                m[ours + x * 16 + 8] = b & 15

    def reg(self, name):
        return self.mem._subject[self.s[name]]

    def setreg(self, name, v):
        self.mem._subject[self.s[name]] = v & 0xFF

    def hl(self):
        return self.reg("rl") | self.reg("rh") << 8

    def rts(self):
        cpu = self.cpu
        lo = self.mem[0x100 + ((cpu.sp + 1) & 0xFF)]
        hi = self.mem[0x100 + ((cpu.sp + 2) & 0xFF)]
        cpu.sp = (cpu.sp + 2) & 0xFF
        cpu.pc = ((hi << 8) | lo) + 1

    def hook(self, n):
        cpu, m = self.cpu, self.mem._subject
        if n == 57307:                  # LineAddr: from the row table 58883
            t = self.a(58883) + 2 * (cpu.a >> 3)
            self.setreg("rl", m[t])
            self.setreg("rh", m[t + 1] + (cpu.a & 7))
        elif n == 57326:                # ATTR_AT
            d = ((self.reg("rh") >> 3) & 7) | 88
            self.setreg("rd", d)
            self.setreg("re", self.reg("rl"))
            cpu.a = m[self.a(d * 256 + self.reg("rl"))]
        elif n == 57355:                # IS_SOLID
            m[self.a(24010)] = cpu.a
            solid = cpu.a in m[self.a(57808): self.a(57808) + 9]
            cpu.p = (cpu.p | cpu.ZERO) if solid else (cpu.p & ~cpu.ZERO)
        else:
            regs = {r: self.reg(r) for r in ("rb", "rc", "rd", "re")}
            if n == 55624:              # SetAnim: the fields the player reads
                slot = self.s["vars"] + 77 + 20 * cpu.a
                m[slot + 13] = regs["rb"]
                m[slot + 12] = m[slot + 14] = m[slot + 19] = 0
                self.log.append((LOGGED[n], cpu.a, regs["rb"]))
            elif n == 55363:
                self.log.append((LOGGED[n], cpu.a, regs["re"], regs["rd"], regs["rc"], regs["rb"]))
            elif n == 57568:
                self.log.append((LOGGED[n], self.z80(regs["re"] | regs["rd"] << 8)))
            elif n == 52781:
                self.log.append((LOGGED[n], self.z80(self.hl())))
            else:
                self.log.append((LOGGED[n],))
        self.rts()

    def call(self, addr, a=0, limit=200000):
        cpu = self.cpu
        cpu.sp = 0xFF
        cpu.a = a
        ret = SENTINEL - 1
        self.mem[0x1FF], self.mem[0x1FE] = ret >> 8, ret & 0xFF
        cpu.sp = 0xFD
        cpu.pc = addr
        hooks = getattr(self, "hooks", {})
        for _ in range(limit):
            if cpu.pc == SENTINEL:
                return cpu.a
            if cpu.pc in hooks:
                self.hook(hooks[cpu.pc])
                continue
            if cpu.pc == self.s["unwritten"]:
                raise RuntimeError(f"reached unwritten {self.reg('unwritten_at') if 'unwritten_at' in self.s else ''}"
                                   f" (A={cpu.a} X={cpu.x})")
            cpu.step()
        raise RuntimeError(f"no return from &{addr:04X}")


# The original's instructions run in the player's code, for the coverage.
PLAYER_CODE = [(53149, 53309), (54513, 55284)]
covered = set()


def z80_run(spec, start, stop, logged=None):
    """Run the original from start to stop one instruction at a time,
    logging the calls to LOGGED's routines."""
    sim, r = spec.sim, spec.sim.registers
    r[PC] = start
    while r[PC] != stop:
        pc = r[PC]
        covered.add(pc)
        if logged and logged[-1][0] == "Kill":
            pass                        # (a tail jump: the rest is 56571's own)
        elif logged is not None and pc in LOGGED:
            name = LOGGED[pc]
            if pc == 55624:
                logged.append((name, r[A], r[B]))
            elif pc == 55363:
                logged.append((name, r[A], r[E], r[D], r[C], r[B]))
            elif pc == 57568:
                logged.append((name, r[E] | r[D] << 8))
            elif pc == 52781:
                logged.append((name, r[L] | r[H] << 8))
            else:
                logged.append((name,))
        sim.run()


def test_passes(syms, passes, seed, verbose):
    rnd = random.Random(seed)
    spec = Spectrum("build/c2.z80")
    spec.frames(100)
    for k in ("1", "4"):                # menu: Kempston, then play
        spec.key(k, True); spec.frames(10); spec.key(k, False); spec.frames(50)
    spec.key("KF", True); spec.frames(10); spec.key("KF", False)
    beeb = Beeb(syms)
    held, hold_for, fails, seen, games, tested = 0, 0, 0, set(), 0, 0
    for n in range(passes):
        if hold_for == 0:
            held = rnd.choice([0, 0, 1, 2, 4, 8, 16, 16, 18, 17, 20, 24, 2 + 8, 1 + 4])
            hold_for = rnd.randint(1, 30)
        hold_for -= 1
        spec.kempston = held
        if rnd.random() < 0.01:
            spec.mem[24017] = rnd.choice([0, 1])
        for _ in range(10):             # game over: fire, the menu's 4, fire
            if spec.run_tstates(10 * 50 * spec.frame, stop=52444) == 52444:
                break
            games += 1
            for f in (0, 16, 0, "4", 16, 0):
                if f == "4":
                    spec.key("4", True); spec.frames(10); spec.key("4", False)
                else:
                    spec.kempston = f
                spec.frames(25)
        else:
            print(f"the original never came back to 52444 (pass {n}, PC {spec.sim.registers[PC]}, "
                  f"lives {spec.mem[24035]}, dying {spec.mem[24034]}, outside {spec.mem[24012]})")
            return 1
        z = spec.mem
        if z[24034] or z[24012]:
            continue                    # dying or outside: the player's code doesn't run
        tested += 1
        # now and then an odd state, for the paths play rarely takes: no
        # vertical direction, a stale deadly hit_attr, the edge bits
        if rnd.random() < 0.02:
            z[24080] = rnd.randrange(16)
        if rnd.random() < 0.02:
            z[24014] = 1
        if rnd.random() < 0.02:
            z[24031] = rnd.choice([0, 4, 8, 12])
        if rnd.random() < 0.02:
            z[24015] = rnd.choice([1, 2])
        if rnd.random() < 0.05:
            # random pixels on a row just under or over the pumpkin, and a
            # solid attribute (white, 7) under them: feet, edges, gaps
            y = (z[24084] + z[24095] + rnd.randrange(4)) if rnd.random() < 0.7 else z[24084] - 1 - rnd.randrange(4)
            if 33 <= y < 190 and z[24083] >= 12:
                row = 16384 + ((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2)
                col = (z[24083] - 12) >> 2
                for c in range(col, min(col + 3, 32)):
                    z[row + c] = rnd.choice([0, 0x0F, 0xF0, 0xC3, 0x3C, rnd.randrange(256)])
                    z[22528 + (y >> 3) * 32 + c] = 7
        zlog = []
        z80_run(spec, 52444, 52451)     # the controls into 24020
        beeb.load(z)                    # (the state with this pass's controls)
        z80_run(spec, 52451, 52466, zlog)
        beeb.log = []
        beeb.call(syms["z53149"])
        if beeb.mem[beeb.a(24020)] & 16:
            beeb.call(syms["z53163"])
        beeb.call(syms["z54530"])
        bad = []
        killed = any(e[0] == "Kill" for e in zlog)
        for addr in COMPARED:
            if killed and (addr == 24014 or addr >= 24077):
                continue                # (56571's, which the test doesn't emulate)
            ours, theirs = beeb.mem[beeb.a(addr)], z[addr]
            if ours != theirs:
                bad.append(f"{addr}: ours {ours} theirs {theirs}")
        if beeb.log != zlog:
            bad.append(f"calls: ours {beeb.log} theirs {zlog}")
        for e in zlog:
            seen.add(e[0])
        seen.add(("state", z[24090], "dir", z[24080] & 3))
        if bad:
            fails += 1
            print(f"pass {n} (room {z[24030]} X {z[24083]} Y {z[24084]}): " + "; ".join(bad))
            if fails > 10:
                break
        elif verbose:
            print(f"pass {n}: room {z[24030]} X {z[24083]} Y {z[24084]} v {z[24026]} calls {zlog}")
    calls = sorted(s for s in seen if isinstance(s, str))
    # the original's instructions in the player's code never run
    skool = open("build/c2.skool").read() if os.path.exists("build/c2.skool") else ""
    insns = [int(a) for a in re.findall(r"^[c* ]?(\d{5}) [A-Z]", skool, re.M)]
    insns += [54530, 54533, 54534, 54535]     # (54530-54538, marked data in the control file)
    missed = sorted(a for a in set(insns) if any(lo <= a <= hi for lo, hi in PLAYER_CODE) and a not in covered)
    print(f"the original's player instructions never run: {len(missed)}"
          + (": " + " ".join(map(str, missed)) if missed else ""))
    print(f"passes: {tested} tested of {passes} ({games} restarts), failures: {fails}; "
          f"calls seen: {', '.join(calls)}")
    return 1 if fails else 0


# The Spectrum keys of the original's Interface II table, in its order
# (UP, DOWN, LEFT, RIGHT, FIRE, ABORT), and the BBC's (decision 6).
ZX_KEYS = ["9", "8", "6", "7", "0", "A"]


def test_input(syms):
    spec = Spectrum("build/c2.z80")
    spec.mem[57784:57808] = spec.mem[57760:57784]   # (52218: the active keys = the defaults)
    beeb = Beeb(syms)
    beeb.load(spec.mem)
    fails = 0
    bbc_keys = [beeb.mem[syms["keys"] + i] for i in range(6)]
    # the keyboard: every set of the six keys
    for combo in range(64):
        for i, k in enumerate(ZX_KEYS):
            spec.key(k, bool(combo >> i & 1))
        spec.sim.registers[SP] = 0xFF00
        spec.mem[0xFF00], spec.mem[0xFF01] = 0xFF, 0xFF   # returns to 65535
        z80_run(spec, 52695, 65535)
        theirs = spec.sim.registers[A]
        beeb.keys = {bbc_keys[i] for i in range(6) if combo >> i & 1}
        ours = beeb.call(syms["z52695"])
        if ours != theirs:
            fails += 1
            print(f"keys {combo:06b}: ours {ours} theirs {theirs}")
    for k in ZX_KEYS:
        spec.key(k, False)
    beeb.keys = set()
    # the joystick: every Kempston nibble, with and without fire
    axis = {0: 0x80, 1: 0x00, 2: 0xFF}  # per axis: centre, low (right/down), high (left/up)
    for nib in range(32):
        spec.kempston = nib
        spec.sim.registers[SP] = 0xFF00
        z80_run(spec, 52658, 65535)
        theirs = spec.sim.registers[A]
        r, l, d, u = nib & 1, nib >> 1 & 1, nib >> 2 & 1, nib >> 3 & 1
        if (r and l) or (d and u):
            continue                    # an analogue axis can't be both ways
        beeb.adc = [axis[1] if r else axis[2] if l else axis[0], axis[1] if d else axis[2] if u else axis[0]]
        beeb.fire_button = bool(nib & 16)
        for _ in range(3):              # one channel converts per read
            ours = beeb.call(syms["z52658"])
        if ours != theirs:
            fails += 1
            print(f"kempston {nib:05b}: ours {ours} theirs {theirs}")
    beeb.fire_button = False
    beeb.adc = [0x80, 0x80]
    beeb.keys = {0x70}                  # ESCAPE: the joystick reader's abort
    for _ in range(3):
        ours = beeb.call(syms["z52658"])
    if ours != 64:
        fails += 1
        print("joystick reader: ESCAPE isn't abort")
    # 52767: through the vector at 57726, abort restarts at 52235
    v = beeb.a(57726)
    beeb.mem[v], beeb.mem[v + 1] = syms["z52695"] & 0xFF, syms["z52695"] >> 8
    beeb.keys = {bbc_keys[2], bbc_keys[4]}
    ours = beeb.call(syms["z52767"])
    if ours != 4 + 16 or not beeb.cpu.p & beeb.cpu.ZERO:
        fails += 1
        print(f"52767: left and fire gave {ours}, Z {bool(beeb.cpu.p & beeb.cpu.ZERO)}")
    beeb.keys = {0x70}
    try:
        beeb.call(syms["z52767"])
        fails += 1
        print("52767: abort returned")
    except RuntimeError as e:
        if "52235" not in str(e) and f"A={52235 & 0xFF} X={52235 >> 8}" not in str(e):
            fails += 1
            print(f"52767: abort went elsewhere: {e}")
    print(f"input: failures: {fails}")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--passes", type=int, default=600)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("-v", action="store_true")
    args = ap.parse_args()
    syms = build()
    return test_input(syms) | test_passes(syms, args.passes, args.seed, args.v)


if __name__ == "__main__":
    sys.exit(main())
