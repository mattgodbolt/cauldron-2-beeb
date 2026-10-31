#!/usr/bin/env node
// The port's state at every main-loop pass, for a scenario: the BBC half
// of the pass-by-pass oracle (tools/zxpass.py is the original's, and its
// docstring says how a run goes; tools/passcmp.py compares them).
//
//   node tools/beepass.mjs NAME [-o build/passes/bbc_NAME.json]
//        [--scenarios tests/scenarios.txt] [--disc build/cauldron2.ssd] [--symbols DISC.json]
//
// Boots the disc, takes the front end as the original's (1, then fire),
// and at the new game (z52372) aims the random pointer (a61248) at a run
// of bytes holding the scenario's start, as zxpass does. Then at each
// arrival at z52430 it logs `vars` and the extra bytes (by their aNNNNN
// symbols, else the region label) and holds the scenario's keys.
//
// An unwritten routine stops the machine at `unwritten_stop`, with the
// original's address in `unwritten_at`: the run reports "stopped at stub
// NNNNN" and keeps what it logged. Every run to a label has a timeout.
import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { dirname } from "path";
import { startBeeb } from "./beeb.mjs";

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
const outOpt = opt("-o", null);
const name = args[0];
const out = outOpt ?? `build/passes/bbc_${name}.json`;

// The format is zxpass.py's (parse_scenarios), described in the file.
const BITS = { R: 1, L: 2, D: 4, U: 8, F: 16 };
function parseScenarios(path) {
    const scs = {};
    readFileSync(path, "utf8").split("\n").forEach((raw, i) => {
        const f = raw.split("#")[0].trim().split(/\s+/).filter(Boolean);
        if (!f.length) return;
        const sc = { name: f[0], start: 0, passes: 100, keys: [] };
        for (const fld of f.slice(1)) {
            if (fld.startsWith("start=")) sc.start = parseInt(fld.slice(6));
            else if (fld.startsWith("passes=")) sc.passes = parseInt(fld.slice(7));
            else if (fld.includes(":")) {
                const [p, keys] = fld.split(":");
                let bits = 0;
                for (const k of keys.replace(/\+/g, "")) {
                    if (k === "-") continue;
                    if (!(k in BITS)) throw new Error(`${path}:${i + 1}: unknown key ${k}`);
                    bits |= BITS[k];
                }
                sc.keys.push([parseInt(p), bits]);
            } else throw new Error(`${path}:${i + 1}: can't read ${fld}`);
        }
        sc.keys.sort((a, b) => a[0] - b[0]);
        scs[sc.name] = sc;
    });
    return scs;
}
const keysAt = (sc, n) => sc.keys.reduce((bits, [p, b]) => (p <= n ? b : bits), 0);

// The BBC's keys for the Kempston bits (the port's controls).
const BBC_KEY = { 1: "X", 2: "Z", 4: "SLASH", 8: "COLON_STAR", 16: "RETURN" };

// As zxpass.py: the run the random pointer is aimed at, and the extras.
const RAND_RUN = [25092, 25100];
const EXTRA_RANGES = [[59450, 59450], [59582, 59582], [61521, 61572], [58804, 58810], [58813, 58814]];
const REGIONS = [[24000, 25099, "vars"], [57726, 64998, "r_tables"]];

const SETUP_SECS = 60;
const PASS_SECS = 30;
const UNDEFINED_SECS = 5;

const scenarios = parseScenarios(scenFile);
const sc = scenarios[name];
if (!sc) {
    console.error(`beepass: no scenario ${name} in ${scenFile}`);
    process.exit(2);
}

const log = { side: "bbc", scenario: sc.name, start: sc.start, passes: [], symbols: {}, missing: [] };
const save = () => {
    mkdirSync(dirname(out), { recursive: true });
    writeFileSync(out, JSON.stringify(log));
};

const beeb = await startBeeb({ model, symbols });
const S = beeb.syms;
for (const k of ["vars", "r_tables"]) if (k in S) log.symbols[k] = S[k];

// Where the original's byte n is: its aNNNNN, else its region's label.
function where(n) {
    if (`a${n}` in S) return S[`a${n}`];
    for (const [lo, hi, label] of REGIONS) if (lo <= n && n <= hi && label in S) return S[label] + n - lo;
    return undefined;
}

class Stop extends Error {}

// Breakpoints that end a run wherever it is: the stubs' stop, and, once a
// game is running, the restart.
const stops = {};
async function stopAt(label, why) {
    if (!(label in S)) return;
    const r = await beeb.breakpoint(label);
    stops[r.breakpoint_id] = why;
}

