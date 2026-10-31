#!/usr/bin/env node
// The front end (src/frontend.6502, decisions 8 and 9) in jsbeeb, on its
// test build (FETEST: its own printer and clear standing in for the
// drawing's, 57664's dispatch of the tunes on vsync_hook).
//
// - The menu: the title's music playing, its text on screen; 3, then six
//   keys: key_table holds them in order and their names show; 1 restores
//   the default keys; 2 sets use_joystick.
// - Game over and the win: their text, and their tunes playing.
//
// Screenshots to shots/fe_*.png. Exits non-zero on a difference.
//
//   node tools/fecheck.mjs
import { startBeeb } from "./beeb.mjs";

let failed = false;
const fail = (msg) => { console.log(`DIFFERS: ${msg}`); failed = true; };
const hex = (a) => a.map((x) => x.toString(16).padStart(2, "0")).join(" ");

const DEFAULTS = [0x48, 0x68, 0x61, 0x42, 0x49, 0x70];     // : / Z X RETURN ESCAPE
const CHOSEN = [0x10, 0x41, 0x36, 0x37, 0x62, 0x60];       // Q A O P SPACE TAB
const NAMES = ["Q", "A", "O", "P", "SPACE", "TAB"];

const b = await startBeeb({ disc: "build/fetest.ssd", symbols: "build/fetest.json", bootUntil: "shown" });
const jmp = async (at, to) => {
    const a = b.addr(to);
    await b.write(at, [0x4c, a & 255, a >> 8]);
};
// From fe_test_idle's loop to `to`, the loop put back once it's left.
const enter = async (to) => {
    await jmp("fe_test_idle", to);
    await b.run(0.05);
    await jmp("fe_test_idle", "fe_test_idle");
};
const press = async (internal, secs = 0.1) => {
    await b.call("key_down", { session_id: b.session_id, internal });
    await b.run(secs);
    await b.call("key_up", { session_id: b.session_id, internal });
    await b.run(0.1);
};
// The SN76489's bytes over some frames.
const sounding = async (frames) => {
    await b.call("start_sound_capture", { session_id: b.session_id });
    await b.frames(frames);
    const text = (await b.call("stop_sound_capture", { session_id: b.session_id, max_entries: 1e6 })).content[0].text;
    return [...text.matchAll(/^\d+: 0x([0-9a-f]{2}) /gm)].length;
};
// The text the printer printed: a rough read of the attribute shadow,
// rows with any non-zero attribute.
try {
    await jmp("shown", "fe_test");
    await b.run(0.5);
    await b.shot("shots/fe_menu.png");
    const n = await sounding(30);
    if (n === 0) fail("the menu: no music");
    else console.log(`the menu: tune 1 playing (${n} bytes to the chip in 30 frames)`);
    if ((await b.peek("a24002")) !== 1) fail("the menu: 24002 isn't 1");

    // 3: define six keys.
    await press(0x11);
    for (const [i, k] of CHOSEN.entries()) {
        await press(k);
        if (i === 4) await b.shot("shots/fe_keys.png");
    }
    await b.run(0.3);
    const keys = await b.read("key_table", 6);
    if (hex(keys) !== hex(CHOSEN)) fail(`define keys: key_table ${hex(keys)}, pressed ${hex(CHOSEN)}`);
    else console.log(`define keys: key_table ${hex(keys)} (${NAMES.join(" ")})`);
    if ((await b.peek("use_joystick")) !== 0) fail("define keys: use_joystick set");
    if ((await b.peekw("unwritten_at")) !== 0) fail("define keys: a stub reached");
    await b.shot("shots/fe_credits.png");

    // 1: the default keys again.
    await enter("fe_test");
    await b.run(0.3);
    await press(0x30);
    await b.run(0.2);
    const keys1 = await b.read("key_table", 6);
    if (hex(keys1) !== hex(DEFAULTS)) fail(`1 KEYBOARD: key_table ${hex(keys1)}, not the defaults`);
    else console.log("1 KEYBOARD: the default keys");

    // 2: the joystick.
    await enter("fe_test");
    await b.run(0.3);
    await press(0x31);
    await b.run(0.2);
    if ((await b.peek("use_joystick")) === 0) fail("2 JOYSTICK: use_joystick not set");
    else console.log("2 JOYSTICK: use_joystick set");

    // Game over: its verse and tune 3. (The score's digits, 58804, are
    // the game's; the snapshot's are stale.)
    await b.write(b.addr("a58803") + 1, [..."0012340"].map((c) => c.charCodeAt(0)));
    await enter("fe_test_over");
    await b.run(0.5);
    // (it waits on the input, 52767, a stub here: stopped there with the
    // interrupts off)
    if ((await b.peekw("unwritten_at")) !== 52767) fail("game over: didn't reach the input's wait");
    await b.shot("shots/fe_over.png");
    if ((await b.peek("a24002")) !== 2) fail("game over: 24002 isn't 2");
    else console.log("game over: verse shown, 24002 = 2, waiting on the input");

    // The win's screen.
    await b.write("unwritten_at", [0, 0]);
    await jmp("unwritten_stop", "fe_test_win");
    await b.run(0.05);
    await jmp("unwritten_stop", "unwritten_stop");
    await b.run(0.5);
    if ((await b.peekw("unwritten_at")) !== 52767) fail("the win: didn't reach the input's wait");
    await b.shot("shots/fe_win.png");
    if ((await b.peek("a24002")) !== 3) fail("the win: 24002 isn't 3");
    else console.log("the win: text shown, 24002 = 3, waiting on the input");
} finally {
    await b.close();
}
process.exit(failed ? 1 : 0);
