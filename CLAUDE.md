# CAULDRON II (BBC Micro port): notes for Claude Code

A port of Palace Software's *Cauldron II: The Pumpkin Strikes Back* (ZX
Spectrum 48K, 1986) to the BBC Micro. Nothing is built yet: start with
`BRIEF.md`, which says what's known, what to read
(`../porting-to-the-beeb.md` first) and what to ask Matt.

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
