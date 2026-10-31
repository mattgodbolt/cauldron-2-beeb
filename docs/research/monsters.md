# Monsters, objects and the rules

Research on the Spectrum original (entry snapshot `build/c2.z80`), for
transcribing to 6502. Addresses are decimal. The control file is
`disasm/monsters.ctl`; `sna2skool.py -c disasm/monsters.ctl build/c2.z80`
gives the labelled listing.

Everything marked *measured* was run on SkoolKit's simulator (scratch
scripts poked the inventory, entered rooms by calling 53949 from the main
loop's top at 52430, and read memory back). Screenshots are under
`build/research/m_*.png`.

## The game in one paragraph

The pumpkin starts in one of eight rooms (random), with 6 spare lives
and MAGIC 99. It must collect seven items around the 128 rooms and touch
the cauldron in room 127. With all seven, "WELL DONE ... THE WITCH IS
DEAD / LONG LIVE THE WITCH" (measured, `m_end1.png`); without them the
cauldron kills it. Touching an ordinary monster kills the monster
(score, MAGIC -8); some things are deadly; some need an item to pass.
The pumpkin can fire only after it has taken one of the 52 magic
refills; each shot costs MAGIC 1. MAGIC below 0 kills it. There is no
lock-of-hair step in the code: the scissors are just one of the seven
items.

## The object engine

### Slots

Six slots of 20 bytes at 24077 (`Slots`): slot 0 the pumpkin, slot 1 its
shot, slots 2-5 the room's monsters and objects. Room-list entry *i*
lives in slot 2+*i*; the magic refill, when a room has one, goes in
slot 5 (no room with a refill has four list entries: measured over the
tables, the four-entry rooms are 56 and 79).

