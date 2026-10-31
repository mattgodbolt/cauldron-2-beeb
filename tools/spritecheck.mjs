#!/usr/bin/env node
// Run tools/spritecases.py's cases on the BBC viewer: each case's room
// drawn, its calls poked into test_calls and made (room.6502's tests),
// the screen and attributes dumped (build/sprite/bbc_NNN.bin) for
// `spritecases.py cmp`.
//
//   node tools/spritecheck.mjs [--disc build/viewer.ssd]
import { readFileSync, writeFileSync } from "fs";
import { startBeeb } from "./beeb.mjs";

const args = process.argv.slice(2);
const i = args.indexOf("--disc");
const disc = i >= 0 ? args[i + 1] : "build/viewer.ssd";
const cases = JSON.parse(readFileSync("build/sprite/cases.json", "utf8"));
const b = await startBeeb({ disc, bootUntil: "shown", symbols: disc.replace(/\.ssd$/, ".json") });
let bad = 0;
try {
    await b.tap("SPACE");
    await b.runUntil("viewer_wait", 10);
    for (const [n, c] of cases.entries()) {
        // Redraw the room even when it's the one shown.
        await b.write("view_shown", [0xff]);
        await b.write("view_num", [c.room]);
        await b.runUntil("viewer_wait", 10);
        await b.write("test_calls", c.calls.flat());
        await b.write("test_n", [c.calls.length]);
        const r = await b.runUntil("test_done", 10);
        if (r.stopped_reason !== "breakpoint" || (await b.peekw("unwritten_at"))) {
            console.log("case", n, "never finished");
            bad++;
        }
        const scr = await b.read(0x5000, 0x3000);
        const attrs = await b.read("attrs", 768);
        // The pre-shift's bytes, 24223-24899 (spritecases.py's BUF_END).
        const buf = await b.read(b.addr("vars") + 223, 24900 - 24223);
        writeFileSync(`build/sprite/bbc_${String(n).padStart(3, "0")}.bin`, Buffer.from([...scr, ...attrs, ...buf]));
        await b.runUntil("viewer_wait", 10);
    }
} finally {
    await b.close();
}
if (bad) process.exitCode = 1;
