# Cauldron II on the BBC Micro: the brief

A port of Palace Software's *Cauldron II: The Pumpkin Strikes Back* (ZX
Spectrum 48K, 1986) to the BBC Micro, in 6502 assembly built with
[baron](https://github.com/waitingforvsync/baron), tested headless in
jsbeeb against the original running on SkoolKit's Z80 simulator.

This file is where a new session starts. Read it, then:

1. `../porting-to-the-beeb.md`: the method, the harness, the screen,
   sound, memory, transcribing Z80, baron, and Matt's house rules.
2. The siblings, for what each is closest in:
   - `../cauldron-beeb`: the same series, artist and screen. Its colour
     scheme, palette splits, harness and build are the ones to copy.
     Read its `CLAUDE.md`, `docs/decisions.md` (2, 3, 4, 5 and 13 in
     particular) and `docs/journal.md`.
   - `../nm`: Z80 transcribed by hand to 6502, which is how this port's
     logic will be done (Cauldron 1's wasn't; see below).
   - `../chuckie-egg-2-beeb`: flip-screen rooms, sideways RAM, and
     `docs/optimising.md`.

Then do a quick look around and ask Matt the questions at the end
before running on your own.

## What's already known (2026-10-30)

An agent from the cauldron-beeb session looked at the game, to decide
whether this is part of that port or its own project. It is its own
project: Cauldron II shares no code with Cauldron 1's Spectrum version.

### Verified from the bytes and by running it

- **Loading.** BASIC `10 BORDER 0: PAPER 0: LOAD ""CODE : LOAD ""SCREEN$
  : PAUSE 0: ... RANDOMIZE USR 25000`. A 70-byte loader at 25000 reads a
  table of (address, length) pairs and loads one headerless block at
  15384 (so 16384-64998; the first 1000 bytes fall on the ROM), then
  jumps to 52180. The main block is identical in Spectrum Computing's
  TAP and TZX. `tap2sna.py --press 7:SPACE -s 52180` makes a snapshot at
  the entry.
- **Hand-written Z80.** None of the BASIC compiler's signatures that
  Cauldron 1 is full of (`EX DE,HL : LD HL,n`, `LD A,H : OR L : JP Z`,
  the ROM calls for PRINT, PAUSE, BEEPER), and none of its runtime
  library. It never calls the ROM in play. So cauldron-beeb's
  decompiler, bytecode compiler, VM and runtime have nothing to work on.
- **Interrupts.** IM 2, the vector table at 65024-65280, the handler at
  57664: it counts frames and runs per-frame work.
- **State.** Bytes of its own around 24000-24040. Random numbers seeded
  from R.
- **Drawing.** Sprite routines at 57138 and 57194 XOR the sprite into
  the screen by the Spectrum's addressing; 57194 then may XOR a block of
  attributes too (the `OR 88` at 57270), which is where colour and clash
  come from.
- **The logic reads attributes.** A helper at 57326 returns the
  attribute under a screen address; the movement and collision code at
  54842-55066 calls it five times. So, as in Cauldron 1, the attributes
  must stay exactly the original's even if the colours on screen don't
  (cauldron-beeb's decision 5).
- **Sound.** A two-channel beeper music engine (`OUT (254)` loops), in
  three copies at about 50216, 51516 and 51966, perhaps one per tune. It
  takes the CPU while it plays. In play the effects are sparse. No AY.
- **Memory.** The game fills 23296-64998 plus the IM 2 table; little of
  it is empty. Executed code lies in 50100-57725 (some tune data inside
  it); the rest is graphics, rooms and tables. It probably needs 32K of
  sideways RAM, or compression, as Cauldron 1 does. That is an estimate,
  not a measurement.
- **Shared with Cauldron 1:** a little art (the panel font and some
  sprite frames: bats, ghost, explosion), no code.
- **On screen.** A menu like Cauldron 1's (1 Kempston, 2 Interface II, 3
  Keyboard, 4 Play Game). Flip-screen rooms under a panel at the top
  (score, MAGIC %, pumpkin lives). The pumpkin bounces; the credits
  scroll: Steve Brown (plot, graphics), Richard Leinfellner (code),
  Richard Joseph (sound).

### Read online, not verified

- Spectrum Computing's [entry 851](https://spectrumcomputing.co.uk/entry/851)
  names no compiler (Cauldron 1's, entry 850, names Phipps Associates').
  48K, Kempston, Interface 2 and redefinable keys.
- [Wikipedia](https://en.wikipedia.org/wiki/Cauldron_II:_The_Pumpkin_Strikes_Back):
  the C64 version came first (Stan Schembri), then the CPC and Spectrum
  (Leinfellner). Flick-screen was chosen over scrolling; the bounce and
  collision were hard to get right.
- No BBC, Electron or Atari 8-bit version, official or fan. A fan Plus/4
  port came out on 31 October 2023
  ([Plus/4 World](https://plus4world.powweb.com/software/Cauldron_II)),
  its physics slightly different.

### Not known yet

- Whether the Spectrum code was converted from the C64's.
- The music data's format.
- The number of rooms and how they're stored.
- How big the 6502 translation will be.

## What to take from cauldron-beeb, and what not

Copy, as cauldron-beeb copied from its siblings:

- `tools/zx.py` (it ran Cauldron II unchanged), `play.mjs`, `beeb.mjs`,
  `grid.py`, `asm.sh`, `lint_labels.py`, `zx02.py`, the Makefile's shape
  and `tools/fetch_original.sh`'s (with `SHA256SUMS`).
- The screen: decision 2's MODE 1 in the Spectrum's geometry.
- No clash: decision 5's lit pixels and attribute shadow exactly the
  original's, with colours that are the port's own; the palette splits
  of decisions 3, 4 and 13 (`src/irq.6502`).
- The checks' method: `make draw` and `make sprites` draw with the
  original's own code and compare byte for byte; `make passes` plays
  both side by side and compares state every pass. Here the state is
  the game's own bytes, listed by hand from the research.
- `src/sound.6502`'s SN76489 driver as a start.

Don't copy: the decompiler and compilers (`decompile*.py`, `bas2vm.py`,
`bas2native.py`), the VM and its runtime (`vm`, `basrt`, `vmxlat`,
`vmio`), `vmcheck.py`, `zxhot.py`, the landscape (`scroll`, `land`),
SPRITE's specifics, or decision 8's chirps-as-tones: Richard Joseph's
two-channel music wants transcribing for the SN76489, which is new.

Lessons cauldron-beeb learnt the hard way:

- `!BOOT` mustn't load into screen memory: the OS echoes its lines into
  MODE 7's screen at `&7C00`.
- Baron: set a file-level `ZA_AUTO` after the calls that come before its
  use; self-modified `JMP` targets need `ZA_CANJUMP`.
- The README's jsbeeb links (`?autoboot&disc1=github:mattgodbolt/<repo>/<disc>.ssd`)
  play the disc committed at the repo's root. Rebuild and commit it
  after every change Matt might try.
- `make check` before every commit, reading its exit status; on the
  Master too.

## Files here

- `prior/`: from the investigation, not to be committed (the original's
  content). `c2.skool` is a plain disassembly of 50000-61500 from the
  entry snapshot, with no labels yet. `grid1.png`-`grid3.png` are the
  original's menu, credits and rooms.
- `.gitignore`: `original/`, `prior/`, `build/`, `.venv/`, `shots/`.

## The original

Spectrum Computing, `https://spectrumcomputing.co.uk/pub/sinclair/games/c/`:

- `CauldronII-ThePumpkinStrikesBack.tap.zip` and `.tzx.zip` (Palace).
- `CauldronII-ThePumpkinStrikesBack(SilverbirdSoftwareLtd).tzx.zip`.
- `CauldronII-ThePumpkinStrikesBack(CauldronII-LaCalabazaContraataca)(ErbeSoftwareS.A.).tap.zip`
  and `.tzx.zip` (Spain).

Fetched into `original/`, never committed. Treat downloads as untrusted:
run Python over them with `-I`.

## Ask Matt up front

Cauldron 1's answers, to confirm or change:

- **Targets:** a Model B with sideways RAM and the Master 128, from one
  disc? (Cauldron 1 needs 32K of SWR; 16K is its aim.)
- **The specification:** the Spectrum version (rule 1), or the C64's,
  which came first and is 6502?
- **Scope:** how far to go alone, with calls marked provisional in
  `docs/decisions.md` for review.
- **Colour:** no clash, as Cauldron 1?
- **Keys:** the BBC's usual (Z, X, `:`, `/`, RETURN)? The pumpkin's
  controls are different, so check what it needs.
- **Rights:** unofficial for now, the original fetched but not committed?
- **Commits and the remote:** local commits and pushing to
  `github.com/mattgodbolt/cauldron-2-beeb`, public?

## House rules

- Commit messages end at `Co-Authored-By:`. Never a claude.ai session
  link or a `Claude-Session:` trailer, anywhere. Never force-push a
  pushed branch; fix with additive commits.
- Comments and docs carry no figure the build computes or one run
  measured (addresses, sizes, free bytes). Name the symbol, `ASSERT` the
  property, or cite the dated decision. The original's addresses and the
  hardware's are fine.
- Never label a statement "honest" or "candid". Size work by what it
  touches, never by time. Matt is they/them.
- Every agent brief carries these rules.
