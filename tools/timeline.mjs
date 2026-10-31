#!/usr/bin/env node
// The port's frame timeline for a scenario: every wait for a frame
// (wait_vsync), pass by pass, and what ran before each. The BBC half of
// tools/zxtimeline.py's log (tools/timecmp.py compares them).
//
//   node tools/timeline.mjs NAME [-o build/timeline/bbc_NAME.json] [--passes N]
//        [--scenarios tests/scenarios.txt] [--disc build/cauldron2.ssd] [--model B-DFS1.2]
//
// Runs jsbeeb in this process (not through the MCP server) so that every
// instruction can be watched: the scenario goes as tools/beepass.mjs runs
// it (its header). For each main-loop pass (arrivals at z52430) it logs
// each wait: its caller, the time since the VSync when it was reached
// (microseconds), the frame it ended in counted from the pass's start, and
// the time of the work before it (since the last wait or the pass's
// start) charged to the routines on the call stack (`incl`, each routine
// once) and to the nearest label (`excl`). Each pass also logs its
// interrupts: how many, and their time (`irq`, waits included; the VSyncs'
// alone too).
import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { dirname, resolve } from "path";
import { pathToFileURL } from "url";
import { MachineSession } from "jsbeeb/machine-session";
import { loadSymbols } from "./beeb.mjs";

const args = process.argv.slice(2);
const opt = (name, dflt) => {
    const i = args.indexOf(name);
    if (i < 0) return dflt;
    const v = args[i + 1];
    args.splice(i, 2);
    return v;
};
const scenFile = opt("--scenarios", "tests/scenarios.txt");
const disc = opt("--disc", "build/cauldron2.ssd");
const symbols = opt("--symbols", disc.replace(/\.ssd$/, ".json"));
const model = opt("--model", process.env.CAULDRON_MODEL || "B-DFS1.2");
const passLimit = opt("--passes", null);
const outOpt = opt("-o", null);
const name = args[0];
const out = outOpt ?? `build/timeline/bbc_${name}.json`;

// tools/beepass.mjs's scenario format and key mapping.
const BITS = { R: 1, L: 2, D: 4, U: 8, F: 16 };
function scenario(path, want) {
    for (const raw of readFileSync(path, "utf8").split("\n")) {
        const f = raw.split("#")[0].trim().split(/\s+/).filter(Boolean);
        if (f[0] !== want) continue;
        const sc = { name: f[0], start: 0, passes: 100, keys: [] };
        for (const fld of f.slice(1)) {
            if (fld.startsWith("start=")) sc.start = parseInt(fld.slice(6));
            else if (fld.startsWith("passes=")) sc.passes = parseInt(fld.slice(7));
            else {
                const [p, keys] = fld.split(":");
                let bits = 0;
                for (const k of keys.replace(/\+/g, "")) if (k !== "-") bits |= BITS[k];
                sc.keys.push([parseInt(p), bits]);
            }
        }
        sc.keys.sort((a, b) => a[0] - b[0]);
        return sc;
    }
    throw new Error(`no scenario ${want} in ${path}`);
}
const sc = scenario(scenFile, name);
const passes = passLimit ? parseInt(passLimit) : sc.passes;
const keysAt = (n) => sc.keys.reduce((bits, [p, b]) => (p <= n ? b : bits), 0);
// Internal key numbers: X, Z, /, :, RETURN for the Kempston bits.
const KEY = { 1: 66, 2: 97, 4: 104, 8: 72, 16: 73 };
const SPACE = 98, K1 = 48, RETURN = 73;
const matrix = (n) => [n & 15, n >> 4];

const S = loadSymbols(symbols);
const labels = Object.entries(S)
    .filter(([k, v]) => typeof v === "number" && !k.includes(".") && v >= 0x0e00 && v < 0xc000 && /^[a-z]/.test(k)
        && !/^(roomdata|room_pack|room_buf|r_|tile_(lo|hi|attr|blank)$)/.test(k) && !/^a\d{5}$/.test(k))
    .sort((a, b) => a[1] - b[1]);
const labelOf = new Map();
const routine = (a) => {
    let r = labelOf.get(a);
    if (r !== undefined) return r;
    if (a >= 0xc000) r = "OS";
    else {
        let lo = 0, hi = labels.length - 1;
        r = "?";
        while (lo <= hi) {
            const m = (lo + hi) >> 1;
            if (labels[m][1] <= a) { r = labels[m][0]; lo = m + 1; } else hi = m - 1;
        }
    }
    labelOf.set(a, r);
    return r;
};

const session = new MachineSession(model);
await session.initialise();
await session.boot(30);
await session.loadDiscImage(pathToFileURL(resolve(disc)).href);
session.keyDownRaw(matrix(0));                 // SHIFT: autoboot
session.reset(true);
await session.runFor(2e6);
session.keyUpRaw(matrix(0));
const cpu = session._machine.processor;
const until = async (label, secs = 60) => session.runUntilAddress(S[label], secs);
await until("shown");
session.keyDownRaw(matrix(SPACE));
await until("z52180");
session.keyUpRaw(matrix(SPACE));
await until("z52481");
session.keyDownRaw(matrix(K1));
await until("z52290");
session.keyUpRaw(matrix(K1));
session.keyDownRaw(matrix(RETURN));
await until("z52372");
session.keyUpRaw(matrix(RETURN));
const rnd = S.vars + (25092 - 24000);
session.writeMemory(rnd, new Array(8).fill(sc.start));
session.writeMemory(S.a61248, [rnd & 0xff, rnd >> 8]);

