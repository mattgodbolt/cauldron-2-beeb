#!/usr/bin/env node
// The music and the pulses (src/sound.6502, decisions 12 and 13) against
// the original's, from the bytes the 6502 writes to the SN76489.
//
// build/musiccheck.ssd (MUSICCHECK) has vsync_hook step a tune as the
// original's interrupt (57664) does; tools/musicmodel.py says, from
// tools/zxmusic.py's decode of the original, which notes each channel
// strikes and when. For each tune, from its start on a frame:
//
// - every note on SN channels 0 and 1, in order: its frame (the ticks 3
//   frames apart, 2 when both channels rest), its period, its two frames
//   sounding; a bass note's half-cycles (their number, and their spacing
//   in microseconds against the original's);
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
const GAP = 12000 * CYCLES_US;          // a silence longer than any half-cycle: a new note
const FRAME_TOL = 0.1;                  // frames
// A bass note's half-cycles, as a fraction of the original's: their
// median (4 cents; with both channels bass, each waits on the other's
// edges); their mean (10 cents: an edge waits while VSync's interrupt
// runs, and the note's last can't be made up). And the furthest out, in
// microseconds.
const HALF_MEDIAN = 0.0025;
const HALF_MEAN = 0.006;
const HALF_WORST_US = 250;
const PULSE_TOL = 0.03;                 // a pulse's width, as a fraction

let failed = false;
const fail = (msg) => { console.log(`DIFFERS: ${msg}`); failed = true; };

// The log's writes as [cycle, byte].
const writes = (text) => [...text.matchAll(/^(\d+): 0x([0-9a-f]{2}) /gm)].map((m) => [Number(m[1]), parseInt(m[2], 16)]);

// Each channel's notes from the chip's bytes: a note starts when the
// volume comes on after a gap, and holds every switch of it until the
// next gap. period: the channel's at the note's start.
function chipNotes(log) {
    const period = [0, 0, 0], vol = [15, 15, 15, 15];
    let latch = 0;
    const out = [[], [], []];
    const lastOff = [-Infinity, -Infinity, -Infinity];
    for (const [t, v] of log) {
        let ch, isVol, data;
        if (v & 0x80) {
            latch = v;
            ch = (v >> 5) & 3; isVol = (v >> 4) & 1; data = v & 15;
            if (!isVol && ch < 3) { period[ch] = (period[ch] & 0x3f0) | data; continue; }
        } else {
            ch = (latch >> 5) & 3; isVol = (latch >> 4) & 1;
            if (!isVol && ch < 3) { period[ch] = (period[ch] & 15) | ((v & 0x3f) << 4); continue; }
            data = v & 15;
        }
        if (!isVol || ch > 2) continue;
        const was = vol[ch];
        vol[ch] = data;
        if ((was === 15) === (data === 15)) continue;           // no switch
        const notes = out[ch];
        if (data !== 15) {
            if (t - lastOff[ch] > GAP || !notes.length) notes.push({ start: t, period: period[ch], switches: [t] });
            else notes[notes.length - 1].switches.push(t);
        } else {
            lastOff[ch] = t;
            if (notes.length) notes[notes.length - 1].switches.push(t);
        }
    }
    return out;
}

const b = await startBeeb({ disc: "build/musiccheck.ssd", symbols: "build/musiccheck.json", bootUntil: "shown" });
try {
    const hook = b.addr("mc_hook");
    const irq = b.addr("irq_handler");
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
        const got = chipNotes(log);
        let first = Infinity, firstModel = Infinity;
        for (const c of [0, 1]) {
            if (got[c].length) first = Math.min(first, got[c][0].start);
            if (tune.channels[c].length) firstModel = Math.min(firstModel, tune.channels[c][0].frame);
        }
        let bad = 0, compared = 0, bassNotes = 0, worstHalf = 0;
        const report = (msg) => { if (++bad <= 8) fail(`tune ${tune.tune}: ${msg}`); };
        // (Only notes that end before the steps stop.)
        const last = tune.frames - 4;
        for (const c of [0, 1]) {
            const want = tune.channels[c].filter((w) => w.frame <= last);
            const have = got[c].filter((h) => (h.start - first) / FRAME + firstModel <= last + 0.5);
            if (have.length !== want.length)
                report(`channel ${c + 1}: ${have.length} notes, the model ${want.length}`);
            for (let i = 0; i < Math.min(have.length, want.length); i++) {
                const h = have[i], w = want[i];
                compared++;
                const frame = (h.start - first) / FRAME + firstModel;
                const where = `channel ${c + 1} note ${i} (frame ${w.frame})`;
                if (Math.abs(frame - w.frame) > FRAME_TOL) { report(`${where} at frame ${frame.toFixed(2)}`); continue; }
                if (h.period !== w.period) report(`${where}: period ${h.period}, the model ${w.period}`);
                const edges = h.switches.length - 1;
                if (edges !== w.edges) report(`${where}: ${edges} switches after the strike, the model ${w.edges}`);
                if (!w.half) {
                    const len = (h.switches[h.switches.length - 1] - h.start) / FRAME;
                    if (Math.abs(len - 2) > FRAME_TOL) report(`${where}: sounds ${len.toFixed(2)} frames, not 2`);
                } else {
                    bassNotes++;
                    const gaps = h.switches.slice(1).map((t, k) => (t - h.switches[k]) / CYCLES_US);
                    const median = [...gaps].sort((x, y) => x - y)[gaps.length >> 1];
                    const mean = (h.switches[h.switches.length - 1] - h.start) / CYCLES_US / gaps.length;
                    const worst = Math.max(...gaps.map((g) => Math.abs(g - w.half)));
                    worstHalf = Math.max(worstHalf, worst);
                    if (Math.abs(median / w.half - 1) > HALF_MEDIAN || Math.abs(mean / w.half - 1) > HALF_MEAN)
                        report(`${where}: half-cycles ${median.toFixed(1)}us (median), ${mean.toFixed(1)}us on average, ` +
                               `the original's ${w.half}us`);
                    if (worst > HALF_WORST_US) report(`${where}: a half-cycle ${worst.toFixed(0)}us out`);
                }
            }
        }
        const stopped = chipNotes(tail);
        const vol = [15, 15];
        for (const [, v] of [...log, ...tail]) {
            if ((v & 0x90) === 0x90 && ((v >> 5) & 3) < 2) vol[(v >> 5) & 3] = v & 15;
        }
        if (vol[0] !== 15 || vol[1] !== 15) fail(`tune ${tune.tune}: still sounding after the steps stopped`);
        if (stopped[0].length + stopped[1].length) fail(`tune ${tune.tune}: a note struck after the steps stopped`);
        if ((await b.peekw("irq1v")) !== irq || (await b.peek("mus_installed")) !== 0)
            fail(`tune ${tune.tune}: mus_irq still on IRQ1V after the steps stopped`);
        if (!bad)
            console.log(`tune ${tune.tune}: ${tune.frames} frames, ${compared} notes as the original's` +
                        (bassNotes ? ` (${bassNotes} bass, every half-cycle within ${worstHalf.toFixed(0)}us)` : "") +
                        "; silent and off IRQ1V once the steps stopped");
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
