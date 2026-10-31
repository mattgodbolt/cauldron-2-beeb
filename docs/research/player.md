# The player: controls, bounce, collision, exits, firing, death

Research on the Spectrum original (`build/c2.z80`), for transcribing to
6502. Every address is the original's, in decimal. Behaviour marked
*measured* was checked by running the original on SkoolKit's simulator
(`tools/zx.py` and Python on its `Spectrum` class), tracing the
variables once per main-loop pass; the scratch scripts are under
`build/research/pl/`. The control file is `disasm/player.ctl`.

## The shape of it

The pumpkin is **object 0** of a six-entry object table at 24077 (20
bytes each, see below). The player's code does not move it: each pass
the player physics (54530) decides a direction and a step size and
writes them into the object's fields, and the general object mover
(55783, shared with the monsters) applies them and redraws. The bounce
is a lookup-table "velocity" index, not a sum; collision is done by
testing **screen pixels** below/above/beside the sprite and then the
**attribute** of the byte the pixel was found in.

### Main loop (52430-52478), the per-pass order

```
52430  if (24034) death countdown running -> 52964 (skips to 52466)
52437  if (24012) warp countdown running  -> 52920 (skips to 52455)
52444  A = READ_CONTROLS (52767); (24020) = A
52451  CALL 53149   reversed-controls timer
52455  if (24020) bit 4 (fire): CALL 53163   fire a bolt
52463  CALL 54530   player physics
52466  CALL 55783   move, animate and redraw all 6 objects; collisions
52469  CALL 53408   room exits
52472  CALL 53651   panel witch animation (after death/warp)
52475  CALL 55285   monster respawn timers
52478  JP 52430
```

There is no frame lock in the loop: the pace comes from the work and
the `HALT` in the object drawer (56256, one per object drawn). One
"pass" is the unit of all timing below.

Two orderings matter to a transcription:

- The physics (54530) tests the screen **before** 55783 redraws the
  objects, so at that moment the screen holds every sprite at the
  position it was drawn last pass, XORed over the room.
- The physics computes this pass's step and its look-ahead checks
  against the *moved* position; 55783 then moves. A reversal found this
  pass (bits of 24028) takes effect at the start of the next pass.

## Controls

### Ports and keys

`READ_CONTROLS` (52767) pushes 52775 as a return address and jumps
through the pointer at 57726, so the reader returns into
`CHECK_ABORT` (52775), which jumps to the menu (52235, which resets SP)
if bit 6 is set, else returns. Result in A:

| bit | value | meaning |
|-----|-------|---------|
| 0 | 1 | up |
| 1 | 2 | down |
| 2 | 4 | left |
| 3 | 8 | right |
| 4 | 16 | fire / bounce |
| 6 | 64 | abort game |

