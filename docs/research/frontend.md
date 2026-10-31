# Front end, text and panel

Research on the original's menu, credits, game-over and win screens, text
printing and the panel. Control file: `disasm/frontend.ctl`. Addresses are
decimal. Sound is in `sound.md`. Checked by running the original on
SkoolKit's simulator (scripts and shots under `build/research/fe/`).

## Flow

    52180 cold start ──> 52235 warm start <── abort key (52775)
                          │                <── game over (53101) after fire
                          │                <── win (56811) after fire
                          ├ reset tune players, play tune 1's first tick, 24002 = 1
                          ├ clear screen (53087)
                          ├ menu (52481): wait for 1-4
                          ├ clear screen
                          └ credits loop (52290): pages 0/1 alternate until fire
                               └ fire: 24002 = 0 (music off), game starts at 52372

- **`52180` cold start**: IM 2 table at 65024-65280 (all 253, vector
  65021), `JP 57664` at 65021 (copied from 52232), border 0, `(24006)` = 0,
  default keys `57760` copied to the active table `57784`. Once only.
- **`52235` warm start**: `SP` = 0, seed `61248` from R, `24007`/`24008` =
  0, the three players' border byte = 0 and tempo = 250, `CALL 50100`
  (tune 1 from the top, one tick), `24002` = 1 (the interrupt plays tune 1
  from now on), clear screen, menu, clear screen, credits loop.
