# Core, rooms and drawing

Research notes on Cauldron II's (ZX Spectrum) startup, main loop, room
entry and drawing, the low-level primitives and the interrupt, for
transcribing to 6502. Decimal addresses are the original's. The control
file is `disasm/core.ctl`; the room oracle is `tools/zxrooms.py`.

What was measured (rule 4), not just read:

- Every room's scenery, all 128, re-drawn in Python from the format below
  and compared with the original's own drawing (`tools/zxrooms.py`): zero
  differing bytes, pixels and attributes.
- The sprite pre-shift (57415): all 155 frames at x = 12-15, 40, 41
  against a model of the format below: identical, and the returned B and C
  are as stated.
- The clipped draw (57058, slot 0) at the four edges, and the coloured
  draw (57194): which cells and lines change.
- The main loop's pace, and the HALTs executed in play.
- The trip outside (53310), run and screenshotted.

## Screen layout

- Character rows 0-3 (pixel lines 0-31): the panel. Its attributes are
  set to 70 (bright yellow on black) by 53550, then text sets its own.
- Character rows 4-23 (lines 32-191): the play area, one room, 32x20
  characters. The room routines only touch these rows.
- The border is black; 24006 is a shadow of the last `OUT (254)` value.

## Startup (52180) and restart (52235)

52180, entered once from the loader:

1. Fills 65024-65280 with 253 (257 bytes), `I`=254, copies `JP 57664`
   (template at 52232) to 65021, `IM 2`. Any vector byte reads 253/253,
   so the handler is always 65021 → 57664.
2. Border 0, 24006=0.
3. Copies the default (Interface II) key table 57760 → 57784 (24 bytes).

52235 is the restart point (also reached from ABORT, game over, win):

1. `LD SP,0`: the stack is 65281-65535, above the vector table. Nothing
   ever returns from here.
