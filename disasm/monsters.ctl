; Cauldron II (ZX Spectrum): monsters, objects and the game's rules.
; Research control file for the BBC Micro port. Covers only this area:
; the per-slot object engine (55285-57057), the witch-head cackle
; (53651, 53798), their variables and data tables. See
; docs/research/monsters.md for the prose.
;
; Object slot layout (6 slots of 20 bytes at 24077; slot 0 the pumpkin,
; slot 1 its shot, slots 2-5 the room's monsters and objects), offsets:
;  +0 move count  +1 move script (bit 7: driven elsewhere)  +2 move index
;  +3 direction bits (b0 up, b1 down, b2 left, b3 right; 252 = chase)
;  +4 x speed  +5 y speed  +6 x  +7 y  +8 x max  +9 y max
;  +10 drawn x  +11 drawn y  +12 anim delay  +13 anim (bit 7: stopped)
;  +14 anim index  +15 frame  +16 drawn frame  +17 width (bytes)
;  +18 height (lines)  +19 respawn timer

@ 24000 label=SndExplode
b 24000 Game variables used by the object engine and the rules
N 24000 Explosion sound timer: set to 50 when anything turns into anim 5; the frame interrupt (57714) counts it down and beeps.
B 24000,1 SndExplode
@ 24001 label=CacklePitch
B 24001,1 CacklePitch: the cackle's pitch step (53798)
B 24002,10 (Other areas: tune selector, sfx pointer, input, ...)
@ 24012 label=TeleTimer
B 24012,1 TeleTimer: passes left of the teleport sequence (53310); objects freeze while nonzero
@ 24013 label=CackleDelay
B 24013,1 CackleDelay: passes before the witch heads cackle
@ 24014 label=PumpkinVar14
B 24014,1 Pumpkin movement variable, zeroed by a death (56571)
@ 24015 label=ReverseTimer
B 24015,1 ReverseTimer: passes left of reversed left/right controls
@ 24016 label=ReverseMask
B 24016,1 ReverseMask: 12 while reversed (XORed into the input's left/right bits), else 0
@ 24017 label=CanFire
B 24017,1 CanFire: 0 until a magic refill is taken, then that room's number OR 128
B 24018,2
@ 24020 label=InputBits
B 24020,1 InputBits: this pass's controls (b0-3 directions, b4 fire)
@ 24021 label=OtherSlot
B 24021,1 OtherSlot: the slot just collided with
@ 24022 label=CurSlot
B 24022,1 CurSlot: the slot being processed
B 24023,2
@ 24025 label=RedrawFlag
B 24025,1 RedrawFlag: nonzero if this slot moved or changed frame this pass
B 24026,4 (Pumpkin bounce state, another area)
@ 24030 label=Room
B 24030,1 Room: the current room (0-127)
@ 24031 label=PushBits
B 24031,1 PushBits: b2/b3 force the pumpkin left/right (handlers 10/9)
@ 24032 label=CackleCount
B 24032,1 CackleCount: steps left of the cackle; bit 7 = just started
@ 24033 label=CackleWait
B 24033,1 CackleWait: passes to wait before the next step
@ 24034 label=DeathTimer
B 24034,1 DeathTimer: passes left of the pumpkin's death (70 at the start)
@ 24035 label=Lives
B 24035,1 Lives: spare lives (6 at the start); a death at 0 ends the game
B 24036,6
@ 24042 label=RoomList
W 24042,2 RoomList: the current room's monster list (from 61677)
B 24044,10
@ 24054 label=RoomDone
B 24054,16,8 RoomDone: one bit per room (bit 7-(room AND 7) of byte room/8): door opened, switch thrown
@ 24070 label=Inventory
B 24070,7 Inventory: one byte per item slot, the item's anim number once held (else 0)
@ 24077 label=Slots
b 24077 Object slots (6 x 20 bytes)
B 24077,20 Slot 0: the pumpkin
@ 24083 label=PumpkinX
@ 24090 label=PumpkinAnim
@ 24097 label=ShotSlot
B 24097,20 Slot 1: the pumpkin's shot
@ 24117 label=MonsterSlots
B 24117,80,20 Slots 2-5: the room's monsters and objects
i 24197

@ 53651 label=CackleTick
c 53651 Witch heads cackle (one step per call)
D 53651 Called every pass of the main loop. After a death (56571) or a teleport (53310) sets CackleDelay and CackleCount=143, it waits CackleDelay passes, then animates both witch heads on the panel through 15 frame swaps, one swap every other pass, each with a falling beep. Each swap XORs the old and new head frame, so the head ends on frame 53/56 (the rest pose). Uses HALT twice per step. Corrupts everything but IX/IY.
  53651,11 Waiting for the delay to run out?
  53662,5 Return if the cackle is over
  53667,15 Just started (bit 7): clear the flag, CackleWait and the pitch
  53682,11 Every other pass
  53693,4 A = step counter (15 down to 1)
  53697,19 Build the left head's new frame (61216+step) at x=4,y=13 into the sprite buffer at 24225...
  53716,8 ...and its old frame (61216+step-1) into the buffer at 24427
  53724,3 Beep
  53727,1 Wait for the frame
  53728,12 XOR the new and old frames: left head changes
  53743,15 Same again for the right head: frames +3 at x=112,y=13
  53787,10 Next step on the next-but-one pass

@ 53798 label=CackleBeep
c 53798 Beep for the cackle
D 53798 Lowers the pitch step at CacklePitch (modulo 32) and plays one tone through the sound routine at 52854. Preserves all registers.

@ 55285 label=Respawn
c 55285 Respawn dead monsters (per pass)
D 55285 Called every pass. Room-list entry i belongs to slot 2+i. For each 4-byte entry (3-byte fixed-object entries are skipped and never respawn), count down the slot's respawn timer (+19, set by a 253 command); when it reaches 0 the monster is spawned again at its list position with its movement script and anim. Does nothing during a teleport.
  55285,5 Not during a teleport
  55290,6 B = entries in the room's list
  55297,4 IX = slot 2
  55304,2 A = slot number
  55306,4 IY = first entry: x, y, move script, anim
  55313,5 Fixed object (bit 7)? Skip its 3 bytes
  55320,10 Count the respawn timer down; nothing to do unless it reaches 0 now
  55332,14 Spawn: E=x, D=y, B=anim, C=move script, A=slot
  55346,8 Next entry (4 bytes; 3 for a fixed object)
  55354,9 Next slot

@ 55363 label=Spawn
c 55363 Put an object in a slot
D 55363 Used at room entry, for the pumpkin's start, the shot, respawns and the teleport.
R 55363 A Slot (0-5)
R 55363 E X
R 55363 D Y
R 55363 C Movement script (128 = none; the pumpkin's)
R 55363 B Anim
R 55363 O:HL corrupted; CurSlot=A
N 55363 Sets CurSlot (24022), which the sprite drawer reads to choose its clipping. Width and height (+17, +18) are not set here: they stay stale until the first animation step.
  55363,3 CurSlot = A
  55371,3 IX = slot A
  55376,16 Clear move count, move index, anim delay, anim index, respawn timer
  55392,12 Position and drawn position
  55404,6 Move script and anim
  55410,15 First frame (byte 1 of the anim script) as frame and drawn frame
  55425,15 Build the sprite and XOR it on
  55440,28 x max = 139 - 4 x width; y max = 191 - height

@ 55472 label=ClearSlots
c 55472 Clear all six slots
D 55472 At room entry. Clears move count, move script, direction, speeds, anim and respawn timer of every slot. Preserves IX; corrupts A, B, DE.

@ 55512 label=StopSlot
c 55512 Stop a slot moving
R 55512 A Slot
D 55512 Clears move count, move script, move index, direction and speeds; the anim carries on. Preserves all registers.

@ 55551 label=RemoveSlot
c 55551 Remove an object
R 55551 A Slot
D 55551 Stops it, clears its anim (so the slot is free) and XORs its drawn sprite off. Sets CurSlot to A for the drawer and restores it. Does not touch the respawn timer. Preserves all registers.

@ 55624 label=SetAnim
c 55624 Change a slot's anim
R 55624 A Slot
R 55624 B New anim
D 55624 Restarts the anim at its first frame and recomputes x max and y max from it. For slots 2-5 the position is first clamped to x<=134, y<=170. Anim 5 (the explosion) also starts the explosion sound (SndExplode=50). Nothing is drawn here: the next pass redraws. Preserves all registers.
  55645,22 Slots 2-5: clamp x to 134 and y to 170
  55674,8 Clear anim index and respawn timer
  55682,3 New anim
  55685,16 Anim delay 0 (step next pass); frame = first frame
  55701,24 x max = 139 - 4 x width; y max = 191 - height
  55725,11 The explosion? Start its sound

@ 55745 label=ChaseDir
c 55745 Direction bits towards the pumpkin
R 55745 IX Slot
R 55745 O:A Direction bits: b3 right/b2 left by x, b1 down/b0 up by y (none when equal)
D 55745 Preserves BC.

@ 55783 label=ObjectsTick
c 55783 Animate, move and draw all six slots (per pass)
D 55783 Called every pass. For each slot in turn: step the sound effect, step the anim script, step the movement script, and if anything changed redraw the slot (waiting for the frame interrupt with HALT) and test it against slots 2-5 for collisions. A slot with nothing to redraw instead spins a delay loop. So a pass takes about one frame per slot that changed.
  55783,6 Six slots from slot 0
@ 55790 label=ObjectsNext
  55790,4 CurSlot = slot number
@ 55795 label=ObjectsRedo
  55795,4 Nothing to redraw yet
  55799,7 Step the sound effect (another area)
N 55806 Animation.
  55806,13 Waiting out the anim delay?
  55819,10 No anim, or stopped (bit 7)? Skip
  55829,10 HL = anim script; reload the delay from its byte 0
  55839,9 Next byte
  55848,13 255 n: go to index n+1
  55861,15 254: stop (set bit 7 of the anim)
  55876,4 253 n: remove the object, respawn in n passes
@ 55880 label=ObjectDie
  55880,5 Respawn timer = n
  55885,10 Clear the anim, anim delay and move script
  55895,18 XOR the drawn sprite off
  55913,3 Next slot
  55916,3 Otherwise a frame number
  55919,33 x max, width, y max, height from the frame's size
  55952,5 Redraw
N 55957 Movement.
  55957,13 Count down the current command
  55970,10 No move script: just draw. Bit 7 (the pumpkin): keep its direction
  55980,20 HL = move script entry (4 bytes) at the move index
  56000,12 255 n: go to entry n
  56012,11 254: end of script
  56023,5 253 n: remove the object, respawn in n passes
  56028,18 251 a: change to anim a, then start this slot again
  56046,21 Otherwise: direction, count, x speed, y speed; next entry
@ 56067 label=ObjectsMove
  56067,9 Redraw if moving
  56076,26 Bounds: slots 2-5 x 12..x max, y 33..y max...
  56102,6 ...slots 0 and 1 x 3..248, y 8..211
  56108,6 252: chase the pumpkin
  56114,20 Apply each direction bit, then draw

@ 56137 label=MoveUp
c 56137 Move up by the y speed, not above B
@ 56160 label=MoveDown
c 56160 Move down by the y speed, not below C
@ 56178 label=MoveLeft
c 56178 Move left by the x speed, not past D
@ 56196 label=MoveRight
c 56196 Move right by the x speed, not past E

@ 56214 label=ObjectsDraw
c 56214 Redraw a slot, test collisions, next slot
D 56214 Tail of 55783.
  56214,7 Nothing changed?
  56221,15 Build the new frame at the new position into the buffer at 24225
  56240,15 Build the old frame at the drawn position into the buffer at 24427
  56255,2 Wait for the frame interrupt
  56257,10 XOR the old off and the new on
  56267,9 Remember what is drawn
  56276,8 Touching slot 2-5? Act on it
@ 56286 label=ObjectsLoop
  56286,13 Next slot
  56299,11 Nothing to draw: spin instead (1024 loops)

@ 56310 label=Collide
c 56310 Act on a collision
R 56310 A The other slot (2-5)
R 56310 IX (set here) the other slot
D 56310 Only the pumpkin (slot 0) and its shot (slot 1) act on collisions. The other object's type comes from the table at 61065, indexed by its anim. Pumpkin: bit 7 kills it; bit 6 is an item to collect; bit 5 runs special handler (low nibble) from 61120; bit 4 is harmless; otherwise it is a monster: score (low nibble indexes 58817), it explodes, magic -8. Shot: bit 7 destroys the shot; bits 6 and 4 and handlers other than 0 let it pass; otherwise the target explodes and scores (handler 0's monster scores 100), and the shot vanishes.
  56310,9 Not during a teleport
  56319,4 OtherSlot = A
  56323,3 IX = other slot
  56326,12 Pumpkin, shot, or neither
N 56338 The pumpkin touched something.
  56338,9 Not if the pumpkin is gone or exploding (anim 5)
  56347,6 Not if the other has no anim
  56353,6 C = its type
  56360,18 Bit 7 deadly, 6 item, 5 handler, 4 harmless
  56378,10 A monster: add its score...
  56388,11 ...it explodes and stops...
  56399,9 ...magic -8
@ 56409 label=CollideHandler
  56409,10 Special: jump through the table at 61120
N 56419 The shot touched something.
  56419,6 Not if it has no anim
  56425,22 C = its type: bit 7 stops the shot, 6 and 4 ignored
@ 56448 label=ShotKill
  56448,24 Explode and stop it, add score C AND 15
@ 56475 label=ShotHandler
  56475,9 Handler 0's monster (anim 11) dies as a 100-point monster; other handlers ignore the shot
@ 56484 label=ShotGone
  56484,6 Remove the shot
@ 56490 label=CollectItem
  56490,9 An item: its inventory slot is bits 3-5 of the type
  56502,6 Remove it from the room
  56508,6 Score 1000
  56514,7 Pickup sound

@ 56521 label=GiveItem
c 56521 Put an item in the inventory
R 56521 A Inventory slot (0-6)
D 56521 Stores the slot's required item (61514) in Inventory and draws that item's first frame on the panel at x=(61507+slot), y=(61506).

@ 56571 label=KillPumpkin
c 56571 The pumpkin dies
D 56571 The pumpkin explodes and stops; DeathTimer=70 passes (the main loop then takes a life), the witch heads cackle after 20 passes.

@ 56601 label=Handler0
c 56601 Handler 0 (anim 11): explodes for 100 points and magic -8; without item 29 (the goblet) the controls reverse
  56601,11 Explode and stop it
  56612,12 Score 100
  56624,6 Magic -8
  56630,6 Holding item 29? Done
  56636,10 Reverse left/right for 50 passes
@ 56647 label=Handler1
c 56647 Handler 1 (anims 8, 31): kills unless item 13 (the shield) is held
@ 56656 label=Handler4
c 56656 Handler 4 (anim 37, a door): with item 28 it opens (anim 30) for good
@ 56672 label=Handler2
c 56672 Handler 2 (anim 35): becomes anim 24 and is marked done
@ 56683 label=Handler3
c 56683 Handler 3 (anim 39): becomes anim 16 and is marked done
@ 56694 label=MarkRoomDone
c 56694 Mark this room done (its RoomDone bit)

@ 56700 label=RoomDoneBit
c 56700 This room's RoomDone bit
R 56700 O:HL RoomDone byte for the room (24054 + room/8)
R 56700 O:A Its value
R 56700 O:C The room's bit (128 >> (room AND 7))

@ 56729 label=HaveItem
c 56729 Is item A in the inventory?
R 56729 A Item (anim number)
R 56729 O:F Z set if held
D 56729 Preserves BC, HL.

@ 56747 label=Handler5
c 56747 Handler 5 (anim 32 in a magic room): magic refill
D 56747 Marks the room's entry in 61521 taken (bit 7) so the refill never returns this game, enables firing (CanFire), removes the object, sets magic to 99 and scores 100.

@ 56794 label=HaveAllItems
c 56794 Are all seven items held?
R 56794 O:F Z set if Inventory matches 61514

@ 56811 label=Handler6
c 56811 Handler 6 (anim 26, the cauldron): the end
D 56811 With all seven items: score 100, play the ending tune and the "WELL DONE" text, wait for fire, back to the menu. Without them the pumpkin dies.
  56811,6 Not all items: death
  56817,6 Score 100
  56823,10 Ending tune
  56833,21 Clear the screen, print the message and the score
  56854,14 Wait for fire to go up, then down; restart

@ 56871 label=Handler7
c 56871 Handler 7 (anim 44): gives item 7 (the moon) if item 34 (the scissors) is held
  56877,6 Already have it?
  56883,17 Inventory slot 3; score 1000; pickup sound

@ 56901 label=Handler8
c 56901 Handler 8 (anim 27, the crown): collect it and stop the chaser of movement script 8
  56901,5 Inventory slot 2
  56906,6 Remove it
  56912,4 Movement script 8's direction (252, chase) becomes 0: its users stand still
  56916,13 Score 1000; pickup sound

@ 56929 label=Handler9
c 56929 Handler 9 (anims 24, 36, 41): once its anim has stopped, push the pumpkin right
@ 56939 label=Handler10
c 56939 Handler 10 (anims 16, 40, 42): once its anim has stopped, push the pumpkin left
@ 56949 label=AnimStopped
c 56949 Has the other object's anim stopped?
R 56949 O:F Z set if its anim is 0 or has bit 7 set

@ 56967 label=Overlap
c 56967 Does slot IX overlap one of slots 2-5?
R 56967 IX Slot
R 56967 O:F NZ if so
R 56967 O:A The first slot it overlaps
D 56967 Boxes: x distance under 4 x the width of the one further left, y distance under the height of the one higher up. Skips empty slots and the slot itself.
i 57058

@ 58796 label=LifeIcons
b 58796 Life icons on the panel: y, then x of icons 1-6
B 58796,1 y
B 58797,6 x of icons 1-6 (icon n is erased when Lives drops to n-1)
i 58803

@ 58817 label=ScoreTable
w 58817 Score strings by monster type (type AND 15): +0, +50, +100, +200, +300, +500, +750, +1000, +5000
W 58817,18,2
@ 58835 label=Numbers
b 58835 Number strings: length, then digits (0-9, not ASCII). Added to the score by 57616; 57568 subtracts the two bytes after the first from MAGIC
B 58835,3 0 (also "magic -00", just a redraw)
B 58838,3 05 (unused here)
@ 58841 label=MagicHit
B 58841,3 Magic -08: touching a monster
B 58844,3 10 (unused here)
B 58847,3 +50
B 58850,4 +100
B 58854,4 +200
B 58858,4 +300
B 58862,4 +500
B 58866,4 +750
B 58870,5 +1000
B 58875,5 +5000
@ 58880 label=MagicShot
B 58880,3 Magic -01: a shot
i 58883

@ 59393 label=MoveScripts
w 59393 Movement scripts by number (0 unused). Entries are 4 bytes: direction (b0 up, b1 down, b2 left, b3 right, 252 chase), count (applied count+1 passes), x speed, y speed; or 255 n (go to entry n), 254 (end), 253 n (remove, respawn in n passes), 251 a (change to anim a)
W 59393,44,2
b 59437 Movement script data
B 59437,13,4 Movement script 1
B 59450,6,4 Movement script 2
B 59456,6,4 Movement script 3
B 59462,6,4 Movement script 4
B 59468,6,4 Movement script 5
B 59474,58,4 Movement script 6
B 59532,50,4 Movement script 7
B 59582,6,4 Movement script 8
B 59588,18,4 Movement script 9
B 59606,18,4 Movement script 10
B 59624,18,4 Movement script 11
B 59642,18,4 Movement script 12
B 59660,10,4 Movement script 13
B 59670,10,4 Movement script 14
B 59680,26,4 Movement script 15
B 59706,18,4 Movement script 16
B 59724,22,4 Movement script 17
B 59746,22,4 Movement script 18
B 59768,10,4 Movement script 19
B 59778,10,4 Movement script 20
B 59788,10,4 Movement script 21
@ 59450 label=ShotDir
@ 59582 label=ChaseDir8
i 59798

@ 60580 label=AnimScripts
w 60580 Anim scripts by anim number (0 = no object). Byte 0 is the delay in passes between steps, byte 1 the first frame; then frames, or 255 n (continue after index n), 254 (stop: anim bit 7), 253 n (remove, respawn in n passes)
W 60580,110,2
b 60690 Anim script data
B 60690,9 Anim 1
B 60699,12 Anim 2
B 60711,12 Anim 3
B 60723,3 Anim 4
B 60726,12 Anim 5
B 60738,7 Anim 6
B 60745,3 Anim 7
B 60748,11 Anim 8
B 60759,7 Anim 9
B 60766,5 Anim 10
B 60771,8 Anim 11
B 60779,9 Anim 12
B 60788,5 Anim 13
B 60793,5 Anim 14
B 60798,7 Anim 15
B 60805,4 Anim 16
B 60809,7 Anim 17
B 60816,23 Anim 18
B 60839,7 Anim 19
B 60846,9 Anim 20
B 60855,9 Anim 21
B 60864,3 Anim 22
B 60867,7 Anim 23
B 60874,4 Anim 24
B 60878,5 Anim 25
B 60883,3 Anim 26
B 60886,5 Anim 27
B 60891,5 Anim 28
B 60896,5 Anim 29
B 60901,5 Anim 30
B 60906,11 Anim 31
B 60917,10 Anim 32
B 60927,28 Anim 33
B 60955,5 Anim 34
B 60960,3 Anim 35
B 60963,3 Anim 36
B 60966,3 Anim 37
B 60969,3 Anim 38
B 60972,3 Anim 39
B 60975,3 Anim 40
B 60978,5 Anim 41
B 60983,23 Anim 42
B 61006,3 Anim 43
B 61009,3 Anim 44
B 61012,10 Anim 45
B 61022,5 Anim 46
B 61027,7 Anim 47
B 61034,5 Anim 48
B 61039,5 Anim 49
B 61044,3 Anim 50
B 61047,3 Anim 51
B 61050,7 Anim 52
B 61057,6 Anim 53
B 61063,2 Anim 54
@ 61065 label=ObjTypes
b 61065 Object type by anim: b7 deadly; b6 item (b3-5 inventory slot); b5 special (b0-3 handler, 61120); b4 harmless; else a monster (b0-3 score index)
B 61065,55,11
@ 61120 label=Handlers
w 61120 Special handlers 0-10
W 61120,22,2
@ 61142 label=FixedAnims
b 61142 Fixed objects' anims by kind (3-byte room entries): 35 (switch), 37 (door), 39 (switch); +1 when the room is done
B 61142,3
i 61145

@ 61216 label=CackleFrames
b 61216 Witch heads' cackle: left head frames by step (right head +3)
B 61216,16
@ 61232 label=RespawnRooms
B 61232,4 Rooms that send a dead pumpkin back unless all items are held...
B 61236,4 ...and where to
@ 61240 label=StartRooms
B 61240,8 Start rooms, one picked at random
@ 61248 label=RandCounter
W 61248,2 Counter incremented every frame and menu pass; the byte at the address it holds picks the start room
@ 61250 label=RoomStarts
W 61250,256,16 Pumpkin's start position per room (x low byte, y high byte)
@ 61506 label=InvPanel
B 61506,1 Inventory icons: y
B 61507,7 Inventory icons: x by slot
@ 61514 label=ItemsNeeded
B 61514,7 The item (anim) each inventory slot holds: the seven to take to the cauldron
@ 61521 label=MagicRooms
B 61521,52,13 Rooms with a magic refill (bit 7 set once taken; cleared at game start)
@ 61573 label=MagicPos
W 61573,104,16 Magic refill positions (x low, y high)
@ 61677 label=RoomLists
w 61677 Monster list per room (128 rooms)
W 61677,256,16
@ 61933 label=RoomListData
b 61933 Monster lists: count, then entries x, y, move script, anim (4 bytes), or x, y, 128+kind (3 bytes: a fixed object, anim from 61142)
B 61933,1 Rooms 3, 5, 9, 11, 12, 14, 22, 30, 32, 33, 46, 59, 64, 72, 73, 80, 94, 101, 121, 122, 123: 0 entries
B 61934,5 Room 0: 1 entry
B 61939,9 Rooms 1, 17: 2 entries
B 61948,9 Room 2: 2 entries
B 61957,9 Room 4: 2 entries
B 61966,5 Room 6: 1 entry
B 61971,9 Room 7: 2 entries
B 61980,5 Room 8: 1 entry
B 61985,13 Room 10: 3 entries
B 61998,5 Room 13: 1 entry
B 62003,5 Room 15: 1 entry
B 62008,5 Room 16: 1 entry
B 62013,9 Room 18: 2 entries
B 62022,5 Room 19: 1 entry
B 62027,9 Room 20: 2 entries
B 62036,5 Room 21: 1 entry
B 62041,9 Room 23: 2 entries
B 62050,5 Room 24: 1 entry
B 62055,9 Room 25: 2 entries
B 62064,5 Room 26: 1 entry
B 62069,9 Room 27: 2 entries
B 62078,9 Room 28: 2 entries
B 62087,5 Room 29: 1 entry
B 62092,5 Room 31: 1 entry
B 62097,13 Room 34: 3 entries
B 62110,13 Room 35: 3 entries
B 62123,13 Room 36: 3 entries
B 62136,13 Room 37: 3 entries
B 62149,9 Room 38: 2 entries
B 62158,12 Room 39: 3 entries
B 62170,12 Room 40: 3 entries
B 62182,13 Room 41: 3 entries
B 62195,13 Room 42: 3 entries
B 62208,13 Room 43: 3 entries
B 62221,12 Room 44: 3 entries
B 62233,13 Room 45: 3 entries
B 62246,13 Room 47: 3 entries
B 62259,13 Room 48: 3 entries
B 62272,9 Room 49: 2 entries
B 62281,13 Room 50: 3 entries
B 62294,9 Room 51: 2 entries
B 62303,9 Room 52: 2 entries
B 62312,8 Room 53: 2 entries
B 62320,13 Room 54: 3 entries
B 62333,13 Room 55: 3 entries
B 62346,17 Room 56: 4 entries
B 62363,13 Room 57: 3 entries
B 62376,12 Room 58: 3 entries
B 62388,5 Room 60: 1 entry
B 62393,13 Room 61: 3 entries
B 62406,5 Room 62: 1 entry
B 62411,13 Room 63: 3 entries
B 62424,5 Rooms 65, 87: 1 entry
B 62429,12 Room 66: 3 entries
B 62441,5 Room 67: 1 entry
B 62446,9 Room 68: 2 entries
B 62455,9 Room 69: 2 entries
B 62464,12 Room 70: 3 entries
B 62476,9 Room 71: 2 entries
B 62485,13 Room 74: 3 entries
B 62498,8 Room 75: 2 entries
B 62506,9 Room 76: 2 entries
B 62515,13 Room 77: 3 entries
B 62528,9 Room 78: 2 entries
B 62537,16 Room 79: 4 entries
B 62553,9 Room 81: 2 entries
B 62562,13 Room 82: 3 entries
B 62575,13 Room 83: 3 entries
B 62588,9 Room 84: 2 entries
B 62597,9 Room 85: 2 entries
B 62606,5 Room 86: 1 entry
B 62611,13 Room 88: 3 entries
B 62624,13 Room 89: 3 entries
B 62637,9 Room 90: 2 entries
B 62646,9 Room 91: 2 entries
B 62655,9 Room 92: 2 entries
B 62664,12 Room 93: 3 entries
B 62676,9 Room 95: 2 entries
B 62685,9 Room 96: 2 entries
B 62694,13 Room 97: 3 entries
B 62707,13 Room 98: 3 entries
B 62720,13 Room 99: 3 entries
B 62733,9 Room 100: 2 entries
B 62742,8 Room 102: 2 entries
B 62750,13 Room 103: 3 entries
B 62763,9 Room 104: 2 entries
B 62772,5 Room 105: 1 entry
B 62777,9 Room 106: 2 entries
B 62786,8 Room 107: 2 entries
B 62794,9 Room 108: 2 entries
B 62803,8 Room 109: 2 entries
B 62811,13 Room 110: 3 entries
B 62824,9 Room 111: 2 entries
B 62833,9 Room 112: 2 entries
B 62842,13 Room 113: 3 entries
B 62855,9 Room 114: 2 entries
B 62864,9 Room 115: 2 entries
B 62873,13 Room 116: 3 entries
B 62886,5 Room 117: 1 entry
B 62891,5 Room 118: 1 entry
B 62896,9 Room 119: 2 entries
B 62905,9 Room 120: 2 entries
B 62914,5 Room 124: 1 entry
B 62919,13 Room 125: 3 entries
B 62932,13 Room 126: 3 entries
B 62945,9 Room 127: 2 entries
i 62954
