# How the port works

## The transcription's conventions

The original is hand-written Z80 (`docs/research/*.md`, `disasm/*.ctl`).
It is transcribed by hand, routine by routine, so each 6502 routine reads
beside its original.

### Names

- **`zNNNNN`**: the transcription of the Z80 code at decimal address
  NNNNN, a routine or an entry point inside one (`.z57326`). Call the
  original's routines by these names whether or not they're written yet:
  `tools/mksyms.py` gives every one referenced but not defined a stub
  (`build/stubs.6502`) that stops at `unwritten` with the address in
  `unwritten_at`, and the build lists them. Give a routine a readable
  alias too if you like (`attr_under = z57326`), but define the `z` name.
- **`aNNNNN`**: where the original's byte NNNNN lives on the BBC. Use it
  for every variable, table and text: `LDA a24030` (the room),
  `LDA a63498,X` (the map). `tools/mksyms.py`'s `REGIONS` say where each
  range went; it defines every `aNNNNN` the sources use. The layout
  inside each range is the original's, so `a24077 + 20` is slot 1.
- The original's constants are written as the original's numbers, with
  the original's address in a comment where it helps.

### Memory

| Original | BBC | Notes |
|---|---|---|
| 22528-23295 attributes | `attrs`, page-aligned | exactly the original's (decision 5); a Z80 attribute address's high byte + `ATTR_HI` is ours |
| 24000-25099 variables, slots, buffers | `vars`, main RAM | the original's layout |
| 25900-34525 sprites | sideways bank GAMEDATA | |
| 34526-49510 tiles, blocks, layouts, tile attributes | sideways bank ROOMDATA | paged in only while a room draws |
| 49511-50022 font | main RAM | |
| 57726-64998 tables, texts, sound data | sideways bank GAMEDATA | paged in all the time |
| 16384-22527 screen | `screen` (MODE 1) | read through `zx_read` |

Pointers stored in tables become BBC addresses (`tools/mkdata.py`
relocates them: `EQUW aNNNNN` or `EQUW zNNNNN`). Pointers into the
Spectrum's screen or attribute file stay the original's values, since
the code does arithmetic on them.

### Registers

The Z80's registers live in fixed zero page (`src/regs.6502`): `rb rc rd
re rh rl`, pairs `rbc rde rhl` (low byte first), `rix riy` (pointers:
`LDY #6 : LDA (rix),Y` is `LD A,(IX+6)`), and an alternate set. A is A.
Keep what a routine leaves in them: callers rely on it, and the research
says where. Watch the flags (`LDY #0` sets Z; `STA` sets none; a Z80 `CP`
sets carry the other way round from the 6502's for "less than": Z80 C
set means A < n, the 6502's C clear).

The interrupt (`irq.6502`) calls `vsync_hook` at each VSync; the
original's per-frame work (57664) goes there. It must save and restore
any of the register zero page it uses.

### The screen

The original's screen addresses stay in the registers and their
arithmetic is the original's (INC H for the next pixel line, the
character-row tables). Only the access translates:

- `zx_read`: A = the lit pixels of the Spectrum byte at HL, as
  `LD A,(HL)` would read them. `zx_addr` sets `zx_ptr` to our address of
  HL (the cell's left four pixels; its right four are at +8).
- Our screen keeps **exactly the original's lit pixels**; only their
  colour is ours (decision 5). The collision code reads pixels (sprites
  included) and attributes, so both must stay exact.
- Writes go through the drawing's own routines (`draw.6502`), which
  colour what they light.

### Time

- `EI : HALT` becomes `JSR wait_vsync`: the original's pace comes from
  its HALTs (one per moving object, `docs/research/core.md`), and so
  does ours.
- A busy loop of T T-states becomes `wait_us` for T / 3.5 microseconds
  (User VIA T2), so the original's pace holds.
- `DI`/`EI` around the original's stack tricks aren't needed: rewrite
  the trick, keeping its result.

### Sideways RAM

GAMEDATA stays paged in (`romsel` and the OS's copy `romshad`). The room
drawing pages ROOMDATA in for as long as it reads the room's data and
pages GAMEDATA back (`page_rooms`, `page_game`).
Most of the sprite drawing runs from GAMEDATA itself (decision 17): it
reads GAMEDATA's tables, so it needs it paged in anyway.