2. The random pointer 61248 = 225×256 + R (H is left at 225 by the
   startup's `LD HL,(52233)`).
3. Resets the three tune players; `CALL 50100` (title tune, sound area);
   24002=1 so the interrupt plays it each frame; `EI`.
4. CLS (53087), menu (52481: 1 Kempston, 2 Interface II, 3 define keys,
   4 play; any choice returns), CLS.
5. Attract loop 52290: every 50 passes prints the other credits page
   (24008 toggles 0/1; strings from 58776, positions from 58780). Each pass
   steps the random pointer, burns 10000 `DEC BC` loops, reads the
   controls; fire starts a game.
6. New game, 52372: 24002=0 (music off); start room = 61240[(byte at the
   random pointer) AND 7], one of 56, 10, 97, 79, 37, 70, 110, 107; reset
   (53858); panel (53550); player to the room's start position (52945);
   draw the room (53949); clear 24026-24028; 24046=2650, 24048=8384 (never
   read anywhere that was found); reset the player state (53036).

The random pointer is a pointer, not a seed: the game reads the byte it
points at. It is stepped once per interrupt and once per attract pass, so
the start room depends on how long the attract screen ran. It is used
only for the start room in the code read here.

## Main loop (52430-52478) and pacing

```
52430  if (24034) != 0: 52964 death countdown   (skips input/player)
52437  if (24012) != 0: 52920 outside countdown (skips input)
52444  A = read controls (52767 → (57726)); (24020) = A
52451  53149 fire-repeat timer (24015; clears 24016 at 0)
52455  if fire (bit 4): 53163 cast a spell (slot 1, type 32, magic -1)
52463  54530 the player                         (player area)
52466  55783 move and redraw all objects        (objects area)
52469  53408 room exits
52472  53651 panel witch heads' animation
52475  55285 respawn monsters (room list at (24042))
52478  JP 52430
```

The controls byte: bit 0 right, 1 left, 2 down, 3 up, 4 fire, 6 abort
(CAPS SHIFT on Kempston; a key in the key table). 52775 (the return
address pushed by 52767) restarts the game when bit 6 is set, from any
caller. The keyboard reader cancels opposite directions.

**There is no frame sync in the loop itself.** The pace comes from
55783 (objects area): for each of the six object slots that moved
(24025), it pre-shifts the new and old frames, then `EI : HALT` (56256),
then XORs the old image off and the new one on; a slot that didn't move
burns a 1024-pass `DEC BC` loop instead. So a pass waits for one frame
per moving object. Measured from the start of a game in room 97: 2.5-7.2
frames a pass, mostly 3-5, often a whole number. The only other HALTs met
in play are in the room-entry routines (54225, 54509) and the head
animation (53727, 53771).

## The interrupt (IM 2, 65021 → 57664)

Every frame:

1. Pushes AF, HL, DE, BC, IX, IY (not the alternate set).
2. Steps the random pointer 61248.
3. If 24002 ≠ 0, calls the word at 64019 + 2×(24002): 1 → 50113 (title
   tune step), 2 → 51863 (game over), 3 → 51413 (win). In play 24002 is 0.
   The title tune step calls the ROM's KEY-SCAN (654) from the interrupt.
4. If 24000 ≠ 0 (a sound effect is running): 24000 -= 1, and 52854 beeps
   with pitch (24000 AND 31) + 50 (sound area).
5. `EI : RETI`.

It never draws and never reads the controls. 57415 runs with
interrupts off while it borrows SP, then executes `EI` regardless.

## Rooms

### Count and map

**128 rooms**, 0-127. Every one draws (contact sheet from
`tools/zxrooms.py`). Rooms 52, 110 and 117 are the outdoor garden;
121-127 are a row of rooms with the yellow-framed floor.

The map, 63498-64009: 4 bytes per room, the neighbour to the **left,
right, below, above**. A neighbour with bit 7 set (seen: 245, 238) means
"outside": room 245 AND 127 = 117 or 238 AND 127 = 110, reached through
the trip outside (53310). 53408 tests the player (slot 0) each pass:

| test | exit | player re-enters at |
|---|---|---|
| x ≤ 8 | map +0 (left) | x = 135 |
| x ≥ 136 | map +1 (right) | x = 9 |
| y + height ≥ 201 (height = slot byte 18) | map +2 (below) | y = 28 |
| y ≤ 27 | map +3 (above) | y = 200 − height |

The x test comes first, then y; one exit a pass. 53408 does nothing while
dying (24034 ≠ 0). 53408 loads 24030 as a word then zeroes H, so 24031 is
not involved.

### The trip outside (53310)

Sets the room to A AND 127, clears the play area's pixels and sets its
attributes to 70, puts object type 33 in slot 0 at x=76 y=100 (a
pumpkin flying off, shrinking), starts the heads' animation (24032=143,
24013=10) and a countdown of 105 main-loop passes (24012). Meanwhile the
loop skips input but still runs the player, objects and heads. At 0,
52920 clears the play attributes, puts the player at the new room's start
position and draws it. Measured: about 300 frames from the edge to room
117 appearing.

### Death and lives

24034 counts the death down (set by the player or monster code, not read
here). At 0 (52964): lives 24035 −1; below 0 → game over (53101);
otherwise the life's pumpkin is XORed off the panel (y=19, x from 58796+1
by the lives count), magic back to "99", and the room is re-entered (or,
if the player died in 124-127 without all seven ingredients, the paired
room from 61232/61236: 124, 125 → 112; 126, 127 → 115) with the player at
that room's start position (61250, a word per room: x, y).

### How a room is stored and drawn (53949)

Three levels, all verified byte for byte:

1. **Layout**, 43750 + 40×room (43750-48869): 5 rows × 8 columns of
   block numbers.
2. **Blocks**, 39654 + 16×block (39654-43749, 256 blocks): 4×4 *tile
   bytes*, row by row. 225 of the 256 blocks are used.
3. **Tile banks**: the tile byte becomes a *tile number* through the
   room's bank list. Word table 62954 + 2×room → a list (16 distinct
   lists, 63210-63497): a count n, then n × (lo, hi, base word). The first
   entry with lo ≤ byte ≤ hi gives tile number = base + byte; if none
   matches, the tile number is the byte itself (bytes 0-105 never match).
   Some bases are negative, stored mod 8192 (8183, 8191, 8138). Tile
   numbers used run 0-640.
4. **Tile pixels**: 8 bytes at 34526 + 8×tile number (34526-39653, 641
   tiles), top line first. The address is formed in 16 bits, so a
   negative base wraps.
5. **Tile attribute**: 48870 + (tile number AND 8191) (48870-49510).

The same tile byte can therefore be different graphics in different
rooms: the banks let 256 tile bytes reach 641 tiles.

