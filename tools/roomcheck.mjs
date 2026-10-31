#!/usr/bin/env node
// Draw every room in the BBC viewer (-D VIEWER=1: room.6502's viewer,
// 53949's drawing) and dump what it drew, for tools/roomcmp.py to compare
// with the original's own drawing (tools/zxrooms.py).
//
//   node tools/roomcheck.mjs [--disc build/viewer.ssd] [rooms]
//
// Writes build/bbcrooms/room_NN.bin: the 12K screen, then the 768 bytes
// of attributes (attrs).
import { mkdirSync, writeFileSync } from "fs";
import { startBeeb } from "./beeb.mjs";

const args = process.argv.slice(2);
const i = args.indexOf("--disc");
const disc = i >= 0 ? args.splice(i, 2)[1] : "build/viewer.ssd";
const rooms = [];
for (const part of (args[0] ?? "0-127").split(",")) {
    const [lo, hi] = part.split("-").map(Number);
    for (let r = lo; r <= (hi ?? lo); r++) rooms.push(r);
}
mkdirSync("build/bbcrooms", { recursive: true });
const b = await startBeeb({ disc, bootUntil: "shown", symbols: disc.replace(/\.ssd$/, ".json") });
let bad = 0;
try {
    await b.tap("SPACE");
    await b.runUntil("viewer_wait", 10);
    for (const n of rooms) {
        await b.write("view_num", [n]);
        // Run until the viewer is back in its wait loop with this drawn.
        const r = await b.runUntil("viewer_wait", 10);
        const shown = await b.peek("view_shown");
        const stub = await b.peekw("unwritten_at");
        if (shown !== n || r.stopped_reason !== "breakpoint" || stub) {
            console.log(`room ${n} never shown (${r.stopped_reason}, stub ${stub})`);
            bad++;
            continue;
        }
        const scr = await b.read(0x5000, 0x3000);
        const attrs = await b.read("attrs", 768);
        writeFileSync(`build/bbcrooms/room_${String(n).padStart(2, "0")}.bin`, Buffer.from([...scr, ...attrs]));
    }
} finally {
    await b.close();
}
console.log(`roomcheck: ${rooms.length - bad} rooms dumped to build/bbcrooms`);
if (bad) process.exitCode = 1;
