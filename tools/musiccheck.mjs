#!/usr/bin/env node
// The music and the pulses (src/sound.6502, decisions 12, 13 and 18)
// against the original's, from the bytes the 6502 writes to the SN76489.
//
// build/musiccheck.ssd (MUSICCHECK) has vsync_hook step a tune as the
// original's interrupt (57664) does; tools/musicmodel.py says, from
// tools/zxmusic.py's decode of the original, which notes each channel
// plays and when. For each tune, from its start on a frame:
//
// - every note on SN channels 0 and 1, in order: its start (the ticks 3
//   frames apart, 2 when both channels rest), its period, and its length:
//   a tone sounds at its period from its strike until its stream changes,
//   held across the ticks; a bass note's volume switches at each
//   half-cycle (their spacing in microseconds against the original's)
//   until it ends;
// - between a channel's notes (its rests), the channel silent;
// - with the stepping stopped (24002 = 0), the music silent within two
//   frames and its interrupt off IRQ1V;
// - the main program (main.6502's `shown`, polling the keyboard
//   throughout) never sees a key: the chip's writes put the System VIA
//   back as key_down had it.
//
// Then a pulse of a few effects from the interrupt, as 57714 plays one:
// channel 2's volume on for the original's width (4 * v T-states).
//
//   node tools/musiccheck.mjs
//
// Exits non-zero on a difference.
import { execFileSync } from "child_process";
import { startBeeb } from "./beeb.mjs";

const PYTHON = process.env.PYTHON || ".venv/bin/python";
const model = JSON.parse(execFileSync(PYTHON, ["tools/musicmodel.py"]).toString());

const CYCLES_US = 2;                    // jsbeeb's cycles: 2MHz
const FRAME = 312 * 64 * CYCLES_US;     // our CRTC's frame (screen.6502)
const FRAME_TOL = 0.1;                  // a note's start and end, in frames
// A bass note's half-cycles, as a fraction of the original's: their
// median (4 cents; with both channels bass, each waits on the other's
// edges); their mean (10 cents). And the furthest out, in microseconds:
// a held note's edge due while VSync's interrupt runs (the tune's step
// among it) waits for it, and the next is timed from when it was due.
const HALF_MEDIAN = 0.0025;
const HALF_MEAN = 0.006;
const HALF_WORST_US = 400;
const PULSE_TOL = 0.03;                 // a pulse's width, as a fraction

let failed = false;
const fail = (msg) => { console.log(`DIFFERS: ${msg}`); failed = true; };

// The log's writes as [cycle, byte].
const writes = (text) => [...text.matchAll(/^(\d+): 0x([0-9a-f]{2}) /gm)].map((m) => [Number(m[1]), parseInt(m[2], 16)]);

// Each tone channel's state from the chip's bytes: a change point
// {t, period, on} whenever its period or whether it sounds changes (a
// volume between two audible levels, the envelope, is no change); and
// levels: each audible volume written, {t, att}.
function chipStates(log) {
    const period = [0, 0, 0], on = [false, false, false];
    let latch = 0;
    const out = [[], [], []], levels = [[], [], []];
    for (const [t, v] of log) {
        let ch, isVol;
        if (v & 0x80) {
            latch = v;
            ch = (v >> 5) & 3; isVol = (v >> 4) & 1;
            if (ch > 2) continue;
            if (!isVol) {
                // (sound.6502 always sends the high bits next: the period
                // changes then.)
                period[ch] = (period[ch] & 0x3f0) | (v & 15);
                continue;
            }
        } else {
            ch = (latch >> 5) & 3; isVol = (latch >> 4) & 1;
            if (ch > 2) continue;
            if (!isVol) period[ch] = (period[ch] & 15) | ((v & 0x3f) << 4);
        }
        if (isVol) {
            on[ch] = (v & 15) !== 15;
            if (on[ch]) levels[ch].push({ t, att: v & 15 });
        }
        const states = out[ch], last = states[states.length - 1];
        if (!last || last.period !== period[ch] || last.on !== on[ch]) states.push({ t, period: period[ch], on: on[ch] });
    }
    out.levels = levels;
    return out;
}

