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

As the port takes shape, this file gathers the gotchas met, as
`../cauldron-beeb/CLAUDE.md` does.

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
