#!/usr/bin/env node
// The front end (src/frontend.6502, decisions 14 and 15) in jsbeeb, on the
// release disc, driven with keys as a player would:
//
// - The menu: the title's music playing (24002 = 1). 3, then six keys:
//   `keys` holds them in order and the keys' reader is at 57726. The new
//   abort key goes back to the menu; 1 restores the default keys; abort
//   again; 2 puts the joystick's reader at 57726.
// - Game over and the win: their screens (entered from the credits' loop,
//   52290, patched to jump there), their tunes (24002 = 2, 3).
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

const b = await startBeeb({ disc: "build/cauldron2.ssd", symbols: "build/cauldron2.json", bootUntil: "shown" });
const press = async (internal, secs = 0.1) => {
    await b.call("key_down", { session_id: b.session_id, internal });
    await b.run(secs);
    await b.call("key_up", { session_id: b.session_id, internal });
    await b.run(0.2);
};
const reader = async () => b.peekw("a57726");
// The SN76489's bytes over some frames.
const sounding = async (frames) => {
    await b.call("start_sound_capture", { session_id: b.session_id });
    await b.frames(frames);
    const text = (await b.call("stop_sound_capture", { session_id: b.session_id, max_entries: 1e6 })).content[0].text;
    return [...text.matchAll(/^\d+: 0x([0-9a-f]{2}) /gm)].length;
};
const jmp = async (at, to) => {
    const a = b.addr(to);
    await b.write(at, [0x4c, a & 255, a >> 8]);
};
try {
    await b.tap("SPACE");
    await b.runUntil("z52481", 10);
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
    const keys = await b.read("keys", 6);
    if (hex(keys) !== hex(CHOSEN)) fail(`define keys: keys ${hex(keys)}, pressed ${hex(CHOSEN)}`);
    else console.log(`define keys: keys ${hex(keys)} (${NAMES.join(" ")})`);
    if ((await reader()) !== b.addr("z52695")) fail("define keys: 57726 isn't the keys' reader");
    await b.runUntil("z52290", 10);
    await b.shot("shots/fe_credits.png");

    // The new abort key (TAB) to the menu; 1: the default keys again.
    await b.call("key_down", { session_id: b.session_id, internal: CHOSEN[5] });
    await b.runUntil("z52481", 10);
    await b.call("key_up", { session_id: b.session_id, internal: CHOSEN[5] });
    await b.run(0.3);
    await press(0x30);
    const keys1 = await b.read("keys", 6);
    if (hex(keys1) !== hex(DEFAULTS)) fail(`1 KEYBOARD: keys ${hex(keys1)}, not the defaults`);
    else console.log("1 KEYBOARD: the default keys");
    if ((await reader()) !== b.addr("z52695")) fail("1 KEYBOARD: 57726 isn't the keys' reader");

    // ESCAPE to the menu; 2: the joystick.
    await b.runUntil("z52290", 10);
    await b.call("key_down", { session_id: b.session_id, internal: DEFAULTS[5] });
    await b.runUntil("z52481", 10);
    await b.call("key_up", { session_id: b.session_id, internal: DEFAULTS[5] });
    await b.run(0.3);
    await press(0x31);
    if ((await reader()) !== b.addr("z52658")) fail("2 JOYSTICK: 57726 isn't the joystick's reader");
    else console.log("2 JOYSTICK: the joystick's reader");

    // Game over: its verse and tune 3, from the credits' loop.
    await b.runUntil("z52290", 10);
    await b.write(b.addr("a58803") + 1, [..."0012340"].map((c) => c.charCodeAt(0)));
    await jmp("z52290", "z53101");
    await b.run(1);
    await b.shot("shots/fe_over.png");
    if ((await b.peek("a24002")) !== 2) fail("game over: 24002 isn't 2");
    else console.log("game over: verse shown, 24002 = 2");

    // The win's screen, likewise.
    await jmp("z52290", "fe_win_screen");
    await b.call("key_down", { session_id: b.session_id, internal: DEFAULTS[5] });   // (the abort: back to 52235)
    await b.runUntil("z52481", 10);
    await b.call("key_up", { session_id: b.session_id, internal: DEFAULTS[5] });
    await b.run(0.3);
    await press(0x12);                                      // 4: on to the credits, patched
    await b.run(1);
    await b.shot("shots/fe_win.png");
    if ((await b.peek("a24002")) !== 3) fail("the win: 24002 isn't 3");
    else console.log("the win: text shown, 24002 = 3");
} finally {
    await b.close();
}
process.exit(failed ? 1 : 0);
