; SkoolKit control file: Cauldron II (ZX Spectrum), core, rooms and drawing.
; See docs/research/core.md. Decimal addresses throughout. Ranges outside
; this area are 'i' (ignored) blocks, for the other areas' control files.
;
;   .venv/bin/sna2skool.py -c disasm/core.ctl build/c2.z80 > build/research/core.skool

; ----------------------------------------------------------------------------
; Room graphics
; ----------------------------------------------------------------------------

@ 34526 label=TILE_GFX
b 34526 Tile graphics
D 34526 641 character tiles, 8 bytes each (top line first), indexed by the tile number that #R53949 forms as (bank base + tile byte) AND 8191. Written straight to the screen by #R54464.
B 34526,5128,8

@ 39654 label=BLOCKS
b 39654 Block definitions
D 39654 256 blocks of 4x4 tile bytes (16 bytes each, row by row). A tile byte is turned into a tile number by the room's bank table (#R62954).
B 39654,4096,16

@ 43750 label=ROOM_LAYOUT
b 43750 Room layouts
D 43750 128 rooms, 40 bytes each: 5 rows of 8 block numbers (#R39654). Each block is 4x4 characters, so a room fills character rows 4-23, all 32 columns.
B 43750,5120,8

@ 48870 label=TILE_ATTR
b 48870 Tile attributes
D 48870 One Spectrum attribute byte per tile number (641), parallel to #R34526.
B 48870,641,16

@ 49511 label=FONT
b 49511 Font
D 49511 64 glyphs, 8 bytes each: 0-9 are '0'-'9', 10-35 are 'A'-'Z'; the rest are reached through the translation table at #R57817 (space, %, @, -, /, ^, ~ and 'e'-'x', which draw the panel's two witch heads).
B 49511,512,8

i 50023

; ----------------------------------------------------------------------------
; Sound (one entry point is called at startup; the sound area owns this)
; ----------------------------------------------------------------------------

@ 50100 label=TitleTuneInit
c 50100 Start the title tune (sound area)
D 50100 Sets the two channels' note pointers (50127, 50131), then falls into 50112, which is also entry 1 of the per-frame interrupt table at #R64019: plays one step of the tune (50171) and calls the ROM's KEY-SCAN (654).
N 50100 Not core: the sound area documents 50124-50335. Startup calls it once; the IM 2 handler calls 50113 every frame while 24002 is 1.
@ 50113 label=TitleTuneFrame

i 50124

; ----------------------------------------------------------------------------
; Startup and the main loop
; ----------------------------------------------------------------------------

@ 52180 label=Entry
c 52180 Entry point (from the loader)
D 52180 Builds the IM 2 vector table, sets border 0 and the default Interface II key table, then goes to #R52235.
 52180 Fill 65024-65280 (257 bytes) with 253, so any vector byte gives 65021
 52193 I=254: the table at 65024
 52197 Copy the JP 57664 template (#R52232) to 65021
 52211 Border black; 24006 is the OUT (254) shadow
 52218 Interface II defaults (#R57760) into the key table (#R57784)

@ 52232 label=JpIrqTemplate
b 52232 JP 57664, copied to 65021 at startup
B 52232,3

@ 52235 label=Restart
c 52235 Restart: title, menu, attract loop, then a new game, then the main loop
D 52235 Also reached by the ABORT key (52775), game over (#R53101) and the win screen. SP is reset to 0, so this never returns.
 52238 Random pointer #R61248: H is left at 225 by startup, L from R
 52251 Reset the three tune players
 52272 Title tune
 52275 24002=1: the interrupt plays the title tune each frame
 52281 Clear the screen
 52284 The menu (1 Kempston, 2 Interface II, 3 define keys, 4 play)
 52290 Attract loop: every 50 passes swap the page of credits (24008, strings #R58776, positions 58780)
 52338 Step the random pointer once a pass
 52345 Delay: 10000 DEC BC loops a pass
 52353 Read the controls; fire (bit 4) starts the game
 52372 New game. Music off
 52377 Start room: 61240 + (byte at random pointer AND 7)
 52384 Reset the variables and panel (#R53858), draw the panel (#R53550)
 52397 Put the player at the room's start position (#R52945)
 52400 Draw the room (#R53949)
@ 52430 label=MainLoop
 52430 Main loop. Dying (24034 counting down) skips input and the player
@ 52437 label=MainLoopAlive
 52437 Going outside (24012 counting down)
 52444 Read the controls into 24020
 52451 Fire-repeat timer (53149)
 52455 Fire pressed: cast (53163)
 52463 Player (player area)
@ 52466 label=MainLoopObjects
 52466 Move and redraw every object; HALTs once per object that moved (55783)
 52469 Room exits (#R53408)
 52472 Panel witch heads (#R53651)
 52475 Respawn monsters (55285)

i 52481

; ----------------------------------------------------------------------------
; Room entry, death and restart
; ----------------------------------------------------------------------------

@ 52920 label=OutsideTick
c 52920 Main loop: count down the trip outside, then enter the outside room
R 52920 A 24012 (non-zero)
D 52920 When 24012 reaches 0: clear the play area, put the player at the room's start position, draw room 24030 (set by #R53310), reset the player's state.

@ 52945 label=PlacePlayer
c 52945 Put the player (object slot 0) at room A's start position
R 52945 A Room number (preserved)
D 52945 Position from the word table at #R61250; object type 1 (the pumpkin) via 55363 (objects area), which also draws it.

@ 52964 label=DeathTick
c 52964 Main loop: count down a death, then lose a life
R 52964 A 24034 (non-zero)
D 52964 At 0: one fewer life (24035; below 0 is game over, #R53101), XOR the life's pumpkin off the panel (positions #R58796), magic back to 99, then re-enter the room (or a respawn room, #R53060) at its start position.

@ 53036 label=ResetPlayerState
c 53036 Reset the player's motion state
D 53036 Clears 24026-24028 and sets bytes in object slot 0 (24078=128, 24080=24081=2).

@ 53060 label=RespawnRoom
c 53060 Room to restart in after a death
R 53060 A Room died in
R 53060 O:A Room to restart in
D 53060 Unless all seven ingredients are held (56794), a death in rooms 124-127 restarts in the room paired with it at 61236 (#R61232).

@ 53087 label=Cls
c 53087 Clear the screen and attributes
D 53087 LDDR from 23296 down: zeroes 16385-23296. 16384 itself is never cleared (off by one) and 23296 is.

@ 53101 label=GameOver
c 53101 Game over
D 53101 Starts the game-over tune (24002=2), prints #R58515 and the score, waits for fire to be released then pressed, and restarts (#R52235).

i 53149

@ 53310 label=GoOutside
c 53310 Leave through an exit marked with bit 7: the trip outside
R 53310 A Map entry (bit 7 set); A AND 127 is the room
D 53310 Sets 24030, clears the play area's pixels (char rows 4-23) and sets its attributes to 70, puts object type 33 (the pumpkin flying off) in slot 0 at x=76 y=100, starts the panel heads' animation (24032=143, 24013=10) and a 105-pass countdown (24012), counted by #R52920. The main loop keeps running (objects, heads) meanwhile.

@ 53408 label=RoomExits
c 53408 Check the player against the room's edges
D 53408 IY points at the room's map entry (#R63498): left, right, down, up. x<=8: left, re-enter at x=135. x>=136: right, at x=9. y<=27: up, at y=200-height. y+height>=201: down, at y=28. A neighbour with bit 7 set goes outside (#R53310).
 53413 H is set to 0: only L (24030) is used

i 53534

@ 53534 label=SetBorder
c 53534 Set the border colour
R 53534 A Colour (bits 0-2); all registers preserved
D 53534 Keeps bits 3-7 of 24006 (the OUT (254) shadow; bit 4 is the beeper) and does not update it.

i 53550

@ 53550 label=DrawPanel
c 53550 Draw the panel (character rows 0-3)
D 53550 Six lives (24035=6): the pumpkin sprite, frame 1, at y=19 and the x positions at #R58796, through #R57415 and #R57194. Attributes of rows 0-3 to 70. "SCORE" and "MAGIC" (#R58032, #R58039), the left and right witch heads in font characters (#R61162, #R61189), the score (#R57616 adding nothing) and magic (#R57568 subtracting nothing), then the heads' eyes (#R53823, frame 53).

@ 53651 label=HeadsTick
c 53651 Animate the panel witch heads
D 53651 Runs when 24013 has counted down and 24032 is non-zero: each step draws two frames from the table at #R61216 on both heads (left at x=4 y=13, right at x=112 y=13), with a HALT and a sound step (#R53798) per frame. Bit 7 of 24032 starts a new animation.

@ 53798 label=HeadsSound
c 53798 Sound step for the heads' animation
D 53798 Preserves every register used. 24001 counts down (AND 31) and is the pitch for 52854 (sound area).

@ 53823 label=DrawHeadEyes
c 53823 XOR the heads' frames onto the panel
R 53823 A Left head's frame (the right head's is A+3)

@ 53858 label=NewGame
c 53858 Reset for a new game
D 53858 Zeroes 24000-25058 (the variables, object slots and buffers), sets the score digits (58804-58810) to '0', clears bit 7 (collected) of the 52 item rooms (#R61521), magic to "99", clears pixel lines 0-191 (#R53931), border black, clears the attributes, and sets 59582 to 252.

@ 53931 label=ClearLines
c 53931 Clear B pixel lines from line A
R 53931 A First line
R 53931 B Number of lines

; ----------------------------------------------------------------------------
; Room drawing
; ----------------------------------------------------------------------------

@ 53949 label=EnterRoom
c 53949 Enter room A: draw it, its monsters and its item
R 53949 A Room number (0-127). All registers are preserved.
D 53949 Called on entering a room (from the main loop's exits, start of game, after a death, after going outside). Clears the play area's attributes (#R54213), keeps object slot 0 (the player) at 24203 while every slot is cleared (55472), then draws 5 rows of 8 blocks of 4x4 tiles: pixels straight to the screen (#R54464), attributes into a buffer at 24225, which #R54499 copies to the screen after a HALT. Then restores the player, redraws it (#R57415, #R57058), and spawns the room's monsters (#R54264) and its item (#R54229).
 53979 IX = this room's tile-bank table (#R62954)
 53988 HL = 43750 + 40*room: the room's layout
 53998 B=4 (char row), C=0 (column); E=5 block rows
@ 54006 label=EnterRoomBlock
 54006 Each block: HL = 39654 + 16*block
 54023 4 tile rows of 4 tiles
 54033 Find the bank: the first (lo, hi, base) with lo <= tile <= hi; base 0 if none
 54078 Pixels from 34526 + 8*(base + tile)
 54092 Attribute from 48870 + ((base + tile) AND 8191)
 54108 Into the attribute buffer (24097 + offset of the screen address: row 4 is 24225)
 54151 Show the attributes after a HALT
 54154 Restore the player's slot and redraw it from its saved frame and position
 54193 Slot 0 flags = 128
 54198 Monsters
 54201 Item

@ 54213 label=ClearPlayAttrs
c 54213 Clear the play area's attributes
D 54213 22656-23295 (char rows 4-23) to 0, after a HALT. Pixels then drawn are invisible until the attribute copy (#R54499).

@ 54229 label=SpawnItem
c 54229 Spawn the room's item, if it has one not yet collected
D 54229 Looks for 24030 among the 52 room numbers at #R61521 (bit 7 set means collected, so no match). If found, spawns object type 32 in slot 5 at the position from the parallel word table #R61573 (55363, objects area).

@ 54264 label=SpawnMonsters
c 54264 Spawn the room's monsters
D 54264 The room's list is at the word table #R61677; its address is kept at 24042 for the respawner (55285). 24011 = this room's bit in 24054. List: a count, then per monster x, y and either one byte with bit 7 set (type from #R61142 by bits 0-1, one more if the room's bit is set; flags 0) or a flags byte and a type byte. Monster i goes in slot 2+i, unless its type is among the ingredients held (#R56729).

@ 54363 label=PrintString
c 54363 Print a string
R 54363 HL String address
R 54363 B Character row
R 54363 C Column
D 54363 String bytes: 36 ('$') ends; 13 starts the next row at the starting column; 128+n sets the attribute to n (24024) for what follows; '0'-'9' and 'A'-'Z' are glyphs 0-35; others are translated by #R57817. Each glyph is written to the screen (#R54464) and its attribute straight to the attribute file.
 54418 Translate through #R57817 / #R57844 (unknown characters keep their code)

@ 54464 label=DrawChar
c 54464 Copy an 8-byte character to the screen
R 54464 A Character number
R 54464 B Character row (0-23)
R 54464 C Column
R 54464 DE Base of the character set
R 54464 O:HL Screen address of the character's top line
D 54464 Copies DE+8*A to the screen at (B, C) with LD (not XOR). A, BC and DE are preserved.

@ 54499 label=ShowPlayAttrs
c 54499 Copy the attribute buffer to the screen
D 54499 After a HALT, LDIR 768 bytes from 24225 to 22656. Only 640 are the play area; the other 128 land in 23296-23423 (the printer buffer), harmlessly.

@ 54513 label=Sub54513
c 54513 Return if A=133; else (part of the player's code, which follows)
D 54513 Calls 55624 with B=24009 and copies 24029 to the object's byte 3, then falls into the player routine at 54530 (player area).

i 54530

; ----------------------------------------------------------------------------
; Low-level primitives
; ----------------------------------------------------------------------------

@ 56700 label=RoomFlag
c 56700 This room's bit in the 128-bit set at 24054
R 56700 O:A Byte 24054 + room/8
R 56700 O:C Mask: 128 >> (room AND 7)
R 56700 O:HL Address of that byte

@ 56729 label=IsHeld
c 56729 Is type A among the 7 bytes at 24070?
R 56729 A Type
R 56729 O:F Z set if found. BC, HL preserved.

i 56747

@ 56794 label=AllHeld
c 56794 Does 24070 match the 7 bytes at #R61514?
R 56794 O:F Z set if they all match (A=0)

i 56811

@ 57058 label=DrawObject
c 57058 XOR a pre-shifted object sprite onto the screen
R 57058 A Frame (for #R57194's colour)
R 57058 B Lines (from #R57415)
R 57058 C Bytes per line (from #R57415)
R 57058 D y: pixel line, 32 is the top of the play area
R 57058 E x: in 2-pixel units; byte column = x/4 - 3
R 57058 HL Pre-shifted sprite (#R57415)
D 57058 Object slots 0 and 1 (24022: the player and its spell) are drawn clipped, without colour, at #R57074. Slots 2-5 go to #R57182: unclipped, with the frame's colour XORed into the attributes.
@ 57074 label=DrawClipped
 57074 Clipped: 24038 = bytes to skip on the left, 24039 = bytes allowed before the right edge
 57121 HL = the pixel-line table #R58931 + 2*y: off-screen lines go to a sink at 24995
@ 57138 label=DrawClippedLine
 57138 One line: XOR the bytes not clipped

@ 57182 label=DrawObjectColour
c 57182 #R57194 with x-12 in E

@ 57194 label=DrawSpriteAttr
c 57194 XOR a sprite onto the screen, and its colour onto the attributes
R 57194 A Frame
R 57194 B Lines
R 57194 C Bytes per line
R 57194 D Pixel line (0-191, not clipped)
R 57194 E Byte column*4 (column = E/4 AND 31)
R 57194 HL Sprite bytes, C per line. All registers preserved.
D 57194 Then, if the frame's byte at #R60422 is non-zero, XORs it into C cells by (B/8 rounded up) rows of attributes, from the cell holding the top line. The colour covers whole cells and does not allow for a top line that is not on a cell boundary.
 57270 The attribute address from the screen address

@ 57307 label=LineAddr
c 57307 Screen address of pixel line A, column 0
R 57307 A Line (0-191), preserved
R 57307 O:HL Address
D 57307 From the character-row table #R58883.

@ 57326 label=AttrUnder
c 57326 Attribute under a screen address
R 57326 HL Screen address
R 57326 O:A Attribute
R 57326 O:DE Its address
D 57326 The game logic reads the attributes to find walls and floors.

@ 57341 label=AttrAddr
c 57341 Attribute-layout address from a screen address
R 57341 HL Screen address
R 57341 DE Base (22528 for the screen; 24097 for the room buffer at 24225)
R 57341 O:HL DE + 256*third + (L): the screen address's cell, row-major. A preserved.

@ 57355 label=IsSpecial
c 57355 Is A among the 9 bytes at 57808?
R 57355 A Byte; also stored at 24010
R 57355 O:F Z set if found

@ 57371 label=ObjectSlot
c 57371 IX = object slot A (24077 + 20*A)
R 57371 A Slot (0-5)
R 57371 O:IX Slot
R 57371 O:HL Slot

@ 57385 label=Index4
c 57385 HL = HL + 4*A
R 57385 O:DE preserved

@ 57395 label=WordAt
c 57395 HL = word at HL + 2*A
R 57395 A Index (0-127), preserved

@ 57408 label=ByteAt
c 57408 A = byte at HL + A
R 57408 O:HL HL + A

@ 57415 label=PreShift
c 57415 Copy sprite frame A to a buffer, shifted for x
R 57415 A Frame (#R59798)
R 57415 E x (shift = 2*(x AND 3) pixels)
R 57415 HL Buffer (24225 or 24427), with 2 spare bytes before it
R 57415 O:B Lines
R 57415 O:C Bytes per line (the frame's width + 1)
D 57415 Copies each line with a zero byte after it, then rotates the whole buffer right as one bit stream, one bit a pass, with the stack: DI, SP into the buffer, POP / RR L / RR H / PUSH. SP is kept at 24050, the buffer's start minus 2 at 24052. EI after, so it enables interrupts even if they were off. A, DE and HL are preserved.
 57486 Stack trick: interrupts off while SP is in the buffer

@ 57520 label=Divide
c 57520 16-bit divide (not seen called)
D 57520 BC / DE: the quotient in BC (bits rotated in through C and A), the remainder in HL.

@ 57546 label=Multiply
c 57546 HL = A * DE
R 57546 A Multiplier (0-255)
R 57546 DE Multiplicand (shifted left on return unless A=0)
R 57546 O:HL Product

@ 57568 label=SubMagic
c 57568 Subtract from the magic and print it
R 57568 DE Amount: two digits at DE+1 and DE+2
D 57568 Magic is ASCII digits at 58813-58814. Below 0 it is set to "00" and 56571 is called (the life is lost). Prints #R58812 at row 3, column 14.
R 57568 O:F C set if magic ran out

@ 57616 label=AddScore
c 57616 Add to the score and print it
R 57616 DE Count n, then n digit values, added to the last n of the 7 ASCII digits at 58804-58810
D 57616 Prints #R58803 at row 1, column 12. n=0 just prints.

@ 57664 label=Irq
c 57664 IM 2 interrupt handler (every frame)
D 57664 Steps the random pointer #R61248. If 24002 is non-zero, calls the routine at #R64019 + 2*24002 (the tunes: 1 title, 2 game over, 3 win). If 24000 is non-zero, a sound effect step (#R57714). Preserves AF, HL, DE, BC, IX, IY, not the alternate set.

@ 57714 label=IrqEffect
c 57714 Sound effect step
D 57714 Decrements 24000 and plays 52854 (sound area) with pitch ((24000) AND 31) + 50.

; ----------------------------------------------------------------------------
; Tables used by the core
; ----------------------------------------------------------------------------

@ 57726 label=ReadControlsVector
b 57726 The controls reader
D 57726 Address that 52767 jumps to: 52658 (Kempston) or 52695 (key table #R57784). Either returns A: bit 0 right, 1 left, 2 down, 3 up, 4 fire, 6 abort.
W 57726,2
b 57728 Keyboard half-row ports, for defining keys
W 57728,16,2
b 57744 Kempston bits to control bits
B 57744,16,8
@ 57760 label=KeysInterface2
b 57760 Default key table (Interface II): 6 entries of port, mask, bit
B 57760,24,4
@ 57784 label=KeyTable
b 57784 Key table in use: port (2 bytes), mask, bit to set
B 57784,24,4
b 57808 Bytes tested by #R57355
B 57808,9
@ 57817 label=FontXlat
t 57817 Characters translated by #R54363
@ 57844 label=FontXlatGlyph
b 57844 Glyph numbers for #R57817
B 57844,27,9
i 57871
t 57872 Menu
i 57941

@ 58032 label=TxtScore
t 58032 Panel: "SCORE" (attribute 68)
@ 58039 label=TxtMagic
t 58039 Panel: "MAGIC" (attribute 66)
i 58046
@ 58515 label=TxtGameOver
t 58515 Game over text (#R53101)
i 58666
@ 58776 label=AttractTexts
b 58776 Attract loop pages: string addresses, then their (column, row) words
W 58776,8,2
i 58784
@ 58796 label=LifeXs
b 58796 Lives on the panel: y, then the x of each of six
B 58796,7
@ 58803 label=TxtScoreValue
b 58803 Score string: attribute, 7 ASCII digits, attribute, '$'
B 58803,9
@ 58812 label=TxtMagicValue
b 58812 Magic string: attribute 5, 2 ASCII digits, '%', '$'
B 58812,5
i 58817
@ 58835 label=MagicNone
b 58835 Magic delta of 0 (redraw only)
B 58835,3
i 58838
@ 58883 label=CharRowAddr
b 58883 Screen address of each character row's top line
W 58883,48,2
@ 58931 label=LineAddrClip
b 58931 Screen address of each pixel line, for the clipped draw
D 58931 Index by y (0-231). Lines 0-31 (the panel) and 192-231 point at 24995, a sink in the variables, so the player is clipped at the top and bottom of the play area; lines 32-191 at the screen.
W 58931,464,16
i 59395

@ 59798 label=FrameTable
b 59798 Sprite frames: width (bytes), height (lines), address of the bytes
D 59798 155 frames, plus a 0x0 one (154). Bytes are row-major, width per line, no mask (drawn by XOR). Their data is 25900-34525.
B 59798,624,4
@ 60422 label=FrameAttr
b 60422 Sprite frames' attribute (0 = none), XORed by #R57194
B 60422,156,12
i 60578

@ 61142 label=MonsterTypes
b 61142 Monster types for one-byte entries (#R54264)
B 61142,4
i 61146
@ 61162 label=TxtLeftHead
t 61162 The left witch head, in font characters
@ 61189 label=TxtRightHead
t 61189 The right witch head, in font characters
@ 61216 label=HeadFrames
b 61216 Witch heads' animation frames (#R53651)
B 61216,16
@ 61232 label=RespawnFrom
b 61232 Rooms whose deaths restart elsewhere, and where (#R53060)
B 61232,8,4
@ 61240 label=StartRooms
b 61240 The eight start rooms
B 61240,8
@ 61248 label=RandPtr
b 61248 Random pointer: a byte read through it gives the start room
W 61248,2
@ 61250 label=RoomStartPos
b 61250 Player start position per room (x, y)
B 61250,256,8
i 61506
@ 61514 label=WinIngredients
b 61514 The seven ingredient types to hold (#R56794)
B 61514,7
@ 61521 label=ItemRooms
b 61521 Rooms of the 52 items; bit 7 set once collected
B 61521,52,13
@ 61573 label=ItemPos
b 61573 Item positions (x, y), parallel to #R61521
B 61573,104,8
@ 61677 label=MonsterLists
b 61677 Monster list per room (#R54264)
W 61677,256,8
B 61933,1021,8

@ 62954 label=RoomBanks
b 62954 Tile-bank table per room
D 62954 Each room's list (16 distinct lists, 63210-63497): a count, then (lo, hi, base) with base a word. A tile byte from lo to hi inclusive becomes tile number base + byte; the first match wins; no match is base 0. Bases may be negative (mod 8192).
W 62954,256,8
B 63210,288,8
@ 63498 label=RoomMap
b 63498 Room map: per room, the room left, right, below and above
D 63498 Bit 7 set: the exit goes outside (#R53310) to room AND 127 (245 to 117, 238 to 110).
B 63498,512,4
i 64010
@ 64019 label=IrqTunes
b 64019 Per-frame tune routines for 24002 = 1, 2, 3 (entry 0 unused)
W 64019,8,2
i 64027
b 65021 Interrupt vector target: JP 57664, written at startup (#R52180)
B 65021,3
b 65024 IM 2 vector table, all 253, written at startup
B 65024,257,16
i 65281