| off | name | meaning |
|---|---|---|
| +0 | count | passes left of the current movement command |
| +1 | move | movement script number; 0 none; bit 7 = moved elsewhere (the pumpkin has 128, its movement is another area's) |
| +2 | moveidx | index of the next 4-byte movement entry |
| +3 | dir | direction bits: b0 up (y-), b1 down (y+), b2 left (x-), b3 right (x+); 252 = chase the pumpkin |
| +4,+5 | xspd, yspd | per-pass step |
| +6,+7 | x, y | position. x is in 2-pixel units, screen byte column = x/4-3 (x=12 is column 0), pixel shift 2*(x mod 4); y in lines from the screen's top |
| +8,+9 | xmax, ymax | 139-4*width, 191-height (55363 computes 140-4w-1, the same) |
| +10,+11 | drawn x, y | where the sprite on screen is |
| +12 | adelay | passes until the next anim step |
| +13 | anim | anim number; 0 = slot empty; bit 7 = anim stopped (254) |
| +14 | aidx | index into the anim script |
| +15 | frame | sprite frame (index into 59798, 4 bytes per frame: width bytes, height, data pointer) |
| +16 | drawn frame | |
| +17,+18 | width, height | of the current frame; set only by an anim step (55916), so stale after a spawn until the first step |
| +19 | respawn | passes until the respawner (55285) brings it back |

Slot 0 is saved to 24203-24222 while a room is built (53949).

### Per pass

The main loop (52430-52478) calls, in order: input (52767) and the
pumpkin's own movement (54530) unless dying or teleporting, then
`ObjectsTick` 55783, the room-exit test 53408, `CackleTick` 53651 and
`Respawn` 55285.

`ObjectsTick` (55783), for slots 0-5, with `CurSlot` (24022) = slot and
IX = slot:

1. `RedrawFlag` (24025) = 0; step the sound effect (52791, another
   area: it runs once per slot, six times a pass).
2. **Anim.** If +12 is nonzero, decrement it and skip. If +13 is 0 or
   negative, skip. Else +12 = script byte 0 (the delay), +14 += 1, read
   script[+14]:
   - 255 n: +14 = n and read again (so the next frame is script[n+1]);
   - 254: +13 |= 128 (stopped);
   - 253 n: remove the object: +19 = n, clear +13, +12, +1, XOR the
     drawn sprite off, go straight to the next slot (no movement);
   - else a frame: +15 = frame, +8/+17/+9/+18 from its size,
     `RedrawFlag` = 1.
3. **Movement.** If +0 is nonzero, decrement and apply +3. Else if +1
   is 0, go to draw; if negative (the pumpkin), apply +3. Else read the
   4-byte entry at script + 4*(+2):
   - 255 n: +2 = n, read again;
   - 254: +1 = 0 (script over);
   - 253 n: remove as above (n is the entry's second byte);
   - 251 a: `SetAnim`(slot, a), +2 += 1, and restart this slot from
     step 1 (the sound step runs again);
   - else +3 = dir, +0 = count, +4 = xspd, +5 = yspd, +2 += 1, apply.
   An entry with count n is applied n+1 passes.
4. **Apply.** `RedrawFlag` |= +3. Bounds: slots 2-5 x in 12..+8, y in
   33..+9; slots 0-1 x 3..248, y 8..211 (in effect none: the exit test
   catches the pumpkin first). 252: the direction is `ChaseDir` (55745):
   right/left and down/up toward the pumpkin's x, y at 24083/24084,
   nothing on an axis where they are equal; it is not stored in +3.
   Then each set bit moves by the speed, clamped (56137 up, 56160 down,
   56178 left, 56196 right; the clamps are min/max of the bounds above).
5. **Draw** (56214). If `RedrawFlag` is 0: spin 1024 times round
   `DEC BC: LD A,C: OR B: JR NZ` and go on. Else build the new frame at
   the new position into the buffer at 24225 and the old one at the
   drawn position into 24427 (57415), `EI: HALT`, XOR old then new on
   (57058), record +16, +10, +11, then `Overlap` (56967); if it hits,
   `Collide` (56310) with A = the other slot.

**Timing.** Every slot that changes waits for a frame interrupt, so a
pass takes about one frame per changing slot (measured: 3-5 frames a
pass in room 97 with three monsters). The spin loop balances slots that
don't change. This is the game's speed governor and wants porting as a
decision, not by accident.

### Collisions

`Overlap` (56967) tests IX against slots 2-5 with +13 nonzero, skipping
itself: overlap when |dx| < 4 * width of the one with the smaller x and
|dy| < height of the one with the smaller y (strict). It returns NZ and
A = the first slot hit (lowest number). The pumpkin and its shot never
test against each other; monsters test against monsters but `Collide`
ignores those (it acts only when `CurSlot` is 0 or 1).

`Collide` (56310), A = other slot, does nothing during a teleport
(`TeleTimer` 24012 nonzero). Sets `OtherSlot` (24021), IX = other. The
other's type is `ObjTypes`[anim AND 127] (61065, one byte per anim
0-54).

The pumpkin (slot 0), skipped if its anim is 0 or 5 (exploding), or the
other's anim AND 127 is 0:

| type | effect |
|---|---|
| bit 7 | `KillPumpkin` (56571) |
| bit 6 | item: inventory slot = bits 3-5; `GiveItem`, remove it, +1000, pickup sound (sfx 64014 via 52781) |
| bit 5 | handler (bits 0-3) through the jump table at 61120 |
| bit 4 | nothing |
| else | monster: score `ScoreTable`[bits 0-3], it explodes (anim 5) and stops, MAGIC -8 |

The shot (slot 1):

| type | effect |
|---|---|
| bit 7 | the shot is removed |
| bit 6, bit 4 | nothing (passes through) |
| bit 5 | handler 0 (anim 11): killed as a 100-point monster; other handlers: nothing |
| else | explodes and stops, scores bits 0-3, the shot is removed |

A shot kill does not cost MAGIC.

### Handlers (61120)

| # | addr | anims | effect |
|---|---|---|---|
| 0 | 56601 | 11 | explodes, +100, MAGIC -8; unless item 29 (goblet) is held, left/right reverse for 50 passes (`ReverseTimer` 24015=50, `ReverseMask` 24016=12, measured) |
| 1 | 56647 | 8, 31 | deadly unless item 13 (shield) is held (measured both ways) |
| 2 | 56672 | 35 | becomes anim 24, room marked done |
| 3 | 56683 | 39 | becomes anim 16, room marked done |
| 4 | 56656 | 37 (door) | with item 28 (key): becomes anim 30 (opening), room marked done (measured: `RoomDone` bit set, anim 30). Without the key nothing happens here (whether the door blocks the pumpkin is the movement area's, not checked) |
| 5 | 56747 | 32 | magic refill: 61521 entry gets bit 7 (gone for this game), `CanFire` (24017) = room OR 128, removed, MAGIC = 99, +100 (measured) |
| 6 | 56811 | 26 (cauldron) | all seven items: +100, ending tune 51400, ending text, wait for fire, restart at 52235. Else death (measured both) |
| 7 | 56871 | 44 | if item 34 (scissors) is held and item 7 not: `GiveItem`(3), +1000, pickup sound. The object stays (measured) |
| 8 | 56901 | 27 (crown) | `GiveItem`(2), removed, **pokes 59582 = 0** (movement script 8's direction, 252 chase, becomes 0: the room-10 guardian, anim 45 on script 8, stands still), +1000 |
| 9 | 56929 | 24, 36, 41 | once its anim has stopped (0 or bit 7), `PushBits` (24031) bit 3: push the pumpkin right |
| 10 | 56939 | 16, 40, 42 | the same, bit 2: push left |

`PushBits` is ORed into the pumpkin's direction by 53221 (another area)
and cleared there.

"Room done" is a bit per room in `RoomDone` (24054-24069): byte
24054+room/8, bit 128>>(room AND 7) (`RoomDoneBit` 56700, set by 56694).
It is read at room entry (54264) for the fixed objects, below.

### Spawning and respawning

Room entry (53949, mostly another area) clears the slots (`ClearSlots`
55472), then 54264: `RoomList` (24042) = word 61677+2*room; 24011 =
this room's done bit; for each entry, slot 2, 3, ...:

- 4 bytes x, y, move, anim: spawn it;
- 3 bytes x, y, 128+k: a fixed object, move 0, anim 61142[k AND 3]
  (k 0: 35, 1: 37 the door, 2: 39), plus 1 if the room is done
  (so an opened door comes back as anim 38, open);
- in both cases skipped if the anim is held in the inventory
  (`HaveItem` 56729): collected items don't come back. (The anim number
  is checked for every entry, not only items.)

Then 54229: if the room is in `MagicRooms` (61521, 52 bytes, bit 7
clear), the refill appears in slot 5 at `MagicPos` (61573 + 2*index; E=x,
D=y) as anim 32, move 0. The fixed-up 61521 bits are cleared at game
start (53858).

`Respawn` (55285), every pass unless teleporting: for each 4-byte entry
*i* with slot 2+*i*'s +19 nonzero, decrement it; at 0, `Spawn` it again
from the list. Fixed objects never respawn. +19 is set by the 253 n
command: the explosion (anim 5) ends `253,30`, so a killed monster is
back 30 passes later (measured: +19 counting down after a kill); a shot's
script ends `253,0` and never respawns (slot 1 is not respawned anyway).

### Routines that callers rely on

| routine | in | out / effects | preserves |
|---|---|---|---|
| `Spawn` 55363 | A slot, E x, D y, C move, B anim | slot set up and drawn; `CurSlot` = A (!); B = the frame's lines, C = 4 x its width | AF, DE, IX; HL corrupted |
| `ClearSlots` 55472 | | | IX; A, B, DE corrupted |
| `StopSlot` 55512 | A slot | +0..+5 = 0 | all |
| `RemoveSlot` 55551 | A slot | stopped, anim 0, sprite erased; +19 untouched | all (and `CurSlot`) |
| `SetAnim` 55624 | A slot, B anim | anim restarted (no draw); slots 2-5 clamped to x<=134, y<=170; B=5 sets `SndExplode` (24000)=50 | all |
| `ChaseDir` 55745 | IX | A = direction bits | BC |
| `HaveItem` 56729 | A anim | Z if held | BC, HL |
| `HaveAllItems` 56794 | | Z if 24070-24076 = 61514-61520 | |
| `RoomDoneBit` 56700 | | HL byte, A its value, C bit | |
| `GiveItem` 56521 | A inventory slot | Inventory[A] = 61514[A]; the item's first frame drawn at (61507+A, y 61506) with 57194 | |
| `Overlap` 56967 | IX | NZ and A = slot | |

`Spawn` and `RemoveSlot` set `CurSlot` because the sprite drawer (57058)
reads it to pick its clipping (slots 0-1 one way, 2-5 another).
`RemoveSlot` restores it; `Spawn` does not.

No IY tricks in this area beyond IY walking the room list (55285) and
the slots (56967). No self-modifying code; self-modified **data**:
59450 (the shot's direction, poked by 53163 from the input), 59582
(handler 8), 61521 bit 7 (refills taken).

## Rules

### Items

Seven inventory slots, `Inventory` 24070-24076; slot *s* holds
`ItemsNeeded`[s] (61514) once collected. Icons on the panel at y 0, x
61507+s. Identified from their sprites (measured, `m_inv.png`):

| slot | anim | frame | looks like | where | how |
|---|---|---|---|---|---|
| 0 | 28 | 146 | a key | room 83 (60,128) | item; opens doors (handler 4) |
| 1 | 13 | 147 | a shield | room 40 (116,104) | item; protects from anims 8/31 |
| 2 | 27 | 148 | a crown | room 56 (72,136) | handler 8; stops room 10's chaser |
| 3 | 7 | 149 | a moon | given in room 10 by anim 44 at (40,144) | handler 7, needs the scissors |
| 4 | 29 | 150 | a goblet | room 79 (120,144) | item; stops anim 11 reversing the controls |
| 5 | 25 | 151 | a book | room 0 (72,160) | item |
| 6 | 34 | 152 | scissors | room 110 (68,120) | item |

All seven collected and taken to the cauldron (room 127, (112,165))
win: measured by collecting them in this order and by poking the
inventory.

### Score

Seven ASCII digits at 58804-58810 (inside the print string at 58803).
`AddScore` 57616 (another area) adds a number string (length byte, then
digits 0-9) right-aligned. `ScoreTable` (58817) by index: 0, 50, 100,
200, 300, 500, 750, 1000, 5000. Monster types use indices 2-6 (100-750).
Items +1000, refills +100, the cauldron +100. Not reset by a death.

### MAGIC

Two ASCII digits at 58813-58814, 99 at the start and after every death
and refill. 57568 subtracts the two digits after a string's first byte:
`MagicHit` 58841 (-8, touching a monster or handler 0) and `MagicShot`
58880 (-1 a shot). Underflow sets "00" and calls `KillPumpkin` (measured:
firing at 00 kills). Nothing drains it over time in this area.

### Firing

53163 (another area): fire with a direction held, not teleporting,
24028 bit 0 clear, `CanFire` nonzero, and slot 1's move script 0 or
negative. It pokes the direction into 59450 and spawns slot 1 at the
pumpkin's position with move 2 (10+1 passes at speed 7,7, then
`253,0`) and anim 32, MAGIC -1. Measured: no shot before a refill, a
shot after poking `CanFire`.

### Death and lives

`KillPumpkin` (56571): pumpkin anim 5 (explodes; `SndExplode`=50),
stopped, `DeathTimer` (24034) = 70, `CackleDelay` (24013) = 20,
`CackleCount` (24032) = 143, 24014 = 0. While `DeathTimer` runs the main
loop skips input and the pumpkin (52964) but monsters keep moving. At 0:
`Lives` (24035) - 1; below 0 is game over (53101: tune 51850, "THOU HAST
AMASSED A MEAGRE SCORE ...", wait for fire, restart). Else erase life
icon `Lives` (x 58797+Lives, y 58796), MAGIC 99, and re-enter the room
at its start position (`RoomStarts` 61250 + 2*room, x low byte, y high),
except that rooms 124-127 (61232) send the pumpkin to 112, 112, 115, 115
(61236) unless all items are held (53060). Inventory and score stay.
`Lives` starts at 6 (53550), with six icons, so seven lives in all
(measured: a death at 6 leaves 5; a death at 0 reaches 53101).

### Start

52372: start room = `StartRooms`[byte at (61248) AND 7], rooms 56, 10,
97, 79, 37, 70, 110, 107. 61248 is a word counter, seeded from R into
its low byte at 52238 and incremented by the frame interrupt (57664) and
the menu loop; the byte *at the address it holds* is the random number.
That is the only randomness: monsters, scripts and respawns are
deterministic. 53858 clears 24000-25058 (variables, slots, inventory,
`RoomDone`, sprite buffers), zeroes the score, sets MAGIC 99, clears
61521's bits and restores 59582 = 252.

### Teleport edges

Room exits (63498 + 4*room: left, right, down, up; room exit test 53408,
another area) of 128 or more go through 53310 to room value AND 127.
The tables use 238 (to room 110) and 245 (to room 117), the outdoor
rooms. 53310 clears the play area, shows the pumpkin as anim 33 with
move 1, `TeleTimer` = 105 passes, cackle after 10. All objects freeze
and collisions are ignored while `TeleTimer` runs.

## The witch heads' cackle (53651, 53798)

`CackleTick` (53651) every pass: wait `CackleDelay` passes; if
`CackleCount` is nonzero (bit 7 = just started: strip it, zero
`CackleWait` 24033 and `CacklePitch` 24001), every other pass take step
c (15 down to 1): left head at x 4, y 13 XOR frames 61216[c] and
61216[c-1], right head at x 112, y 13 the same frames +3, each with a
beep (`CackleBeep` 53798: `CacklePitch` = (it - 1) AND 31, tone through
52854) and a HALT before drawing. The frames go 54, 55, 54, ... 55, 53:
the heads cackle and come to rest on 53/56 (measured, `m_panelseq.png`).
Drawn with 57194, which writes attributes too (the panel's sprite set).

## Data tables

| addr | size | label | format |
|---|---|---|---|
| 58796 | 7 | `LifeIcons` | y, then x of icons 1-6 |
| 58817 | 18 | `ScoreTable` | 9 pointers to number strings |
| 58835 | 48 | `Numbers` | number strings: length, digits 0-9 |
| 59393 | 44 | `MoveScripts` | 22 pointers (0 unused) |
| 59437 | 361 | | movement scripts, 4-byte entries (above) |
| 60580 | 110 | `AnimScripts` | 55 pointers (0 = empty) |
| 60690 | 375 | | anim scripts: delay, first frame, frames/commands |
| 61065 | 55 | `ObjTypes` | type byte per anim |
| 61120 | 22 | `Handlers` | 11 handler addresses |
| 61142 | 3 | `FixedAnims` | anims of fixed-object kinds 0-2 |
| 61216 | 16 | `CackleFrames` | |
| 61232 | 8 | `RespawnRooms` | 4 rooms, then the 4 to go to |
| 61240 | 8 | `StartRooms` | |
| 61248 | 2 | `RandCounter` | |
| 61250 | 256 | `RoomStarts` | per room, x then y |
| 61506 | 8 | `InvPanel` | y, then x of slots 0-6 |
| 61514 | 7 | `ItemsNeeded` | 28, 13, 27, 7, 29, 25, 34 |
| 61521 | 52 | `MagicRooms` | room numbers, bit 7 = taken |
| 61573 | 104 | `MagicPos` | x, y per refill |
| 61677 | 256 | `RoomLists` | pointer per room (128 rooms) |
| 61933 | 1021 | | lists: count, then 4- or 3-byte entries; rooms with identical lists share one (21 rooms share the empty list) |

Movement scripts (number: what it does): 1 teleport (wait 36, one step
up-left at 6,10, stop); 2 the shot; 3-5 chase at speeds (0,4), (1,0),
(1,2); 6 patrol 8 right/left with pauses, switching anims 54/22; 7 slow
patrol with pauses; 8 chase (1,2), switchable off; 9-12 and 16 patrol
right then left, switching to the left-facing anim (9/17, 8/31, 41/14);
13, 14 bob down/up; 15 jitter; 17-19 wait, swoop, then chase; 20, 21
patrol 30/80 each way. Number 18 is in no room list.

Anims of note: 1-4 the pumpkin (bounce, spin both ways, still); 5 the
explosion; 26 the cauldron; 30 the door opening; 32/45 the magic
sparkle (refill, shot, room 10's guardian); 33 the teleport; 37/38 door
shut/open; 48 the deadly chandelier (8 bytes wide).

## Variables (24000-24076)

| addr | size | label | meaning |
|---|---|---|---|
| 24000 | 1 | `SndExplode` | explosion sound frames left (the interrupt, 57714, counts it down) |
| 24001 | 1 | `CacklePitch` | |
| 24011 | 1 | | this room's done bit (54264) |
| 24012 | 1 | `TeleTimer` | |
| 24013 | 1 | `CackleDelay` | |
| 24014 | 1 | | pumpkin movement state, zeroed on death |
| 24015 | 1 | `ReverseTimer` | counted down by 53149; at 0 clears 24016 |
| 24016 | 1 | `ReverseMask` | 12 or 0 |
| 24017 | 1 | `CanFire` | |
| 24020 | 1 | `InputBits` | |
| 24021 | 1 | `OtherSlot` | |
| 24022 | 1 | `CurSlot` | |
| 24025 | 1 | `RedrawFlag` | |
| 24030 | 1 | `Room` | |
| 24031 | 1 | `PushBits` | |
| 24032 | 1 | `CackleCount` | |
| 24033 | 1 | `CackleWait` | |
| 24034 | 1 | `DeathTimer` | |
| 24035 | 1 | `Lives` | |
| 24042 | 2 | `RoomList` | |
| 24054 | 16 | `RoomDone` | |
| 24070 | 7 | `Inventory` | |
| 24077 | 120 | `Slots` | |
| 24203 | 20 | | slot 0 saved during room entry |
| 24225, 24427 | 202 each | | sprite build buffers (new, old) |

## For the port

- The engine is table-driven: the scripts, types, lists and handlers
  carry over as data. Keep slot layout and order, since collision picks
  the lowest slot and list entry *i* is slot 2+*i*.
- The HALT per redrawn slot sets the game's speed; the spin loop is
  timed in Z80 cycles. Both need a port decision.
- The comparison state for `make passes`: 24000-24076, the slots, the
  score and MAGIC digits, and the self-modified 59450, 59582 and 61521.
