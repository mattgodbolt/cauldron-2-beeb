; Cauldron II (ZX Spectrum): the player. See docs/research/player.md.
; Only the player's routines and tables; the gaps are ignored.
@ 52658 label=READ_KEMPSTON
c 52658 Read the controls from a Kempston joystick
D 52658 Returns the control bits in A: 1 up, 2 down, 4 left, 8 right, 16 fire, 64 abort (A alone on half-row A-G). Preserves BC, DE.
R 52658 O:A Control bits
C 52660 Kempston: R=1 L=2 D=4 U=8 F=16
C 52663 Remap the directions through KEMPSTON_MAP (opposites cancel)
C 52672 Add the fire bit
C 52677 Abort if exactly A is pressed on half-row A-G
@ 52695 label=READ_KEYS
c 52695 Read the controls from the keyboard (Interface II by default)
D 52695 Reached only through the pointer at 57726, so the executed-code maps miss it. Walks the six (port, mask, bit) entries at KEYS; opposite directions cancel. Preserves IX, DE, BC.
R 52695 O:A Control bits
C 52707 OR in the result bit of each pressed key
C 52739 Left and right together cancel
C 52750 Up and down together cancel
@ 52767 label=READ_CONTROLS
c 52767 Read the controls through the selected reader
D 52767 Pushes CHECK_ABORT as the return address and jumps through 57726 (READ_KEMPSTON or READ_KEYS).
R 52767 O:A Control bits
@ 52775 label=CHECK_ABORT
c 52775 Abort the game if bit 6 is set
D 52775 Jumps to the menu (52235, which resets SP) on abort, else returns A unchanged.
@ 52781 label=SFX_START
c 52781 Start a sound effect
R 52781 I:HL Effect: [start, end, step]... 255
@ 52791 label=SFX_STEP
c 52791 Play one step of the current sound effect
D 52791 Called once per object per pass from 55801.
@ 52854 label=BEEP
c 52854 Beep one tone on the beeper
D 52854 Self-modifies a jump into the run of NOPs at 52888.
i 52920
@ 53036 label=RESET_PHYSICS
c 53036 Reset the player's bounce
D 53036 v, level and flips to 0; direction down, dx 2, script 128 (steered by the player code).
i 53060
@ 53149 label=TICK_REVERSE
c 53149 Count down the reversed-controls timer
D 53149 Clears rev_mask (24016) when rev_timer (24015) reaches 0.
@ 53163 label=FIRE
c 53163 Fire a bolt
D 53163 Needs no warp, not the landing pass, can_fire (24017) set, a direction pressed and object 1 free. Costs 1% magic.
C 53185 Self-modify the bolt script's direction byte
C 53188 Object 1's script byte: fire if 0 or negative
C 53199 Spawn object 1 at the player with script 2, state 32
C 53214 Magic -1
@ 53221 label=LANDED
c 53221 The squash pass: choose the next bounce
D 53221 Runs while the player's state is 4. Fire raises the level (max 2, bit 7 set); no fire clears bit 7 or lowers the level. v = LAUNCH_V[level]; the new direction is kept in 24029.
R 53221 I:IX Player object (24077)
C 53230 No fire: clear bit 7, or level - 1
C 53247 v = LAUNCH_V[level]
C 53258 land_dir = (dir AND 3) OR edge OR ((rev_mask XOR controls) AND 12)
C 53295 Fire: level + 1 (max 2), set bit 7
@ 53310 label=WARP
c 53310 Leave the map through an exit byte >= 128
D 53310 Blanks the play area and shows the pumpkin shrinking (object 0, state 33) for 105 passes; 52920 then places the player in room A AND 127.
R 53310 I:A Exit byte (128 + room)
@ 53408 label=CHECK_EXITS
c 53408 Move to a neighbouring room when the player reaches an edge
D 53408 IY = EXITS + 4*room: left, right, down, up. X <= 8, X >= 136, Y <= 27, Y + h >= 201, tested in that order.
@ 53464 label=EXIT_LEFT
@ 53480 label=EXIT_RIGHT
@ 53496 label=EXIT_DOWN
@ 53512 label=EXIT_UP
i 53534
@ 54513 label=PLAYER_ANIM_DONE
c 54513 The player physics, run once per pass
D 54513 54513: the animation ended (state bit 7): resume state land_state with land_dir, unless dead (133).
D 54513 54530 (PLAYER, called from the main loop): apply the flips in 24028, then move up (MOVE_UP), down (MOVE_DOWN) or test walls only.
@ 54530 label=PLAYER
C 54539 State negative: animation ended
C 54546 State 5: dead
C 54549 State 4: squash pass
C 54557 Flips: bits 0/1 swap up and down
C 54596 Flip bit 2 swaps left and right
@ 54631 label=MOVE_DOWN
C 54631 C = first row below the sprite
C 54641 B = STEP_ROWS[v]
C 54655 Test each row downwards
C 54687 No hit: v + 1, max 9
C 54699 dy = rows; direction down
C 54712 level = 0 (v <= 4), 1 (v <= 6), 2
@ 54746 label=LANDING
C 54746 Landed on attribute 1: death
C 54754 Flip vertical next pass
C 54762 dy = rows - 1; state 4 (squash)
C 54769 land_state = (edge >> 2) + 1
@ 54799 label=TEST_WALLS
c 54799 Test for a wall beside the moved sprite
D 54799 54799: going up (A = Y - dy + 7). 54807: A = the row to start at.
@ 54807 label=TEST_WALLS_AT
C 54827 Right: column X + dx + 8
C 54849 Solid: flip, state 3, sound
C 54867 Left: column X - dx - 1
C 54888 Solid: flip, state 2, sound
@ 54906 label=TEST_COLUMN
c 54906 Test one X unit on five rows for a lit pixel
R 54906 I:A X unit
R 54906 I:B Rows (5)
R 54906 I:C First row
R 54906 O:HL Screen byte where a pixel was found (NZ)
@ 54970 label=TEST_ROW
c 54970 Test a row under or over the sprite: centre, then feet
R 54970 I:C Row tested +1 (down) or -1 (up), for the 33..190 range test
R 54970 I:HL Address of column 0 of the row tested
R 54970 O:F NZ if blocked
C 54984 Centre X+3..X+5: hit_attr; solid blocks
C 55010 Left foot X+1, X+2: edge bit 3
C 55051 Right foot X+6: edge bit 2
C 55082 One foot only blocks; both or neither do not
@ 55095 label=TEST_UNITS
c 55095 Test B consecutive X units on the row at (24040)
R 55095 I:A First X unit
R 55095 I:B Count
R 55095 O:HL Screen byte where a pixel was found (NZ)
@ 55131 label=MOVE_UP
c 55131 Move the player up
C 55131 B = STEP_ROWS[v], start at row Y - 1
C 55153 Test each row upwards
C 55187 No hit: v - 1; at 0 flip (peak)
C 55230 level = 2 (v >= 9), 1 (v >= 6), 0
@ 55261 label=HIT_CEILING
C 55261 Hit: dy = rows (overlaps the ceiling by one), flip
i 55285
@ 56571 label=KILL_PLAYER
c 56571 Kill the player
D 56571 State 5 (explosion), stop the object, start the death countdown (70 passes) and the panel witches.
i 56601
@ 57326 label=ATTR_AT
c 57326 Get the attribute of a screen byte
R 57326 I:HL Screen address
R 57326 O:A Attribute
R 57326 O:DE Attribute address
i 57341
@ 57355 label=IS_SOLID
c 57355 Is an attribute solid?
D 57355 Searches SOLID_ATTRS. Preserves A, BC, HL.
R 57355 I:A Attribute
R 57355 O:F Z if solid
i 57371
@ 57726 label=CONTROL_READER
w 57726 Address of the control reader (READ_KEMPSTON or READ_KEYS)
i 57728
@ 57744 label=KEMPSTON_MAP
b 57744 Kempston direction nibble to control bits
@ 57760 label=DEFAULT_KEYS
b 57760 Interface II keys: port (2 bytes), mask, bit for up, down, left, right, fire, abort
B 57760,24,4
@ 57784 label=KEYS
b 57784 The keys in use (same layout as DEFAULT_KEYS)
B 57784,24,4
@ 57808 label=SOLID_ATTRS
b 57808 Attributes whose lit pixels are solid
D 57808 Bright blue, red, magenta, green, cyan; white, blue (water: deadly on landing), yellow; green on blue.
i 57817
@ 58880 label=FIRE_COST
b 58880 Magic cost of a bolt (digits 0, 1)
i 58883
@ 59450 label=BOLT_SCRIPT
b 59450 Script 2, the bolt: direction (self-modified by FIRE), 10 passes, dx 7, dy 7; 253 ends it
i 59456
@ 61145 label=STEP_ROWS
b 61145 Rows moved per pass, by v
@ 61155 label=LAUNCH_V
b 61155 v at take-off, by bounce level (also the level thresholds)
@ 61158 label=PIXEL_MASKS
b 61158 Pixel-pair masks for X units 0-3 within a byte
i 61162
@ 61250 label=START_POS
b 61250 Player start position per room: X, Y
B 61250,256,2
i 61506
@ 63498 label=EXITS
b 63498 Exits per room: left, right, down, up (>= 128: warp to room AND 127)
B 63498,512,4
i 64010
@ 64010 label=SFX_BOUNCE
b 64010 Bounce sound: start, end, step; 255
i 64014
