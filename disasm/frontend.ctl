; Cauldron II (ZX Spectrum): front end, text, panel. See docs/research/frontend.md.
;
@ 49511 label=font
b 49511 The font: 64 glyphs of 8 bytes, top row first
D 49511 Glyphs 0-9 are the digits, 10-35 A-Z, 36 '%', 37 space, 38-57 the pieces of the two witch faces in the panel's corners, 59 the copyright sign; #R57817 maps the other characters. Shared with Cauldron 1's panel font.
  49511,512,8
i 50023
@ 52180 label=cold_start
c 52180 Entry point (cold start)
D 52180 Builds the IM 2 vector table (65024-65280 all 253, so the vector is 65021) and puts JP 57664 at 65021; border 0; copies the default key table (#R57760, the Interface II keys) to the active one (#R57784). Runs once: later restarts enter at #R52235, so redefined keys survive a game.
  52211,7 Border 0, and 24006 (the border colour the effects OUT) = 0
  52218,11 Active keys = default keys
b 52232 JP 57664, copied to 65021
@ 52235 label=warm_start
c 52235 Warm start: title music, menu, credits
D 52235 Entered from #R52180, from the abort key (#R52775), after game over (#R53101) and after the win (#R56819). Seeds 61248 (the random number pointer) from R, resets the three tune players (border byte 0, tempo 250), plays tune 1's first tick, sets 24002 = 1 so the interrupt plays tune 1, clears the screen and runs the menu. Then it cycles the two credits pages until fire, and starts a game at 52372.
  52235,3 SP = 0 (the stack is reset on every restart)
  52244,7 24007 (page countdown) = 0, 24008 (page) = 0
  52251,21 Tune players: border byte 0, tempo 250 (#R50124, #R51424, #R51874)
  52272,3 Restart tune 1 and play its first tick
  52275,5 24002 = 1: the interrupt plays tune 1
  52281,3 Clear the screen
  52284,3 The menu (returns on 1-4)
@ 52290 label=credits_loop
  52290,6 Page countdown not 0: just wait
  52296,3 Clear the screen
  52299,17 HL = page text (#R58776), BC = its row and column (#R58780)
  52316,5 Print it with interrupts off (the music pauses)
  52321,5 Show it for 50 passes
  52326,12 Flip the page (0, 1)
  52338,7 Step the random pointer every pass
  52345,8 Delay: 10000 counts
  52353,3 Read the input (the abort key restarts here)
  52356,4 Fire: start the game
  52360,10 Count the page down
i 52372
@ 52481 label=menu
c 52481 The menu
D 52481 Prints the menu and waits for 1, 2, 3 or 4 (half-row 63486, keys 1-5). 1 selects the Kempston reader; 2 the keyboard reader with the default keys (Interface II's 6-0); 3 lets the player define six keys, then selects the keyboard reader; 4 returns with the reader unchanged (at power-on the keyboard reader with the Interface II keys). Every choice returns to the credits.
  52481,9 Print #R57872 at row 1, column 10
@ 52493 label=menu_wait
  52508,3 4: play with the current reader
@ 52513 label=menu_kempston
  52513,7 1: Kempston (#R52658)
@ 52520 label=menu_if2
  52520,18 2: active keys = default keys; keyboard reader (#R52695)
@ 52538 label=menu_define
  52538,10 3: wait until 1-5 are all released
  52548,9 Print DEFINE KEYS at row 12, column 10
  52557,7 For each of the six keys (UP DOWN LEFT RIGHT FIRE/BOUNCE ABORT GAME)
  52566,12 Print its prompt at row 14, column 10
  52578,3 Wait for a key
  52581,9 Store its port and mask; the action bit (byte 3) stays the default's
  52603,7 Keyboard reader
@ 52610 label=wait_key
c 52610 Wait for a key
R 52610 O:BC Port of the key's half-row
R 52610 O:A The keys held in that half-row (bits 0-4; more than one if several are held)
D 52610 Scans the eight half-rows (#R57728) in turn until one has a key down. The key must read as held 256 times in a row, then as released 256 times in a row, before it counts. Any key will do, including one already chosen.
@ 52658 label=read_kempston
c 52658 Input reader: Kempston joystick
R 52658 O:A Input bits: 0 up, 1 down, 2 left, 3 right, 4 fire, 6 abort
D 52658 Maps the joystick's direction bits through #R57744 and keeps fire (bit 4). Abort is the A key, alone in its half-row.
  52677,14 A, alone of A S D F G: abort
@ 52695 label=read_keys
c 52695 Input reader: keyboard (Interface II or defined keys)
R 52695 O:A Input bits, as #R52658
D 52695 Reads each of the six entries of #R57784 (port, key mask, action bit) and ORs in the action bits of the keys held. Up with down, or left with right, cancel each other.
@ 52767 label=read_input
c 52767 Read the input through the current reader
R 52767 O:A Input bits: 0 up, 1 down, 2 left, 3 right, 4 fire, 6 abort
D 52767 Calls the reader whose address is at #R57726 and returns through #R52775, which restarts the game at the menu if the abort bit is set. Used in the credits, in play and on the game-over and win screens.
@ 52775 label=check_abort
c 52775 Abort: back to the title
R 52775 A Input bits (kept; the flags are BIT 6's)
i 52781
@ 53087 label=cls
c 53087 Clear the screen
D 53087 Zeroes 23296 down to 16385 by LDDR: pixels and attributes (and 23296, one past them), but not 16384, the top-left byte, which is never cleared.
@ 53101 label=game_over
c 53101 Game over
D 53101 Entered from 52975 when the lives (24035) go below 0. Restarts tune 3 and sets 24002 = 2 so the interrupt plays it, prints the game-over verse and the score, then waits for fire to be released and pressed, and restarts at #R52235.
  53101,9 Tune 3, from its start; 24002 = 2
  53114,9 Print #R58515 at row 3, column 6
  53123,9 Print the score (#R58803) at row 21, column 16
  53132,14 Wait for fire up, then fire down
i 53149
@ 53550 label=panel_init
c 53550 Draw the panel for a new game
D 53550 Lives = 6 and six pumpkin icons (sprite frame 1 at row #R58796, the x positions after it), the top four character rows' attributes = 70 (bright yellow on black), then SCORE, MAGIC, the two witch faces as text, the score (adding 0), the magic (subtracting 0), and the witches' mouths at rest (frame 53).
  53550,5 Lives (24035) = 6
  53555,32 Draw the pumpkins
  53587,11 Panel attributes (rows 0-3) = 70
  53598,9 SCORE at row 0, column 13
  53607,9 MAGIC at row 2, column 13
  53616,9 Left witch at row 0, column 0
  53625,11 Print the score and the magic
  53636,9 Right witch at row 0, column 28
  53645,5 Mouths at rest
@ 53651 label=witch_anim
c 53651 Animate the witches' mouths after a room change
D 53651 Called once per main-loop pass. A room change (53310) sets 24013 = 10 (a delay in passes) and 24032 = 143 (bit 7 = start, 15 steps). Each step draws the next mouth frames from #R61216 into both faces with two HALTs and four cackle pulses (#R53798), then waits one pass (24033).
  53651,11 Delay before it starts
  53662,5 Nothing to do
  53667,15 Start: clear bit 7, 24033 = 0, 24001 (the cackle's effect number) = 0
  53682,11 Wait a pass between steps
@ 53693 label=witch_step
  53693,31 New frames (left face at 3332, using #R61216's entry and the one before)
  53724,19 Cackle, wait a frame, XOR the old ones off
  53743,28 The same for the right face (at 3440, frames + 3)
  53787,10 Next step; wait one pass
i 53798
@ 53823 label=witch_mouths
c 53823 Draw the witches' mouths
R 53823 A Sprite frame for the left mouth (the right one is A + 3)
@ 53858 label=new_game_init
c 53858 Reset the game state for a new game
D 53858 Zeroes 24000-25058 (the game's variables and sprite buffers), the score to 0000000, clears bit 7 of 52 bytes at 61521, magic to 99, clears the pixels, border 0 and attributes 0.
  53861,11 Zero 24000-25058
  53872,10 Score digits = 0000000 (ASCII)
  53894,8 Magic = 99
  53902,6 Clear the 192 pixel rows
  53908,4 Border 0
  53912,13 Attributes 0
@ 53931 label=clear_rows
c 53931 Clear B pixel rows from row A
i 53949
@ 54363 label=print
c 54363 Print a string
R 54363 HL String
R 54363 B Character row (0-23)
R 54363 C Column (0-31)
D 54363 '$' ends the string; 13 goes to the next row, back to the first column; a byte of 128 or more sets the attribute (byte AND 127, kept in 24024) for the characters after it. 0-9 and A-Z are glyphs 0-35; other characters go through #R57817. Each character's 8 bytes go straight onto the screen (no XOR) and its attribute cell is set.
  54364,7 '$': done
  54371,10 13: next row, same start column
  54381,13 Attribute byte
  54394,24 Digits and capitals
  54418,24 Other characters: #R57817
@ 54442 label=print_glyph
  54442,7 Draw the glyph
  54449,10 Set its attribute
@ 54464 label=draw_glyph
c 54464 Draw a glyph at a character cell
R 54464 A Glyph number
R 54464 DE Font (#R49511)
R 54464 B Character row
R 54464 C Column
D 54464 Row addresses from #R58883. Preserves everything but HL, which is left at the cell's screen address.
i 54499
@ 56811 label=win
c 56811 The win check and the win sequence
D 56811 Reached through the table at 61131. If the seven bytes at 24070 don't match 61514's, the pumpkin dies (56571). Otherwise: +100 to the score, restart tune 2 and set 24002 = 3 so the interrupt plays it, print the win text and the score, wait for fire to be released and pressed, and restart at #R52235.
  56811,6 Not complete: lose a life
  56817,6 +100 (#R58850)
  56823,10 Tune 2, from its start; 24002 = 3
  56836,9 Print #R58666 at row 6, column 6
  56845,9 Print the score at row 12, column 16
i 56871
@ 57568 label=magic_sub
c 57568 Subtract from the magic
R 57568 DE Record: a byte (not read here), then two digits (#R58835)
D 57568 Subtracts the two digits from the magic (ASCII digits at 58813-58814). If it goes below 0, the magic is set to 00 and the pumpkin dies (56571). Prints the magic at row 3, column 14.
R 57568 O:F Carry if the magic ran out
@ 57616 label=score_add
c 57616 Add to the score
R 57616 DE Record: n, then n digits (#R58835)
D 57616 Adds the record's n digits, right-aligned, to the seven ASCII digits at 58804-58810 (no carry out of the top digit), then prints the score at row 1, column 12. n = 0 just prints.
i 57664
@ 57726 label=input_reader
w 57726 Address of the input reader (#R52658 Kempston or #R52695 keyboard)
@ 57728 label=key_ports
w 57728 The eight keyboard half-row ports, for #R52610
@ 57744 label=kempston_map
b 57744 Kempston direction bits (right 1, left 2, down 4, up 8) to the game's (up 1, down 2, left 4, right 8)
@ 57760 label=keys_default
b 57760 Default keys (Interface II port 1 = keys 6-0): six entries of port (2 bytes), key mask, action bit
  57760,4 9: up
  57764,4 8: down
  57768,4 6: left
  57772,4 7: right
  57776,4 0: fire
  57780,4 A: abort
@ 57784 label=keys_active
b 57784 Active keys, as #R57760 (copied from it at the cold start; option 3 overwrites the ports and masks)
  57784,24,4
i 57808
@ 57817 label=char_codes
t 57817 Characters the printer looks up (27), other than 0-9 and A-Z
D 57817 Lower-case e-x select the witch-face glyphs; '@' is the copyright sign.
@ 57844 label=char_glyphs
b 57844 The glyph for each character of #R57817
D 57844 A character missing from #R57817 prints as the glyph its own code gives (never happens).
@ 57872 label=menu_text
t 57872 The menu
@ 57941 label=define_text
t 57941 DEFINE KEYS
@ 57954 label=key_prompts
t 57954 The six key prompts
  57954,13
  57967,13
  57980,13
  57993,13
  58006,13
  58019,13
t 58032 SCORE
t 58039 MAGIC
@ 58046 label=credits_text
t 58046 Credits page (page 0)
@ 58301 label=instructions_text
t 58301 The verse (page 1)
@ 58515 label=game_over_text
t 58515 The game-over verse
@ 58666 label=win_text
t 58666 The win text
@ 58776 label=pages
w 58776 Credits pages' texts
w 58780 Credits pages' positions (B row, C column)
@ 58784 label=key_prompt_ptrs
w 58784 The key prompts, in action-bit order
@ 58796 label=pumpkin_icons
b 58796 Lives icons: the sprite row, then the six x positions (by life number)
@ 58803 label=score_text
t 58803 The score: attribute 195, seven ASCII digits
@ 58812 label=magic_text
t 58812 The magic: attribute 133, two ASCII digits, '%'
@ 58817 label=score_values
w 58817 Score records by points class (monster table bits 0-3, 56381)
@ 58835 label=score_records
b 58835 Score and magic records: n, then n decimal digits
  58835,3 0 (print only; also subtracts 00 from the magic)
  58838,3 2,0,5 (unused)
  58841,3 -08 magic (56402, when a monster dies)
  58844,3 2,1,0 (unused)
  58847,3 +10
  58850,4 +100
  58854,4 +200
  58858,4 +300
  58862,4 +500
  58866,4 +750
  58870,5 +1000
  58875,5 +5000
  58880,3 -01 magic (a shot)
@ 58883 label=char_rows
w 58883 Screen address of each character row's top pixel line
i 58931
@ 61162 label=witch_left
t 61162 The left witch's face (row 0, column 0), drawn as text
@ 61189 label=witch_right
t 61189 The right witch's face (row 0, column 28)
@ 61216 label=witch_frames
b 61216 Mouth frames for #R53693, by step (15 down to 0): 53 closed, 54 and 55 open
i 61232