// The instructions that matter: wait_vsync's entry and its RTS, and the
// VSync's INC vsyncs in the handler.
const mem = (a, n) => session.readMemory(a, n);
const waitRts = S.wait_vsync + mem(S.wait_vsync, 16).indexOf(0x60);
const handler = mem(S.irq_handler, 128);
let incVsyncs = -1;
for (let i = 0; i < handler.length - 1; i++)
    if (handler[i] === 0xe6 && handler[i + 1] === S.vsyncs) { incVsyncs = S.irq_handler + i; break; }
if (incVsyncs < 0) throw new Error("no INC vsyncs in irq_handler");

const cycles = () => session.elapsedCycles;
const log = { side: "bbc", scenario: sc.name, passes: [] };
let pass = null, held = 0, frames = 0, lastVsync = 0;
let seg = null;                       // the work since the last wait
let waitIn = null;                    // [caller, cycles at entry]
let stack = [], lastPc = -1, lastOp = 0, lastT = 0, done = false;
// Every interrupt, from the OS's entry to the RTI, waits included.
const osIrq = mem(0xfffe, 2)[0] | (mem(0xffff, 1)[0] << 8);
let inIrq = false, irqs = 0, irqCycles = 0, irqT0 = 0, irqV = false, vsyncCycles = 0;
const newSeg = () => ({ incl: {}, excl: {}, cycles: 0 });
// (In microseconds, the most first.)
const top = (o, n) => Object.fromEntries(Object.entries(o).sort((a, b) => b[1] - a[1]).slice(0, n)
    .map(([k, v]) => [k, Math.round(v / 2)]));

const hold = (bits) => {
    for (const [bit, key] of Object.entries(KEY)) {
        const b = Number(bit);
        if ((bits & b) && !(held & b)) session.keyDownRaw(matrix(key));
        if (!(bits & b) && (held & b)) session.keyUpRaw(matrix(key));
    }
    held = bits;
};

session.onExecute((pc) => {
    const t = cycles();
    const dt = t - lastT;
    lastT = t;
    // Charge the instruction just run.
    if (seg && waitIn === null && lastPc >= 0) {
        const r = routine(lastPc);
        seg.excl[r] = (seg.excl[r] ?? 0) + dt;
        const seen = new Set();
        for (const f of stack) if (!seen.has(f)) { seen.add(f); seg.incl[f] = (seg.incl[f] ?? 0) + dt; }
        seg.cycles += dt;
    }
    if (inIrq) irqCycles += dt;
    if (lastOp === 0x40 && inIrq) {
        inIrq = false;
        if (irqV) vsyncCycles += t - irqT0;
    }
    if (pc === osIrq) { inIrq = true; irqs++; irqT0 = t; irqV = false; }
    if (pc === incVsyncs) irqV = true;
    // The call stack, from the instruction just run.
    if (lastOp === 0x20) stack.push(routine(pc));
    else if (lastOp === 0x60 || lastOp === 0x40) stack.pop();
    if (pc === S.irq_handler && lastOp !== 0x20) stack.push("irq_handler");
    const op = mem(pc, 1)[0];
    lastPc = pc;
    lastOp = op;

    if (pc === incVsyncs) { frames++; lastVsync = t; }
    if (pc === S.wait_vsync && pass) {
        waitIn = [stack[stack.length - 2] ?? "?", t, frames, lastVsync];
    }
    if (pc === waitRts && waitIn && pass) {
        pass.waits.push({
            caller: waitIn[0], phase: Math.round((waitIn[1] - waitIn[3]) / 2), frame: frames - pass.f0,
            work: Math.round(seg.cycles / 2), incl: top(seg.incl, 30), excl: top(seg.excl, 30),
        });
        waitIn = null;
        seg = newSeg();
    }
    if (pc === S.z52430) {
        if (pass) {
            pass.frames = frames - pass.f0;
            pass.irq = { n: irqs, us: Math.round(irqCycles / 2), vsync_us: Math.round(vsyncCycles / 2) };
            pass.tail = { work: Math.round(seg.cycles / 2), incl: top(seg.incl, 30), excl: top(seg.excl, 30) };
            delete pass.f0;
            log.passes.push(pass);
            hold(keysAt(log.passes.length - 1));
        }
        if (log.passes.length >= passes) { done = true; cpu.stop(); return; }
        pass = { pass: log.passes.length, f0: frames, phase: Math.round((t - lastVsync) / 2), waits: [] };
        seg = newSeg();
        stack = [];
        irqs = irqCycles = vsyncCycles = 0;
    }
});
lastT = cycles();
while (!done) await session.runFor(400000);
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, JSON.stringify(log));
console.log(`timeline ${sc.name}: ${log.passes.length} passes -> ${out}`);
process.exit(0);