- **Menu `52481`**: prints `57872` at row 1, column 10 and polls half-row
  63486 (keys 1-5):
  - **1**: Kempston: reader = `52658`.
  - **2**: Interface II: active keys = defaults, reader = `52695`.
  - **3**: Keyboard: wait for 1-5 released, print `DEFINE KEYS` at row
    12, column 10, then six prompts (`UP`, `DOWN`, `LEFT`, `RIGHT`,
    `FIRE/BOUNCE`, `ABORT GAME`, from `58784`) at row 14, column 10, each
    followed by `52610` (wait for a key); stores its port and mask in the
    active table; reader = `52695`. Checked: Q A O P M X gave
    `57784` = `FE FB 01 01, FE FD 01 02, FE DF 02 04, FE DF 01 08, FE 7F 04
    10, FE FE 04 40`.
  - **4**: play with the reader as it is. At power-on that is `52695` with
    the Interface II keys (the snapshot's `57726` = 52695).

  All four return to the credits; fire there starts the game. There is no
  separate "start" from the menu.
- **Credits loop `52290`**: when the page countdown `24007` is 0: clear,
  print page `24008` (text from `58776`, position from `58780`: page 0 at
  row 0 column 3, page 1 at row 0 column 6) **with interrupts off** (the
  music pauses for the print), countdown = 50, flip the page. Every pass:
  step `61248`, delay 10000 counts (`DEC BC` loop), read the input (abort
  restarts), fire starts the game, count down. Measured: a page shows for
  about 655 frames with tune 1 playing, since the music takes 2.11 of
  every 3 frames.
- **Game over `53101`**: from 52975 when the lives (`24035`) go below 0.
  `DI`, `CALL 51850` (tune 3 from the top), `24002` = 2, `EI`, clear,
  print `58515` at row 3, column 6 (magenta verse ending in red `THY
  SCORE`), print the score string `58803` at row 21, column 16, wait for
  fire released then pressed, `JP 52235`. Checked by forcing it
  (lives 0, magic 00, fire).
- **Win `56811`**: reached through the table at 61131 (game logic). If
  the seven bytes at 24070 don't match 61514's, the pumpkin dies
  (`56571`). Otherwise: +100 (`58850`), `DI`, `CALL 51400` (tune 2),
  `24002` = 3, `EI`, clear, print `58666` at row 6, column 6, the score at
  row 12, column 16, wait for fire, `JP 52235`. Not reached in a run.

### Input

`52767` reads the input: it pushes `52775` as the return address and
jumps to the reader at `(57726)`. `52775` does `BIT 6,A` and `JP NZ,52235`
(abort), else returns with A intact and the flags from the `BIT`.

Input bits (both readers): 0 up, 1 down, 2 left, 3 right, 4 fire, 6
abort.

- **`52658` Kempston**: `IN (31)`, bits 0-3 mapped through `57744`
  (Kempston R1 L2 D4 U8 to the game's U1 D2 L4 R8), fire bit 4 kept;
  abort = key A alone in half-row 65022. Preserves BC, DE; HL changed.
- **`52695` keyboard**: the six entries of `57784` (port low, port high,
  key mask, action bit); ORs the action bits of keys held. Up+down and
  left+right cancel. Preserves IX, DE, BC.
- **`52610` wait for a key**: scans the eight half-rows (`57728`) until
  one has a key (bits 0-4) down; the key must read held 256 times in a
  row, then released 256 times in a row. Returns BC = port, A = the keys
  held in that half-row (several bits if several keys). No check for a
  key already used.

Defaults (`57760`, Interface II port 1 on keys 6-0): 9 up, 8 down, 6
left, 7 right, 0 fire, A abort. Redefining keeps each entry's action bit
and replaces only the port and mask. Redefined keys survive games (the
cold start's copy isn't repeated); option 2 restores the defaults.

## Text

### The printer `54363` (`print`)

In: HL = string, B = character row (0-23), C = column (0-31). Out: HL at
the `$`; C = the first column, B = the first row plus the newlines
(the row is kept on the stack and bumped by each 13); A, DE, flags
changed.

| Byte | Meaning |
|---|---|
| 36 `$` | end |
| 13 | next row (B+1), column back to the string's first column |
| 128-255 | attribute = byte AND 127, kept in `24024` for what follows |
| `0`-`9` | glyphs 0-9 |
| `A`-`Z` | glyphs 10-35 |
| other | looked up in `57817` (27 characters) to `57844` (their glyphs) |

The other characters: space 37, `%` 36, `@` 59 (the copyright sign), `-`
60, `/` 61, `^` 62, `~` 63, and lower case `e`-`x` = glyphs 38-57 (the
witch faces). A character in neither list would print as the glyph its
own code gives; none of the strings has one.

Each character: `54464` copies the glyph's 8 bytes to the screen (plain
stores, no XOR) at the row address from `58883` + column, then the
attribute cell (via `57341`, which turns the screen address into the
attribute address with `DE` = 22528) gets `(24024)`. So text sets the
attribute of every cell it prints, including spaces. The attribute
carries over from string to string until a string sets its own; all of
them start with one.

### The font

`49511`, 64 glyphs of 8 bytes, top row first, 1 bit per pixel (bit 7
left). 0-9, A-Z (stylised: the S looks like a backwards 2), `%`, space,
20 witch-face pieces (38-57), an unused glyph (58), copyright (59), and
four small marks (60-63). The brief says the panel font is shared with
Cauldron 1. `build/research/fe/font.png` renders it.

### Strings

| Address | Text | Where |
|---|---|---|
| 57872 | ` CAULDRON II` (attr 70), then `1 KEMPSTON` ... `4 PLAY GAME` (attr 5) | menu, row 1, col 10 |
| 57941 | `DEFINE KEYS` (66) | row 12, col 10 |
| 57954-58019 | six prompts, 11 chars each, padded with spaces (70) | row 14, col 10 |
| 58032 | `SCORE` (68) | panel row 0, col 13 |
| 58039 | `MAGIC` (66) | panel row 2, col 13 |
| 58046 | credits: CAULDRON II, PEERLESS PLOT, STEVE BROWN, GORGEOUS GRAPHICS, STEVE BROWN, CRAFTY CODE, RICHARD LEINFELLNER, SCINTILLATING SOUND, RICHARD JOSEPH, `@ PALACE SOFTWARE MCMLXXXVI` (titles 5, names 66, rest 70) | page 0, row 0, col 3 |
| 58301 | the verse: MAGIC OBJECTS / THOU WILL NEED / ... / AND MAY THY BOUNCE / BE EVER HIGHER | page 1, row 0, col 6 |
| 58515 | THOU HAST AMASSED / A MEAGRE SCORE / ... / THY SCORE (3, last line 2) | game over, row 3, col 6 |
| 58666 | WELL DONE / THOU HAST COMPLETED / CAULDRON II WITH A / SCORE OF / THE WITCH IS DEAD / LONG LIVE THE WITCH | win, row 6, col 6 |
| 58803 | score: attr 67, seven ASCII digits at 58804-58810, `$` | panel row 1, col 12; also game over and win |
| 58812 | magic: attr 5, two ASCII digits at 58813-58814, `%`, `$` | panel row 3, col 14 |
| 61162 | left witch: `efgh`/`ijkl`/`m`/`n` with attrs 68 and 70 | row 0, col 0 |
| 61189 | right witch: `rqpo`/`vuts`/`w`/`x` | row 0, col 28 |

## The panel

Character rows 0-3 (the top 32 pixel lines). Drawn for each new game by
`53550` after `53858` has reset everything:

1. Lives `24035` = 6; six pumpkin icons, sprite frame 1, drawn by the
   sprite routines (`57415` then `57194`, XOR) at `D` = `58796` (19) and
   `E` = `58797`-`58802` (20, 32, 43, 76, 87, 99). From the screen these
   look like D = pixel row and E = x / 2 (see the drawing research).
2. Attributes of rows 0-3 = 70 (bright yellow on black).
3. `SCORE`, `MAGIC`, the left witch (text, 4x4 cells), the score (`57616`
   with the zero record `58835`), the magic (`57568`, subtracting 00), the
   right witch.
4. The witches' mouths: `53823` with A = 53 draws sprite frame 53 at
   DE = 3332 (D 13, E 4) and frame 56 at 3440 (D 13, E 112), XORed over
   the text faces.

So the panel's colours come from the text attributes: SCORE bright
green, digits bright magenta, MAGIC bright red, magic digits cyan, the
witches bright green and yellow, the pumpkins in the 70 base. The pumpkin
sprites' own attribute handling is the drawing research's.

### Updates

- **Score `57616`** (`score_add`): DE = record `n, d1..dn` (decimal
  digits, `58835`-`58882`); adds it right-aligned to the ASCII digits
  58804-58810 with decimal carry (none out of the top digit), then
  reprints `58803` at row 1, column 12. Records by points class (`58817`,
  indexed by the monster table's bits 0-3 at 56381): 0, 50, 100, 200,
  300, 500, 750, 1000, 5000.
- **Magic `57568`** (`magic_sub`): DE = record `n, tens, units`
  (n not read); subtracts the two digits from 58813-58814; if it goes
  below 0, the magic becomes `00` and `56571` kills the pumpkin. Reprints
  `58812` at row 3, column 14. Carry out = ran out. Callers: firing
  (53214, record `58880` = 1%), a monster destroyed (56402, `58841` = 8%),
  the reprint after a life lost (53009, record 0).
- **A life lost** (`52964`, game logic): lives - 1; if negative, game
  over; else XOR off the icon at `58797 + lives` (the rightmost
  remaining), magic = `99`, reprint the magic, then the game logic carries on
  (53015-53033).
  With 6 icons at the start, there are seven lives in all.
- **The witches cackle `53651`** (`witch_anim`), once per main-loop pass:
  a room change (53310) sets `24013` = 10 (passes to wait) and `24032` =
  143 (bit 7 = start, 15 steps). Each step draws the next mouth frames
  from `61216` (53 closed, 54 and 55 open) over both faces, with two
  `HALT`s and four cackle pulses (`53798`, sound.md), then waits a pass
  (`24033`).

### Spectrum dependencies

- The text writes straight to the Spectrum's display file through the
  row table `58883` (24 words, the top pixel line of each character row;
  `57307` adds the pixel line within the row for the sprite code) and the
  attribute file at 22528.
- The game reads attributes back (brief): the panel's attributes (70 and
  the text's) are under the 32 top lines and the room starts at row 4
  (53310 clears attributes from 22656, row 4).
- `53087` (`cls`) clears 23296 down to 16385 with `LDDR`: byte 16384 is
  never cleared and 23296 (one past the attributes) is.

## Variables

| Address | Size | Name | Meaning |
|---|---|---|---|
| 24002 | 1 | fe_mode | 0 play, 1 title music, 2 game over, 3 win (sound.md) |
| 24006 | 1 | border | Border colour for OUTs (0) |
| 24007 | 1 | page_count | Credits passes left on this page |
| 24008 | 1 | page | Credits page, 0 or 1 |
| 24013 | 1 | witch_delay | Passes before the cackle starts |
| 24020 | 1 | input | Input bits read this pass (52447) |
| 24024 | 1 | text_attr | The printer's current attribute |
| 24032 | 1 | witch_step | Cackle steps left; bit 7 = just started |
| 24033 | 1 | witch_wait | Passes to wait between steps |
| 24035 | 1 | lives | Spare lives (icons shown) |
| 57726 | 2 | input_reader | Reader routine (52658 or 52695) |
| 57784 | 24 | keys_active | Six (port, mask, action bit) entries |
| 58804 | 7 | score | ASCII digits |
| 58813 | 2 | magic | ASCII digits |
| 61248 | 2 | rnd_ptr | Random pointer, also a frame counter |

`53858` (`new_game_init`) zeroes 24000-25058 for each game, so 24000-24060
start at 0 in play.

## Cross-area notes

- The IRQ handler `57664` also counts frames in `61248` (the pointer the
  game takes random bytes from).
- The main loop's pass in play measured about 0.6-1.1 frames (from the
  bounce pulses' spacing); not frame-locked.
- `57355` searches the 9 bytes at `57808` (`ABCDE` and 7, 1, 6, 12):
  game logic's, not text.
- `53534` sets the border from A (only ever 0).
