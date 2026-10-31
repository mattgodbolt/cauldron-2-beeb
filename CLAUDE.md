# CAULDRON II (BBC Micro port): notes for Claude Code

A port of Palace Software's *Cauldron II: The Pumpkin Strikes Back* (ZX
Spectrum 48K, 1986) to the BBC Micro. `BRIEF.md` is where it started;
`docs/how-it-works.md` holds the transcription's conventions (zNNNNN,
aNNNNN, the registers in zero page, `zx_read`), `docs/research/*.md` the
original, `docs/decisions.md` every deviation, `docs/journal.md` the
story.

## Commands

```sh
make venv / make fetch / make zx   # tools, the original, build/c2.z80
make            # build/cauldron2.ssd (+ .json symbols, listing.txt)
make run        # boot in jsbeeb, shots/run.png
make check      # every check (MODEL=Master for a Master 128)
make disc       # from a clean tree: cauldron2.ssd at the root
make disasm     # build/c2.skool from disasm/*.ctl
```

- `.venv/bin/python tools/zx.py '<script>' shots/zx_` runs the original;
  `node tools/play.mjs '<script>' shots/p_` the port (same script
  language; their docstrings). A game starts on the original with
  `2,1:tap,1,4:tap,4,KF:0.3`.
- `.venv/bin/python tools/zxrooms.py` has the original draw every room
  (`build/zxrooms/`): the drawing's oracle.
- The build lists the original's routines not yet transcribed (stubs that
  stop at `unwritten`).

- `make passes` plays the original and the port side by side
  (`tests/scenarios.txt`) and compares 24000-25099 every main-loop pass;
  `python3 tools/fuzz.py --count N --seed S` does it with random keys
  (a failing line goes into the scenarios). `node tools/sample.mjs` is a
  sampling profiler of play.
- `make SOFT=1`: stubs return instead of stopping, to try what's written.

## Gotchas met

- **Main RAM is full** (decision 16). The build's `PRINT`s say what's
  left, and the viewer build (`make rooms`) is tighter than the release.
  A test-only build that adds code can overflow: test the release disc
  where you can (as `make front` does).
- C2's code is packed (baron's `zx02` transform) because it loads at
  `&1900`, below the title in the screen. The loader runs first in the
  file, moves the packed bytes up and unpacks from page 4.
- A palette program built by `make_program` isn't shown until
  `set_palette` takes it (the room does it at 54499).
- The panel's pixels take their colours from the rows' palettes when
  they're drawn: set the colours (`plain_colours`) before drawing text.
- jsbeeb's key names: `K4` not `4`, `SLASH`, `COLON_STAR`.
- Agents in worktrees: merging two that each transcribed the same
  routine fails with a duplicate symbol; append-only docs (decisions,
  journal) conflict and get renumbered on merge.

## The rules (from kieranhj/beeb-port-kit)

1. **The original is the specification.** Transcribe its routines,
   tables and constants. When the BBC forces a change, port the
   original's *decision*, not just its effect.
2. **Deviations are numbered decisions** in `docs/decisions.md`. Matt
   makes the design calls: lay out the options with figures. A call made
   while Matt is away is marked provisional there, for review.
3. **One layer at a time**, working and visible in the emulator before
   the next one starts: screen, data, drawing, player, monsters,
   objects, sound, front end, loader.
4. **Measure, don't recall.** Run it, read the bytes, read memory back.
   Verify against the buffer, not the screenshot.

## House rules

- Commit messages end at `Co-Authored-By:`; never a claude.ai session
  link or a `Claude-Session:` trailer. Never force-push a pushed branch;
  fix with additive commits.
- Comments and docs carry no figure the build computes or one run
  measured (addresses, sizes, free bytes). Name the symbol, `ASSERT` the
  property, or cite the dated decision. The original's addresses and the
  hardware's are fine.
- Never label a statement "honest" or "candid". Size work by what it
  touches, never by time. Matt is they/them.
- Every agent brief carries these rules.
- The original's files (`original/`, `prior/`) are never committed.