The direction bits are the same encoding as an object's direction
byte (IX+3), which is why the code can copy them across. (Checked
against the code: KEMPSTON_MAP 57744 is `0,8,4,0,2,10,6,0,1,9,5,0,...`,
so the port's R=1 L=2 D=4 U=8 become 8, 4, 2, 1; core.md's "bit 0
right, 1 left, 2 down, 3 up" is the Kempston port's order, not the
controls byte's.)

- **Kempston** (`READ_KEMPSTON`, 52658; selected by menu 1): `IN A,(31)`,
  the low nibble (R=1, L=2, D=4, U=8) looked up in `KEMPSTON_MAP`
  (57744, 16 bytes) which remaps it to the bits above and maps L+R and
  U+D to 0 in each axis; fire is Kempston bit 4 passed through. Abort:
  port 65022 (half-row A-G) read, and bit 6 set only if the value
  (inverted, `AND 31`) is exactly 1, i.e. **A alone**. Preserves BC, DE;
  HL is left pointing into the table.
- **Interface II / keyboard** (`READ_KEYS`, 52695; menu 2 or 3). This is
  code, but the executed-code maps marked it as data (it is only
  reached through 57726). It walks six 4-byte entries at `KEYS` (57784):
  port low, port high, key mask, result bit; each pressed key ORs its
  result bit in. Then left+right pressed together cancel (both bits
  cleared), and up+down likewise. Preserves IX, DE, BC.
- `DEFAULT_KEYS` (57760) holds the Interface II defaults; the entry
  code (52218) and menu 2 (52520) copy them to `KEYS`:

  | entry | port | mask | key | bit |
  |---|---|---|---|---|
  | UP | 61438 (&EFFE) | 2 | 9 | 1 |
  | DOWN | &EFFE | 4 | 8 | 2 |
  | LEFT | &EFFE | 16 | 6 | 4 |
  | RIGHT | &EFFE | 8 | 7 | 8 |
  | FIRE/BOUNCE | &EFFE | 1 | 0 | 16 |
  | ABORT GAME | 65022 (&FDFE) | 1 | A | 64 |

- Menu 3 (52538) redefines all six, prompting `UP`, `DOWN`, `LEFT`,
  `RIGHT`, `FIRE/BOUNCE`, `ABORT GAME`; it overwrites only the port and
  mask of each entry, so the result bits keep the order above.
  52610 scans the eight half-rows at 57728 and waits for a key press
  then release, each debounced by 256 consecutive identical reads.
- The pointer 57726 initially holds 52695 (keyboard), so with no menu
  choice the keyboard reader with the Interface II keys is in force.

### What each control does in play

- **Left/right** are read **only at the moment of landing** (in
  `LANDED`, 53221): they set the horizontal direction for the whole of
  the next bounce. Holding a direction mid-air does nothing. No
  direction at landing means bouncing straight up and down.
- **Up/down** do nothing to the pumpkin's movement. They only aim the
  bolt (firing takes all four direction bits).
- **Fire** has two jobs, both from the one button:
  1. Held at the landing pass it raises the bounce level by one (see
     *The bounce*). The menu calls it FIRE/BOUNCE.
  2. Pressed with any direction, it fires a bolt in that direction (if
     firing is enabled; see *Firing*).
- **Reversed controls**: `(24016)` is XORed with the controls' left/right
  bits at landing. A collision handler (56636, objects area) sets
  `(24015)=50, (24016)=12` unless item 29 is carried; `TICK_REVERSE`
  (53149) counts 24015 down once per pass and clears 24016 at zero.
  While reversed, *no key* gives bits 12 = left **and** right: the
  object mover then applies X-dx and X+dx, so the pumpkin stays put
  horizontally (measured), and only the right-hand wall check runs.

For the BBC: Z/X give left/right (bits 4/8), `:`and `/` up/down (bits
1/2, which only aim the bolt), RETURN fire (bit 16). Abort needs a key
of its own (the original's is A).

## Coordinates

- **Y**: screen pixel row, 0 at the top of the Spectrum screen, of the
  sprite's top row. The sprite covers rows Y .. Y+h-1, h = IX+18 (13 for
  every pumpkin frame). Rows 0-31 are the panel; collision tests only
  rows in 33..190 (see below).
- **X**: in **double-pixel units, offset by 12**: screen pixel =
  2*(X-12). So X=12 is the left edge of the screen, and one screen byte
  holds four X units ((X-12)>>2 is the byte column, (X-12)&3 the pair
  within it; `PIXEL_MASKS`, 61158 = 192, 48, 12, 3). This is the C64
  version's multicolour geometry showing through. The sprite drawer
  (57415) also does `SUB 12 : SLA A : AND 7` for the bit shift.
- Width: IX+17 in character cells (2 for the pumpkin), so the pumpkin
  spans X .. X+7 (4 units per cell).
- `ROW_ADDR` (57307): A = pixel row -> HL = screen address of column 0
  of that row, from the 24-entry row table at 58883 plus (A AND 7) in H.

## The player's variables

### Object 0, at 24077 (IX = 24077 throughout the player code)

The same 20-byte layout as every object; fields the player uses:

| off | addr | name | meaning for the player |
|---|---|---|---|
| +0 | 24077 | timer | script step timer; 0 for the player |
| +1 | 24078 | script | 128 = "steered by the player code" (set by 53036 and 54193). 55783 skips the script and just applies +3/+4/+5 when it is negative. |
| +2 | 24079 | script pos | unused for the player |
| +3 | 24080 | dir | direction bits: 1 up, 2 down, 4 left, 8 right |
| +4 | 24081 | dx | horizontal step per pass, X units: always 2 (53036) |
| +5 | 24082 | dy | vertical step this pass, rows: written by the physics each pass |
| +6 | 24083 | X | see Coordinates |
| +7 | 24084 | Y | see Coordinates |
| +8 | 24085 | Xmax | 139 - 4*width (written per frame by 55916) |
| +9 | 24086 | Ymax | 191 - height |
| +10,11 | 24087 | oldX, oldY | where it was last drawn (for the XOR erase) |
| +12 | 24089 | anim delay | frames-per-step countdown |
| +13 | 24090 | state | animation state (below); bit 7 = animation ended |
| +14 | 24091 | anim pos | index into the state's animation list |
| +15 | 24092 | frame | sprite frame to draw |
| +16 | 24093 | old frame | frame last drawn |
| +17 | 24094 | width | cells, from the frame table 59798 |
| +18 | 24095 | height | rows, from the frame table |
| +19 | 24096 | respawn | (monsters only) |

Animation states (table 60580, word per state -> `[delay, frame...,
255 n (loop to n) | 254 (end: set bit 7) | 253 n (kill)]`):

| state | frames | use |
|---|---|---|
| 1 | 0-5, looping | normal bounce |
| 2 | 15, 6-13 looping | after a left-wall hit, or landing with 24031=4 |
| 3 | 15, 13-6 looping | after a right-wall hit, or landing with 24031=8 |
| 4 | 14 once, then ends (state 132) | squash on landing |
| 5 | 23-30 then kill | death explosion; also sets (24000)=50, the interrupt's death warble |
| 33 | shrinking frames | the warp (see *Room exits*) |

States 2 and 3 loop, so after a wall hit the state stays 2/3 until the
next landing.

### Player variables in 24000-24060

| addr | name (mine) | meaning |
|---|---|---|
| 24000 | death_sfx | IM 2 handler (57696) beeps while nonzero; 55624 sets 50 on state 5 |
| 24009 | land_state | animation state to resume after the squash: (24031>>2)+1 = 1, 2 or 3 |
| 24010 | last_attr | 57355 stores the attribute it tested (no reader found in my area) |
| 24012 | warp_timer | passes left of the warp interlude (105); physics, fire and exits idle while nonzero |
| 24013 | panel_delay | delay before the panel witch animation (53651) |
| 24014 | hit_attr | attribute under the centre of the feet/head at the last vertical pixel hit (written even when not solid); 1 = deadly on landing; zeroed on death |
| 24015 | rev_timer | reversed-controls countdown (passes) |
| 24016 | rev_mask | 12 while reversed, else 0 |
| 24017 | can_fire | nonzero once the item that enables firing is picked up (56747 handler, which also refills magic); 0 at the start of a game |
| 24020 | controls | this pass's control bits |
| 24026 | v | bounce "velocity" index 0..9 into `STEP_ROWS` |
| 24027 | level | bounce level 0..2 in bits 0-1; bit 7 = fire was held at the last landing |
| 24028 | flip | bit 0: landed (flip vertical next pass); bit 1: hit ceiling or reached the peak (flip vertical); bit 2: hit a wall (flip horizontal) |
| 24029 | land_dir | direction to resume after the squash |
| 24030 | room | current room (0-127) |
| 24031 | edge | set by the feet test: 8 = only the left foot is on something solid (roll right), 4 = only the right foot (roll left); also set by two collision handlers (56930: bit 3, 56939: bit 2, objects area) |
| 24034 | death_timer | passes left of the death sequence (70) |
| 24035 | lives | 6 at the start (53550); game over when it would go below 0 |
| 24040 | row_addr | screen address of the row being tested (word) |
| 24203 | saved player | 20-byte copy of object 0 kept across a room redraw (53949) |

Others the player touches: 58813-58814 the MAGIC % as two ASCII
digits; 59450 the bolt script's direction byte (self-modified).

## The bounce

### Tables

- `STEP_ROWS` (61145): `1,1,2,4,5,8,8,10,10,10`, indexed by v: rows to
  move (at most) this pass.
- `LAUNCH_V` (61155): `4,6,9`, indexed by level: v at take-off.
- The same three bytes double as the thresholds for recomputing the
  level from v in flight.

### Going up (`MOVE_UP`, 55131), dir bit 0

1. B = STEP_ROWS[v]. Test rows Y-1, Y-2, ... Y-B for a hit (`TEST_ROW`,
   54970). E counts rows tested.
2. **Hit on the k-th row** (row Y-k): dy = k (*not* k-1: the sprite's top
   moves onto the ceiling row, overlapping it by one; measured), set
   24028 bit 1, dir = (dir AND 12) OR 1. v is left as it is, so the fall
   starts at that speed.
3. No hit: dy = B, 24031 = 0, dir = (dir AND 12) OR 1, v = v-1 (not below
   0). If v is now 0, set 24028 bit 1 (peak). Else level (bits 0-1 of
   24027, bit 7 kept) = 2 if v >= 9, 1 if v >= 6, else 0.
4. Then the wall test at the moved position (`TEST_WALLS`, 54799 with
   A = Y - dy + 7).

### Going down (`MOVE_DOWN`, 54631), dir bit 1

1. B = STEP_ROWS[v]. Test rows Y+h, Y+h+1, ... Y+h+B-1.
2. No hit: dy = B; v = v+1 (not above 9).
3. **Hit on the k-th row**: if 24014 = 1 -> death (56571). Else 24028
   bit 0, dy = k-1 (the sprite comes to rest just above the hit row),
   state 4 (squash, 55624), 24009 = (24031>>2)+1, start the bounce
   sound (52781 with 64010). v is not incremented.
4. Either way: dir = (dir AND 12) OR 2; level = 0 if v <= 4, 1 if
   v is 5-6, 2 if v >= 7 (bit 7 kept).
5. Then the wall test with A = Y + dy + 7.

### Neither (dir has no vertical bit)

Only after the reset with state 0; the wall test runs with A = Y.

### Landing (`LANDED`, 53221), every pass while state = 4

The squash frame lasts one pass. On it:

- Fire held: level = min(level+1, 2), bit 7 set.
- Fire not held: if bit 7 set, clear it (level kept); else level =
  max(level-1, 0).
- v = LAUNCH_V[level].
- land_dir (24029) = (old dir AND 3) OR 24031 OR ((24016 XOR controls)
  AND 12). Old dir AND 3 is "down", flipped to "up" next pass.
- dir = 0, 24031 = 0, bounce sound.

When the squash ends (state 132), `PLAYER` (54513) sets the state to
24009 and dir to 24029, then runs the flips: 24028 bit 0 turns down into
up, and the pumpkin takes off.

So the height of a bounce depends on the speed of the fall before it:
falling from high up lands at level 2 and, without fire, bounces back
at level 1, then 0. Fire on landing adds a level up to 2.

### Measured trajectories (rows risen per pass, from the floor)

| level | v at take-off | steps up | height | passes up+down on a flat floor |
|---|---|---|---|---|
| 0 | 4 | 5, 4, 2, 1 | 12 | 10 (incl. the squash pass) |
| 1 | 6 | 8, 8, 5, 4, 2, 1 | 28 | |
| 2 | 9 | 10, 10, 10, 8, 8, 5, 4, 2, 1 | 58 | |

Falling: 1, 1, 2, 4, 5, 8, 8, 10, 10, 10, 10... (v = 0, 1, 2, ...).
With fire held on the start platform the pumpkin rose from Y=107 to 49
(58 rows), measured; at level 1 to 79 (28).

Horizontally the pumpkin moves dx = 2 units (4 pixels) every pass it
has a horizontal bit, in the air or not; on the squash pass dir is 0, so
it stops for that pass.

### Flips (start of `PLAYER`, 54557)

If 24028 bit 0 or 1: dir XOR 3 (swap up/down), clear both bits. If bit 2:
dir XOR 12 (swap left/right), clear it. These run only when the state is
not 4 or 5.

**Quirk (measured):** if a wall is hit on the same pass as a landing,
the wall's `55624` call sets state 3 over state 4, so there is no
squash: next pass both flips apply and the pumpkin goes back up at the
landing speed v with no level adjustment, its direction reversed.

## Collision with the scenery

All tests read the Spectrum bitmap and attributes directly.

### `TEST_ROW` (54970): the feet / head test on one row

In: HL = address of column 0 of the row tested, C = a row number used
only for the range test, IX = object. Out: NZ = blocked. It clobbers
A, B, DE, HL; the callers push BC, DE, HL around it.

1. If C >= 191 or C < 33: return Z (nothing). Note C is the tested row
   +1 going down (`MOVE_DOWN` does INC C before the call, HL is one row
   behind) and the tested row -1 going up.
2. Store HL at 24040.
3. **Centre**: X units X+3, X+4, X+5 (`TEST_UNITS`, 55095). If any is
   set: 24014 = its attribute; if the attribute is solid, return NZ.
4. 24031 = 0. If X >= 12: **left foot** X+1, X+2 solid -> 24031 |= 8.
   **Right foot** X+6 solid -> 24031 |= 4. (X+0 and X+7 are never
   tested.) X < 12 skips both feet, not just the left (55019 jumps to
   55082).
5. 24031 = 0 -> return Z. 24031 = 12 (both feet, no centre) -> clear it,
   return Z: the pumpkin passes between them. 24031 = 4 or 8 -> return
   NZ: a hit "on the edge", which at landing makes the next bounce
   roll off that edge (land_dir gets the bit; land_state 2 or 3).

Quirk: on an edge hit, 24014 still holds the attribute from the last
time a centre pixel was found, so a stale 1 there could kill on a
landing that is on something else. Preserve it.

### `TEST_UNITS` (55095)

In: A = first X unit, B = count, (24040) = row address. For each unit
(X-12 must be 0-127, else skipped): byte (X-12)>>2, mask
PIXEL_MASKS[(X-12)&3]; if `(byte) AND mask` is nonzero return NZ with
HL = that screen byte's address. Else Z. A unit is two pixels: either
lit counts.

### `TEST_COLUMN` (54906): the wall test on one column

In: A = X unit, B = 5 rows, C = first row, (24040) = its address. For
rows C .. C+4 (stopping if the row is >= 191 or < 33): if the pixel pair
is set return NZ with HL = the byte. Out-of-range X (X-12 not 0-127)
returns Z.

### `TEST_WALLS` (54799 / 54807)

A = the row to start from (moved Y + 7, the middle of the sprite).
`ROW_ADDR` -> 24040. Then:

- dir bit 3 (right): `TEST_COLUMN` at X + dx + 8 (the first unit right
  of the sprite after the move).
- else dir bit 2 (left): at X - dx - 1.
- A pixel found and its attribute solid: 24028 bit 2, state 3 (right
  wall) or 2 (left wall), bounce sound.

Measured: a wall at unit 30, pumpkin moving right from X=20: the move to
22 happens (22+7 = 29, touching), the flip comes next pass.

### Attributes: `ATTR_AT` (57326) and `IS_SOLID` (57355)

`ATTR_AT`: HL = a screen byte address -> DE = its attribute address
(`(H>>3 AND 3) OR 88`, L), A = the attribute. DE is clobbered.

`IS_SOLID`: stores A in 24010, then `CPIR` for A in the nine bytes at
`SOLID_ATTRS` (57808). Z = solid. Preserves HL, BC and A.

`SOLID_ATTRS` = **65, 66, 67, 68, 69, 7, 1, 6, 12** (constant; nothing
writes it):

| attr | colour |
|---|---|
| 65-69 | bright blue, red, magenta, green, cyan ink on black |
| 7 | white ink on black (not bright) |
| 1 | blue ink on black (not bright): **water: solid, and deadly when landed on** |
| 6 | yellow ink on black (not bright) |
| 12 | green ink on blue paper |

Everything else is passable even where pixels are lit: bright yellow
(70) and bright white (71) scenery, for instance (the fruit on the first
room's table is 70 and is passed through; measured). The death test is
`hit_attr = 1` on the landing path only: water hit from below or from
the side is just a wall (measured, by drawing a line with attribute 1).

Why the port must shadow the attributes and the 1-bit pixels: the
solidity of every lit pixel is decided by the attribute of its
character cell, and the pixels include the **sprites currently drawn**
(XORed, from last pass). A monster or the bolt whose cell attribute is in
the list is solid to the pumpkin for that pass; an XORed sprite over a
platform can also erase the platform's pixels. To match the original
the port's tests need (a) a bitmap with the Spectrum's lit pixels as
they are at 54530, sprites included, and (b) the attribute bytes exactly
as the original's, including the attributes the sprite drawer writes
(57194's `OR 88` path).

## Room exits (`CHECK_EXITS`, 53408)

Runs after the objects moved, unless the death timer runs. IY = `EXITS`
(63498) + 4*room: four bytes, **left, right, down, up**. The map is a
grid 8 rooms wide (97: left 96, right 98, down 105, up 89).

| test (in order) | exit | new position |
|---|---|---|
| X <= 8 | IY+0 (left) | X = 135 |
| X >= 136 | IY+1 (right) | X = 9 |
| Y <= 27 | IY+3 (up) | Y = 200 - h |
| Y + h >= 201 | IY+2 (down) | Y = 28 |

then `CALL 53949` with A = the new room. Only one exit per pass; X is
tested first. 53949 (draw room, graphics area) saves object 0 to 24203,
clears the objects (55472), draws the room, restores object 0, sets
IX+1 = 128 and spawns the room's monsters (54264, 54229). The player's
v, level, dir and state carry over: a bounce continues across the edge
(measured: room 97 -> 96 at X=8, reappearing at X=135, same v).

An exit byte >= 128 is not a room: it goes to `WARP` (53310) with the
room = byte AND 127. In the table these are 245 (-> room 117) and 238
(-> 110), on the outer edges of the map. `WARP`:

- room = byte AND 127; clear the play area's attributes (rows 4-23) and
  objects; clear 160 pixel rows from row 32; set the play area's
  attributes to 70; spawn object 0 at X=76, Y=100 with script 1 and
  state 33 (the pumpkin shrinks to a dot; screenshots
  `build/research/pl/warpb.png`);
- 24013 = 10, 24032 = 143 (the panel witches), 24012 = 105.
- 105 passes later (52920): clear the attributes, place the player at
  the room's start (52945), draw the room (53949), reset the physics
  (53036). Measured: room 117 at X=40, Y=128, falling.

`START_POS` (61250, two bytes per room: X, Y) is the position 52945
uses on a warp, after a death, and at the start of a game (room =
61240[random AND 7], one of 56, 10, 97, 79, 37, 70, 110, 107).

`RESET_PHYSICS` (53036): 24026 = 24027 = 24028 = 0, dir = 2 (down),
dx = 2, script = 128.

## Firing (`FIRE`, 53163)

Called when the controls have bit 4. Returns without firing if: the
warp runs; 24028 bit 0 (the landing pass); `can_fire` (24017) is 0;
no direction is pressed; or object 1 (the bolt) is busy (its script
byte 24098 is 1-127). Otherwise:

1. (59450) = controls AND 15: **self-modifies** the first step of
   script 2 (59450: `dir, 10, 7, 7` then 253 = die).
2. Spawn object 1 at the player's X, Y with script 2 and state 32
   (55363): it moves 7 units (14 pixels) and 7 rows per pass in the
   pressed direction(s), for 10 passes, then disappears.
3. Magic -1 (57568 with 58880: the two digits 0, 1). If the magic goes
   below 0 it is set to 00 and the player dies (56571).

Measured (24017 poked to 1): one bolt at a time; MAGIC 99 -> 98. With
24017 = 0, as at the start of a game, fire only affects the bounce.
`can_fire` is set by the pickup handler at 56747 (an item from the
52-room list at 61521, which is also marked collected), which also
resets the magic to 99.

## Death and losing magic

- `KILL_PLAYER` (56571): state 5 (explosion; 24000 = 50 for the death
  warble), 55512 stops the object (dir, dx, dy, script = 0), 24034 = 70,
  24013 = 20, 24032 = 143 (panel witches), 24014 = 0.
- Causes: landing on attribute 1 (54751); magic underflow (57602); a
  monster whose collision flags have bit 7 (56362).
- While 24034 counts down (52964) input, fire and physics are skipped.
  At 0: lives - 1 (game over at 53101 if it goes negative); a life
  pumpkin in the panel is XORed away (positions 58796); magic reset to
  99; if all seven items are carried (56794) the respawn room is
  remapped via 61232/61236; player placed at `START_POS[room]`; room
  redrawn; physics reset. Measured: died in the water of room 117, came
  back 70 passes later at that room's start, lives 6 -> 5.
- Touching a monster (56310, objects area): flags from 61065[monster
  state]. Bit 7 kills, bit 6 is a pickup, bit 5 a special handler via
  61120 (reverse controls, push via 24031, ...), bit 4 harmless;
  otherwise the monster explodes, its score is added and **MAGIC -8**
  (58841). Measured: 98 -> 90 on hitting a bat.
- The overlap test (56967): |dX| < 4 * width and |dY| < height, using
  the width/height of whichever object is further left/up.

## Sound hooks in my area (for the sound research)

- `SFX_START` (52781): HL = an effect (64010 for bounces), stores it in
  24003, first pitch in 24005, under DI.
- `SFX_STEP` (52791): called once per object per pass (6 times) from
  55801; steps the effect: entries `[start, end, step]`, 255 ends.
  Calls `BEEP` (52854), which self-modifies a jump into a run of NOPs
  (52888) for the waveform.
- 64010: bounce/wall `20, 30, 2, 255`.

## Things to keep in the transcription

1. The pixel tests read the real bitmap with sprites XORed in, and the
   attributes; see *Attributes*. Both shadows must be the original's.
2. The off-by-ones: TEST_ROW's range test uses the row +-1; up hits
   overlap the ceiling by one row, down hits stop one short.
3. Left/right only at landing; reversed controls with no key give
   bits 12.
4. A wall on the landing pass cancels the squash.
5. Stale 24014 on edge landings.
6. Exits use X <= 8, X >= 136, Y <= 27, Y + h >= 201 in that order.
7. The bolt's direction is a self-modified script byte (59450).
8. `READ_KEYS` is code that the executed-code maps miss.