const b = await startBeeb({ disc: "build/musiccheck.ssd", symbols: "build/musiccheck.json", bootUntil: "shown" });
try {
    const hook = b.addr("mc_hook");
    const irq = b.addr("irq_handler");
    const LOUD = b.addr("SN_LOUD"), SUSTAIN = b.addr("MUS_SUSTAIN");
    await b.write("vsync_hook", [hook & 255, hook >> 8]);
    const capture = async (frames, before) => {
        await b.call("start_sound_capture", { session_id: b.session_id });
        await before();
        await b.frames(frames);
        const text = (await b.call("stop_sound_capture", { session_id: b.session_id, max_entries: 1e7 })).content[0].text;
        return writes(text);
    };

    for (const tune of model.tunes) {
        const log = await capture(tune.frames, () => b.write("mc_req", [tune.req]));
        // Stop stepping: within two frames the music must stop by itself.
        const tail = await capture(3, () => b.write("mc_req", [0xff]));
        const got = chipStates(log);
        // The tune's first strike is the model's first note's frame.
        let first = Infinity, firstModel = Infinity;
        for (const c of [0, 1]) {
            const strike = got[c].find((s) => s.on);
            if (strike) first = Math.min(first, strike.t);
            if (tune.channels[c].length) firstModel = Math.min(firstModel, tune.channels[c][0].frame);
        }
        const frameOf = (t) => (t - first) / FRAME + firstModel;
        let bad = 0, compared = 0, bassNotes = 0, worstHalf = 0, held = 0;
        const report = (msg) => { if (++bad <= 8) fail(`tune ${tune.tune}: ${msg}`); };
        // (Only notes that end, and rests that start, before the steps stop.)
        const last = tune.frames - 4;
        for (const c of [0, 1]) {
            const states = got[c];
            const want = tune.channels[c].filter((w) => w.frame + w.frames <= last);
            let k = 0;                  // the state the search starts from
            let prevEnd = -Infinity;
            for (let i = 0; i < want.length; i++) {
                const w = want[i];
                const where = `channel ${c + 1} note ${i} (frame ${w.frame}, ${w.frames} frames)`;
                const end = w.frame + w.frames;
                // Its strike: the last change to sounding at its period while
                // it's due (after the last note's edges, and its stopping).
                const from = k;
                while (k < states.length && frameOf(states[k].t) < w.frame - FRAME_TOL) k++;
                for (let j = k; j < states.length && frameOf(states[j].t) <= w.frame + FRAME_TOL; j++)
                    if (states[j].on && states[j].period === w.period) k = j;
                // The rest before it: nothing sounds after the last note's end.
                for (let j = from; j < k; j++) {
                    const f = frameOf(states[j].t);
                    if (states[j].on && f > prevEnd + FRAME_TOL) {
                        report(`channel ${c + 1}: sounds at frame ${f.toFixed(2)}, in a rest before note ${i}`);
                        break;
                    }
                }
                prevEnd = end;
                const s = states[k];
                if (!s || !s.on || s.period !== w.period || Math.abs(frameOf(s.t) - w.frame) > FRAME_TOL) {
                    report(`${where}: ` + (s ? `the chip at frame ${frameOf(s.t).toFixed(2)} ${s.on ? "plays period " + s.period : "silent"}`
                                             : "never struck") + `, the model period ${w.period}`);
                    continue;
                }
                compared++;
                if (w.frames > 3) held++;
                // Struck once, at SN_LOUD, then settling a step a frame to
                // MUS_SUSTAIN: never louder again while it holds.
                const lv = got.levels[c].filter((l) => l.t >= s.t && frameOf(l.t) < end - FRAME_TOL).map((l) => l.att);
                const settled = Math.min(SUSTAIN, Math.floor(w.frames - FRAME_TOL));
                if (lv[0] !== LOUD || lv.some((a, n) => n && a < lv[n - 1]) || lv[lv.length - 1] > settled ||
                    (!w.half && lv[lv.length - 1] !== settled))
                    report(`${where}: its volumes ${lv.slice(0, 12).join(" ")}`);
                if (!w.half) {
                    // Held at its period until its end.
                    let j = k + 1;
                    while (j < states.length && states[j].on && states[j].period === w.period) j++;
                    const stop = j < states.length ? frameOf(states[j].t) : Infinity;
                    if (Math.abs(stop - end) > FRAME_TOL)
                        report(`${where}: sounds ${(stop - w.frame).toFixed(2)} frames`);
                    k = j;
                } else {
                    // The bass: its switches until the note ends.
                    bassNotes++;
                    let j = k + 1;
                    const switches = [s.t];
                    while (j < states.length && states[j].period === 1 && frameOf(states[j].t) < end - FRAME_TOL)
                        switches.push(states[j++].t);
                    const gaps = switches.slice(1).map((t, n) => (t - switches[n]) / CYCLES_US);
                    if (!gaps.length) { report(`${where}: no half-cycles`); k = j; continue; }
                    const median = [...gaps].sort((x, y) => x - y)[gaps.length >> 1];
                    const mean = (switches[switches.length - 1] - s.t) / CYCLES_US / gaps.length;
                    const worst = Math.max(...gaps.map((g) => Math.abs(g - w.half)));
                    worstHalf = Math.max(worstHalf, worst);
                    if (Math.abs(median / w.half - 1) > HALF_MEDIAN || Math.abs(mean / w.half - 1) > HALF_MEAN)
                        report(`${where}: half-cycles ${median.toFixed(1)}us (median), ${mean.toFixed(1)}us on average, ` +
                               `the original's ${w.half}us`);
                    if (worst > HALF_WORST_US) report(`${where}: a half-cycle ${worst.toFixed(0)}us out`);
                    if (process.env.DEBUG && worst > HALF_WORST_US)
                        console.log(states.slice(k - 3, j + 2).map((x) => `${frameOf(x.t).toFixed(3)} ${x.period} ${x.on}`).join("\n"));
                    // It went on to the end: its last switch within a
                    // half-cycle of it, and then silent or the next note.
                    const tailUs = (end - frameOf(switches[switches.length - 1])) * FRAME / CYCLES_US;
                    if (tailUs > w.half + HALF_WORST_US + FRAME_TOL * FRAME / CYCLES_US)
                        report(`${where}: stops ${(tailUs / 1000).toFixed(1)}ms early`);
                    const next = states[j];
                    if (next && next.on && frameOf(next.t) < end + FRAME_TOL &&
                        !(i + 1 < want.length && Math.abs(want[i + 1].frame - end) <= FRAME_TOL))
                        report(`${where}: sounds on past its end`);
                    k = j;
                }
            }
            // After the last note, silence until the steps stop (or a note
            // that doesn't end before then).
            const after = tune.channels[c].find((w) => w.frame + w.frames > last);
            const until = after ? after.frame - FRAME_TOL : last;
            for (let j = k; j < states.length && frameOf(states[j].t) < until; j++) {
                if (states[j].on && frameOf(states[j].t) > prevEnd + FRAME_TOL) {
                    report(`channel ${c + 1}: sounds at frame ${frameOf(states[j].t).toFixed(2)}, after its last note`);
                    break;
                }
            }
            if (want.length < 2) report(`channel ${c + 1}: only ${want.length} notes compared`);
        }
        const stopped = chipStates(tail);
        const vol = [15, 15];
        for (const [, v] of [...log, ...tail]) {
            if ((v & 0x90) === 0x90 && ((v >> 5) & 3) < 2) vol[(v >> 5) & 3] = v & 15;
        }
        if (vol[0] !== 15 || vol[1] !== 15) fail(`tune ${tune.tune}: still sounding after the steps stopped`);
        // (The tail may start with the held notes stopping, but no strike.)
        if (stopped[0].some((s) => s.on && s.period !== 1) || stopped[1].some((s) => s.on && s.period !== 1))
            fail(`tune ${tune.tune}: a note struck after the steps stopped`);
        if ((await b.peekw("irq1v")) !== irq || (await b.peek("mus_installed")) !== 0)
            fail(`tune ${tune.tune}: mus_irq still on IRQ1V after the steps stopped`);
        if (!bad)
            console.log(`tune ${tune.tune}: ${tune.frames} frames, ${compared} notes as the original's, ` +
                        `${held} held over ticks` +
                        (bassNotes ? ` (${bassNotes} bass, every half-cycle within ${worstHalf.toFixed(0)}us)` : "") +
                        "; silent in the rests, and off IRQ1V once the steps stopped");
    }

    for (const p of model.pulses) {
        const log = await capture(3, () => b.write("mc_req", [0x80 + p.effect]));
        const ch2 = log.filter(([, v]) => (v & 0xf0) === 0xd0);
        if (ch2.length !== 2 || (ch2[0][1] & 15) === 15 || (ch2[1][1] & 15) !== 15) {
            fail(`effect ${p.effect}: channel 2 got ${ch2.map(([, v]) => v.toString(16))}, not one pulse`);
            continue;
        }
        const us = (ch2[1][0] - ch2[0][0]) / CYCLES_US;
        const ok = Math.abs(us / p.us - 1) <= PULSE_TOL;
        if (!ok) fail(`effect ${p.effect}: a pulse of ${us.toFixed(0)}us, the original's ${p.us.toFixed(0)}us`);
        else console.log(`effect ${p.effect}: a pulse of ${us.toFixed(0)}us, the original's ${p.us.toFixed(0)}us`);
    }

    if (await b.peekw("unwritten_at")) fail("the main program left `shown`: it saw a key");
    else console.log("the main program polled the keyboard throughout and saw no key");
} finally {
    await b.close();
}
process.exit(failed ? 1 : 0);