In code, 53949 (all registers preserved; A = room):

1. 54213: `EI : HALT`, then attributes 22656-23295 (rows 4-23) to 0, so
   the pixel drawing that follows is invisible.
2. Saves object slot 0 (the player, 24077, 20 bytes) to 24203 and clears
   all six slots (55472, objects area); (24030) = room.
3. For char rows 4-23, columns 0-31, by block: the tile's 8 bytes are
   written with LD (not XOR) straight to the screen (54464, through the
   character-row table 58883); the attribute goes into a buffer at
   24225 (the cell's offset in the attribute layout, minus 128).
4. 54499: `EI : HALT`, then LDIR 768 bytes 24225 → 22656. 640 are the
   play area; the last 128 go to 23296-23423 (printer buffer), harmless.
   The port needs only the 640.
5. Restores slot 0, sets 24022=0, pre-shifts and XORs the player at its
   position (old position = new), slot byte 1 = 128.
6. 54264: spawns the room's monsters; 54229: spawns its item.

Monster lists (objects area, noted here because room entry runs them):
word table 61677 + 2×room → list (61933-62953): count, then per monster
x, y and either one byte with bit 7 set (type from 61142 by bits 0-1,
plus 1 if the room's bit in 24054-24069 is set; 3-byte entry) or a flags
byte and a type byte (4-byte entry). Monster i goes in slot 2+i, unless
its type is one of the seven ingredients held (24070-24076). Items: the
52 room numbers at 61521 (bit 7 set once collected), positions at 61573;
the item is object type 32 in slot 5.

## Graphics formats

### Character tiles and font

Plain 8×8, 8 bytes top line first, no mask. Tiles at 34526, font at
49511 (64 glyphs, 49511-50022). Each tile has its own attribute (48870).

### Strings (54363)

HL = string, B = char row, C = column. Bytes: `$` (36) ends; 13 = next
row, back to the starting column; 128+n sets the attribute n (held in
24024) for what follows; `0`-`9` → glyphs 0-9; `A`-`Z` → 10-35; others
through the translation table 57817 (27 characters) → 57844 (glyph
numbers): space 37, `%` 36, `@` 59, `-` 60, `/` 61, `^` 62, `~` 63,
`e`-`x` 38-57. Glyphs are written with LD; the attribute goes straight
into the attribute file. The panel's two witch heads are font
characters `e`-`x` (strings 61162, 61189).

### Sprites

Frame table 59798: 4 bytes per frame (width in bytes, height in lines,
address), 155 frames plus a 0×0 one (frame 154), graphics at
25900-34525. Row-major bytes, no mask: everything is drawn with XOR,
and erased by drawing again. Largest frame 8 bytes wide, 48 high;
largest (width+1)×height is 192. 60422: a byte per frame, the
attribute it XORs on (0 for none; seen 1, 4, 65, 67, 68, 69). Object
types (60580, objects area) give each object's frames.

Coordinates: x in 2-pixel units with an origin of 12: screen pixel =
2×(x − 12), byte column = x/4 − 3, shift = 2×(x AND 3) pixels; y is the
screen pixel line (32 = top of the play area). So x moves in 2-pixel
steps; a sprite has 4 shift positions.

Drawing an object is two steps:

1. **57415 pre-shift**: copies frame A into a buffer (24225 for the new
   image, 24427 for the old), each line followed by a zero byte, then
   shifts the whole buffer right by the shift, one bit a pass, as one bit
   stream: `DI`, SP into the buffer, `POP HL : RR L : RR H : PUSH HL :
   POP HL` across it, SP restored from 24050, `EI`. Returns B = lines,
   C = width+1. The two bytes before the buffer are zeroed and included
   in the stream.
2. **57058 XOR to screen**. Slots 0 and 1 (the player and its spell,
   24022) are clipped and colourless (57074/57138): horizontal clipping
   by a skip count (24038) and a limit (24039), vertical by the
   pixel-line table 58931 (232 words): lines 0-31 and 192-231 point at a
   sink line at 24995, 32-191 at the screen. Slots 2-5 go through 57182 →
   57194: no clipping, then the frame's attribute XORed onto C × ⌈B/8⌉
   cells starting at the cell of the top line. A sprite whose top line is
   not on a cell boundary can overlap one more cell row than is coloured.

Because the colour is XORed, drawing a coloured monster twice restores
the attributes; and the attributes under a monster are the room's XOR
its colour while it is drawn. The logic reads attributes (57326, used by
the player area), so the port must keep the attribute bytes exactly the
original's (cauldron-beeb's decision 5).

### Panel (53550)

Lives: six pumpkins (frame 1) at y=19, x from 58796. Rows 0-3
attributes 70. "SCORE" (58032, attr 68) at row 0 col 13, "MAGIC"
(58039, attr 66) at row 2 col 13; the score (58803: attr 67, 7 ASCII
digits at 58804-58810) at row 1 col 12; the magic (58812: attr 5,
digits at 58813-58814, `%`) at row 3 col 14; the witch heads as text at
(0,0) and (0,28), then frames 53 and 56 XORed at (E=4, y=13) and
(E=112, y=13) through 57194 (E/4 = column). 53651 animates the heads
(frames from 61216, both heads, with HALTs and a beep per step).

Score and magic are ASCII digits, added (57616: count n, then n digit
values for the last n digits) and subtracted (57568: two digits at DE+1,
DE+2) with decimal carry by hand. Magic below 0 → "00" and 56571.

## Routines

All preserve the registers they push; "O:" are outputs.

| addr | name | does | in / out, notes |
|---|---|---|---|
| 50100 | TitleTuneInit | title tune (sound area) | sets 50127/50131; 50113 is the per-frame step |
| 52180 | Entry | IM 2 table, border, key defaults | |
| 52235 | Restart | title, menu, attract, new game, main loop | SP=0 |
| 52430 | MainLoop | see above | |
| 52767 | (input) | `JP (57726)` with 52775 pushed | O:A controls; bit 6 restarts |
| 52920 | OutsideTick | outside countdown | A = (24012) |
| 52945 | PlacePlayer | slot 0 = type 1 at 61250[A] | A preserved |
| 52964 | DeathTick | death countdown, lose a life | |
| 53036 | ResetPlayerState | 24026-8=0; 24078=128, 24080/1=2 | |
| 53060 | RespawnRoom | death room → restart room | A in, A out |
| 53087 | Cls | zero 16385-23296 | 16384 is not cleared |
| 53101 | GameOver | tune 2, text 58515, wait fire, restart | |
| 53310 | GoOutside | the trip outside | A = map byte |
| 53408 | RoomExits | edge tests, re-enter | IX = slot 0, IY = map entry |
| 53534 | SetBorder | `OUT (254)` A AND 7 with 24006's bits 3-7 | doesn't update 24006 |
| 53550 | DrawPanel | lives, texts, score, magic, heads | 24035 = 6 |
| 53651 | HeadsTick | heads' animation step | HALTs |
| 53798 | HeadsSound | beep (52854) at 24001 | |
| 53823 | DrawHeadEyes | XOR frames A, A+3 on the heads | |
| 53858 | NewGame | zero 24000-25058, digits, items, magic, screen | 59582=252 |
| 53931 | ClearLines | B lines from line A | |
| 53949 | EnterRoom | draw room A | all registers preserved; 2 HALTs |
| 54213 | ClearPlayAttrs | HALT, attrs rows 4-23 = 0 | |
| 54229 | SpawnItem | item in slot 5 | |
| 54264 | SpawnMonsters | monsters in slots 2+ | 24042 = list |
| 54363 | PrintString | string HL at B, C | uses 24024 |
| 54464 | DrawChar | 8 bytes DE+8A to (B, C) | O:HL screen address; A, BC, DE kept |
| 54499 | ShowPlayAttrs | HALT, 768 bytes 24225 → 22656 | |
| 54513 | — | `CP 133 : RET Z`, then into the player code | player area |
| 56700 | RoomFlag | room's bit in 24054-24069 | O:A byte, C mask, HL address |
| 56729 | IsHeld | A in 24070-24076? | O:Z; BC, HL kept |
| 56794 | AllHeld | 24070-6 = 61514-20? | O:Z |
| 57058 | DrawObject | XOR pre-shifted sprite | A frame, B lines, C width, D y, E x, HL buffer |
| 57182 | DrawObjectColour | E −= 12, then 57194 | |
| 57194 | DrawSpriteAttr | XOR sprite and its colour | all registers kept |
| 57307 | LineAddr | HL = screen address of line A | A kept |
| 57326 | AttrUnder | O:A attribute under screen address HL | O:DE its address |
| 57341 | AttrAddr | HL = DE + cell offset of screen HL | A kept |
| 57355 | IsSpecial | A in the 9 bytes at 57808? (24010 = A) | O:Z |
| 57371 | ObjectSlot | IX = HL = 24077 + 20×A | |
| 57385 | Index4 | HL += 4×A | |
| 57395 | WordAt | HL = word at HL + 2A | A kept; A < 128 |
| 57408 | ByteAt | A = (HL + A) | O:HL the address |
| 57415 | PreShift | frame A to buffer HL, shifted for E | O:B lines, C width+1; DI/EI |
| 57520 | Divide | BC / DE (16-bit) | not seen called |
| 57546 | Multiply | HL = A × DE | DE is shifted on return |
| 57568 | SubMagic | magic −= DE+1, DE+2 digits; print | O:C ran out |
| 57616 | AddScore | score += digits at DE; print | |
| 57664 | Irq | the interrupt | |
| 57714 | IrqEffect | sound effect step | |

Not core but met: 52481 menu; 52610 wait for a key (redefine); 52658
Kempston reader; 52695 key-table reader (stored as data in auto.ctl);
52781 start a sound sequence (24003/24005); 52791 sound-sequence step;
52854 beeper tone; 55363 spawn object (slot A, DE = x/y, B type, C
flags; draws it); 55472 clear slots; 55783 object mover (the pacing).

## Variables (24000-25058, zeroed by 53858)

| addr | size | name | meaning |
|---|---|---|---|
| 24000 | 1 | sfxCount | sound effect frames left (interrupt) |
| 24001 | 1 | headPitch | heads' animation beep pitch |
| 24002 | 1 | irqTune | 0 none, 1 title, 2 game over, 3 win |
| 24003 | 2 | sndSeqPtr | sound sequence pointer (52781) |
| 24005 | 1 | sndSeqVal | sound sequence value |
| 24006 | 1 | portFE | last `OUT (254)` value |
| 24007 | 1 | attractCount | passes until the next credits page |
| 24008 | 1 | attractPage | 0/1 |
| 24009 | 1 | — | player area (B for 55624) |
| 24010 | 1 | — | last byte tested by 57355 |
| 24011 | 1 | roomBit | this room's bit in 24054 (nonzero if set) |
| 24012 | 1 | outsideCount | trip outside, passes left |
| 24013 | 1 | headDelay | passes before the heads animate |
| 24014 | 1 | — | player area |
| 24015 | 1 | fireTimer | counts down; at 0 clears 24016 |
| 24016 | 1 | — | XORed with input bits 2-3 (53221) |
| 24017 | 1 | canCast | non-zero: fire casts (set on item pickup) |
| 24020 | 1 | controls | this pass's controls byte |
| 24021 | 1 | — | object index (objects area) |
| 24022 | 1 | curSlot | object slot being drawn/spawned |
| 24024 | 1 | printAttr | attribute for 54363 |
| 24025 | 1 | moved | object moved this pass (55783) |
| 24026-8 | 3 | — | player motion state |
| 24029 | 1 | — | player input state |
| 24030 | 1 | room | current room |
| 24031 | 1 | — | flags (bits 2, 3 set by 56929/56939) |
| 24032 | 1 | headAnim | bit 7 start; low bits steps left |
| 24033 | 1 | headStep | delay between steps |
| 24034 | 1 | deathCount | dying, passes left |
| 24035 | 1 | lives | 6 at the start |
| 24038 | 1 | clipSkip | bytes clipped on the left |
| 24039 | 1 | clipLimit | bytes before the right edge (128 = none) |
| 24040 | 2 | — | player area pointer |
| 24042 | 2 | monList | this room's monster list |
| 24046 | 2 | — | 2650 at new game; never read |
| 24048 | 2 | — | 8384 at new game; never read |
| 24050 | 2 | savedSP | 57415's SP |
| 24052 | 2 | shiftBuf | 57415's buffer − 2 |
| 24054 | 16 | roomBits | a bit per room (meaning: objects/player area) |
| 24070 | 7 | held | ingredient types held |
| 24077 | 120 | slots | six object slots × 20 bytes; slot 0 the player |
| 24203 | 20 | savedPlayer | slot 0 kept over room entry |
| 24225 | 640 | attrBuf / spriteBuf0 | room attribute buffer; then new-image buffer |
| 24427 | | spriteBuf1 | old-image buffer |
| 24995 | ~40 | sink | off-screen line for clipped drawing |

Object slot bytes met: +1 flags (C at spawn; 128 for the player), +3
input bits, +6 x, +7 y, +8 x limit (139 − 4×width), +9 y limit (191 −
height), +10/+11 old x/y, +13 type (0 = empty), +15 frame, +16 old
frame, +17 width (bytes), +18 height, +19 respawn timer.

## Memory map, 23296-65535

| range | contents |
|---|---|
| 23296-23999 | system variables and the BASIC loader (not the game's) |
| 24000-25058 | variables, object slots, buffers (zeroed per game) |
| 25000-25069 | the machine-code loader (overwritten by the game) |
| 25070-25899 | zero in the snapshot; no reference found |
| 25900-34525 | sprite graphics (frames, 59798) |
| 34526-39653 | room tiles, 641 × 8 |
| 39654-43749 | blocks, 256 × 16 |
| 43750-48869 | room layouts, 128 × 40 |
| 48870-49510 | tile attributes, 641 |
| 49511-50022 | font, 64 × 8 |
| 50023-50099 | zero |
| 50100-57725 | code (with tune data; ~50100-52179 sound) |
| 57726-57871 | controls vector, key tables, font translation |
| 57872-58782 | texts: menu, key names, credits, panel, game over, win |
| 58784-58882 | key-name pointers, lives x, score/magic strings, deltas |
| 58883-58930 | character-row screen addresses (24 words) |
| 58931-59394 | pixel-line addresses for clipping (232 words) |
| 59395-59797 | objects area (pointer table and sequences) |
| 59798-60421 | sprite frame table (156 × 4) |
| 60422-60577 | sprite frame attributes |
| 60580-61141 | object types (objects area) |
| 61142-61249 | monster type choices, heads text, head frames, respawn and start rooms, random pointer (61248) |
| 61250-61505 | player start position per room |
| 61514-61520 | the seven ingredients to win |
| 61521-61676 | the 52 items: rooms, then positions |
| 61677-62953 | monster lists: pointers, then lists |
| 62954-63497 | tile-bank pointers and lists |
| 63498-64009 | room map, 128 × 4 |
| 64010-64018 | sound sequences (sound area) |
| 64019-64026 | interrupt tune table |
| 64027-64998 | not in this area (52854's tone table at 64027) |
| 65021-65023 | `JP 57664`, written at startup |
| 65024-65280 | IM 2 vector table, written at startup |
| 65281-65535 | stack (SP = 0) |

## The room oracle: `tools/zxrooms.py`

```
.venv/bin/python tools/zxrooms.py [rooms] [--full]
```

Starts a game from `build/c2.z80`, saves the in-game state, then per
room: reloads it, A = room, pushes a sentinel return address (23296),
jumps to 53949 and runs to 54154 (the scenery and its attribute copy
done). Writes `build/zxrooms/room_NN.scr` (6912 bytes, SCREEN$ layout),
`room_NN.png` and `contact.png`. Rows 4-23 depend only on the room;
rows 0-3 are the panel as the game drew it. `--full` runs to the
sentinel, so the player, the monsters and the item are drawn too (those
depend on the saved state). All 128 rooms take a few seconds.

## For the port

- The room format is compact and regular: the port can keep it as is
  (layouts, blocks, banks, tiles, attributes are 5120 + 4096 + 288 +
  5128 + 641 bytes of the original) and transcribe 53949 directly. The
  tile drawing is the only full-screen work, done once per room.
- Room drawing hides itself by zeroing the attributes first and copying
  them after a HALT; on the BBC the equivalent is drawing with the
  palette blanked, or off screen.
- The 2-pixel x step and 4 pre-shifts match MODE 1's 4 pixels a byte
  only partly: a Spectrum byte is 8 pixels; decision 2 of cauldron-beeb
  (the Spectrum's geometry in MODE 1) applies.
- The game's speed is set by the number of moving objects (one HALT
  each). To match the original's pace the port needs the same rule, or
  the measured frames per pass.
- Monster colour is XORed into the attributes and the logic reads
  attributes: keep the attribute shadow exact.