// What stopped a run early, as a Stop: a stub or another breakpoint.
async function stopped(r, what) {
    if (r.stopped_reason !== "breakpoint" && r.stopped_reason !== "pending_breakpoint") return;
    const why = stops[r.breakpoint?.id];
    if (why === "stub") throw new Stop(`stopped at stub ${await beeb.peekw("unwritten_at")}`);
    throw new Stop(`${why ?? "a breakpoint"} before ${what}`);
}

// Run for a while; a stub or a restart on the way throws Stop.
async function runFor(secs) {
    await stopped(await beeb.run(secs), `${secs}s ran`);
}

// Run to a label; a stub or a restart on the way throws Stop. A label not
// yet written still runs a little, so a stub before it is the report.
async function until(label, secs) {
    if (!(label in S)) {
        await runFor(UNDEFINED_SECS);
        throw new Stop(`${label} isn't defined yet`);
    }
    const r = JSON.parse(
        (await beeb.call("run_until_address", { session_id: beeb.session_id, address: S[label], timeout_secs: secs }))
            .content.find((c) => c.type === "text").text,
    );
    if (r.reached) return r;
    await stopped(r, label);
    throw new Stop(`${label} not reached in ${secs}s (PC ${r.registers?.pc})`);
}

let held = 0;
async function hold(bits) {
    for (const [bit, key] of Object.entries(BBC_KEY)) {
        const b = Number(bit);
        if ((bits & b) && !(held & b)) await beeb.keyDown(key);
        if (!(bits & b) && (held & b)) await beeb.keyUp(key);
    }
    held = bits;
}

let status = 0;
try {
    await beeb.boot(disc);
    await stopAt("unwritten_stop" in S ? "unwritten_stop" : "unwritten", "stub");
    await until("shown", SETUP_SECS);
    // Any key leaves the title for the original's entry.
    await beeb.keyDown("SPACE");
    await until("z52180", SETUP_SECS);
    await beeb.keyUp("SPACE");
    // The menu: 1 returns from it (the original's Kempston; the port's own
    // controls), then fire starts a game from the attract loop.
    if ("z52481" in S) await until("z52481", SETUP_SECS);
    await beeb.keyDown("K1");
    if ("z52290" in S) await until("z52290", SETUP_SECS);
    else await runFor(0.5);
    await beeb.keyUp("K1");
    await beeb.keyDown("RETURN");
    await until("z52372", SETUP_SECS);
    await beeb.keyUp("RETURN");

    const rnd = where(RAND_RUN[0]);
    const ptr = where(61248);
    if (rnd === undefined || ptr === undefined) throw new Stop("can't find vars or a61248 to fix the start room");
    await beeb.write(rnd, new Array(RAND_RUN[1] - RAND_RUN[0]).fill(sc.start));
    await beeb.write(ptr, [rnd & 0xff, rnd >> 8]);

    // Read a range at once where the BBC keeps it in one piece.
    const extras = [];
    for (const [lo, hi] of EXTRA_RANGES) {
        if (where(lo) !== undefined && where(hi) - where(lo) === hi - lo) {
            extras.push([lo, hi]);
            continue;
        }
        for (let a = lo; a <= hi; a++) {
            if (where(a) === undefined) log.missing.push(a);
            else extras.push([a, a]);
        }
    }
    if (log.missing.length) console.error(`beepass ${sc.name}: no symbol for ${log.missing.join(" ")}, not logged`);

    await stopAt("z52235", "restart (52235)");
    await stopAt("z53101", "game over (53101)");
    const f0 = JSON.parse(await beeb.regs()).frame_count;
    for (let n = 0; n < sc.passes; n++) {
        const r = await until("z52430", PASS_SECS);
        const vars = await beeb.read(S.vars, 1100);
        const extra = {};
        for (const [lo, hi] of extras) {
            const bytes = await beeb.read(where(lo), hi - lo + 1);
            bytes.forEach((v, i) => (extra[lo + i] = v));
        }
        log.passes.push({ pass: n, frame: r.registers.frame_count - f0, vars, extra });
        await hold(keysAt(sc, n));
    }
    log.stopped = "done";
} catch (e) {
    if (!(e instanceof Stop)) throw e;
    log.stopped = e.message;
    status = 1;
} finally {
    save();
    await beeb.close();
}
console.log(`beepass ${sc.name}: ${log.passes.length} passes, ${log.stopped}`);
process.exit(status);
