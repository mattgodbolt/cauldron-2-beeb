; Cauldron II (ZX Spectrum): sound. See docs/research/sound.md.
;
; Three copies of one two-channel beeper player, each with its own tune:
;   tune 1 (title/menu)  50100   IRQ mode 1 (24002 = 1)
;   tune 2 (win)         51400   IRQ mode 3
;   tune 3 (game over)   51850   IRQ mode 2
; Copies 2 and 3 are byte-for-byte copy 1 relocated (only the addresses
; differ), so only copy 1 is commented in full.
;
@ 50100 label=mus1_start
c 50100 Tune 1: restart the tune and play its first tick
D 50100 Resets both channel pointers to one byte before their data (they are pre-incremented), plays one tick, then falls into the tail the IRQ handler enters at #R50113.
D 50100 Called by #R52235 (warm start) with 24002 = 0; afterwards the IRQ handler (#R57664) plays one tick per interrupt through #R50113 while 24002 = 1.
  50100,6 Channel 1 pointer = 50365
  50106,6 Channel 2 pointer = 50879
@ 50113 label=mus1_tick
  50113,3 Entry from the IRQ handler (mode 1): play one tick
  50116,3 Scan the keyboard (ROM KEY-SCAN): E = 255 if no key
  50119,1 Z if no key
  50120,2 Disabled loop: as 28,247 this would be JR Z,50113 (play until a key); as 62,247 it is LD A,247, so one tick per call
  50122,2 The IRQ handler's interrupts come back on here, before its own RETI
@ 50124 label=mus1_vars
b 50124 Tune 1 player's variables
D 50124 The snapshot's values here are stale: #R52235 sets 50126 and 50135, #R50100 the pointers.
  50124,1 Channel 1's current note
  50125,1 Channel 2's current note
  50126,1 Value OUT to 254 with the speaker bit clear (border 0, MIC 0); set to 0 by #R52235
W 50127,2 Channel 1 pointer (pre-incremented)
W 50129,2 Channel 1 loop address (50366, the first note)
W 50131,2 Channel 2 pointer
W 50133,2 Channel 2 loop address (50880)
  50135,1 Tempo: the tick runs (256 - this) * 256 loop iterations; set to 250 by #R52235
@ 50136 label=mus1_next
c 50136 Advance one channel's pointer and fetch its note
R 50136 HL Address of the channel's pointer
R 50136 O:A The note (signed semitone, -12..41)
  50140,5 64 ends the stream
  50145,4 Store the advanced pointer
@ 50149 label=mus1_period
c 50149 Period of a note
R 50149 HL Address of the note
R 50149 O:H Half-period in loop iterations (1 = rest)
R 50149 O:L 1 (the counter, so the first flip comes on the first iteration)
R 50149 O:E Note + 12 (the table index; the caller tests its bit 7)
  50155,3 Table #R50312 (its last entry, 50365, is the 1 just before the channel 1 data)
@ 50163 label=mus1_loop
c 50163 End of stream: go back to the channel's loop address
  50163,6 DE = loop address (the word after the pointer)
  50169,2 Fetch the note there (a stream of only 64 would hang)
@ 50171 label=mus1_play
c 50171 Play one tick of tune 1
D 50171 Fetches both channels' next notes and plays them together for one tick. The loop is 96 T-states on every path, so the pitch doesn't depend on which channel flips: a channel with half-period P flips the speaker bit (bit 4) every P iterations, f = 3500000 / (2 * 96 * P). The two channels OUT alternately, once each per iteration, which mixes them.
D 50171 Registers in the loop: E counts channel 1 down (reloaded from IXh), L counts channel 2 down (reloaded from H), A' is channel 1's output byte and A channel 2's, D = 16 (the speaker bit), B and C count the tick's iterations.
  50195,5 Never taken: the notes are -12..41, so bit 7 of note + 12 is never set
  50208,8 Both channels at period 1 (rest): play the silent delay instead
  50216,4 C = tempo: 256 - C outer passes of 256 iterations
  50222,7 Both output bytes start at the border byte (speaker bit clear)
  50229,2 IXh = channel 1's period
@ 50233 label=mus1_loop96
  50235,4 Channel 1: count down, OUT its byte
  50239,2 Not yet: on to channel 2 (via the timing pad at 50264)
  50241,3 Reload channel 1's counter and flip its speaker bit
  50245,4 Channel 2: count down
@ 50249 label=mus1_ch2flip
  50249,4 Channel 2: OUT, reload, flip
  50253,2 Next iteration
  50255,4 Next outer pass (C counts up to 0)
@ 50260 label=mus1_sig
t 50260 The programmer's mark, in all three copies
c 50264 The loop's other half (padding keeps every path at 96 T-states)
  50264,2 Never taken (Z is clear here): a 7 T-state pad
@ 50271 label=mus1_ch2out
@ 50282 label=mus1_rest
c 50282 Rest tick: both channels silent
D 50282 Delays (255 - tempo) * 256 passes of 93 T-states (119040 T at tempo 250) with no OUT. SRA (HL) on HL = 0 writes to ROM: a no-op for its timing.
@ 50312 label=mus1_periods
b 50312 Period table (half-periods in loop iterations, indexed by note + 12)
D 50312 53 entries from 255 down to 12, a semitone apart; the 54th, period 1 (note 41 = rest), is the byte at 50365 before the channel 1 data. The three copies' tables are identical.
  50312,53,13
@ 50365 label=tune1_ch1
b 50365 Tune 1 (title/menu), channel 1
D 50365 One byte per tick: a signed note number (-12..41, 41 a rest), 64 = end (loop to #R50366). 512 ticks.
  50365,1 Doubles as the period table's last entry (1 = rest)
  50366,512,16 Notes
  50878,1 End
@ 50879 label=tune1_ch2
b 50879 Tune 1, channel 2
  50879,1 Skipped (the pointer is pre-incremented)
  50880,512,16 Notes (bytes over 127 are negative)
  51392,1 End
b 51393 Unused
@ 51400 label=mus2_start
c 51400 Tune 2 (win): restart the tune and play its first tick
D 51400 A relocated copy of #R50100; called by the win sequence (#R56819) before it sets 24002 = 3.
@ 51413 label=mus2_tick
  51413,3 Entry from the IRQ handler (mode 3)
  51416,6 Where copy 1 has its key scan
@ 51424 label=mus2_vars
b 51424 Tune 2 player's variables (as #R50124)
W 51427,4
W 51431,4
@ 51436 label=mus2_next
c 51436 Copy of #R50136
@ 51449 label=mus2_period
c 51449 Copy of #R50149
@ 51463 label=mus2_loop
c 51463 Copy of #R50163
@ 51471 label=mus2_play
c 51471 Copy of #R50171: play one tick of tune 2
  51495,5 Never taken (the jump goes into the tune data, like copy 1's)
t 51560 Copy of #R50260
c 51564 Copy of #R50264
@ 51582 label=mus2_rest
c 51582 Copy of #R50282
@ 51612 label=mus2_periods
b 51612 Period table (copy of #R50312)
  51612,53,13
@ 51665 label=tune2_ch1
b 51665 Tune 2 (win), channel 1: 90 ticks
  51665,1 Period table's last entry
  51666,90,15 Notes
  51756,1 End
@ 51757 label=tune2_ch2
b 51757 Tune 2, channel 2
  51757,1 Skipped
  51758,90,15 Notes
  51848,1 End
  51849,1 Unused
@ 51850 label=mus3_start
c 51850 Tune 3 (game over): restart the tune and play its first tick
D 51850 A relocated copy of #R50100; called by the game-over sequence (#R53101) before it sets 24002 = 2.
@ 51863 label=mus3_tick
  51863,3 Entry from the IRQ handler (mode 2)
@ 51874 label=mus3_vars
b 51874 Tune 3 player's variables (as #R50124)
W 51877,4
W 51881,4
@ 51886 label=mus3_next
c 51886 Copy of #R50136
@ 51899 label=mus3_period
c 51899 Copy of #R50149
@ 51913 label=mus3_loop
c 51913 Copy of #R50163
@ 51921 label=mus3_play
c 51921 Copy of #R50171: play one tick of tune 3
t 52010 Copy of #R50260
c 52014 Copy of #R50264
@ 52032 label=mus3_rest
c 52032 Copy of #R50282
@ 52062 label=mus3_periods
b 52062 Period table (copy of #R50312)
  52062,53,13
@ 52115 label=tune3_ch1
b 52115 Tune 3 (game over), channel 1: 26 ticks, a falling chromatic scale
  52115,1 Period table's last entry
  52116,26,13 Notes
  52142,1 End
@ 52143 label=tune3_ch2
b 52143 Tune 3, channel 2: the same scale a semitone higher
  52143,1 Skipped
  52144,26,13 Notes
  52170,1 End
  52171,9 Unused
i 52180
@ 52781 label=sfx_start
c 52781 Start a sound-effect sweep
R 52781 HL Sweep descriptor (#R64010 bounce, #R64014 collect)
D 52781 The sweep then plays one pulse per pass of the main loop, from #R52791. A new call restarts it.
@ 52791 label=sfx_step
c 52791 Play the next pulse of the current sweep
D 52791 Called once per pass of the main loop (from 55783). A descriptor is a list of 3-byte records (first, last, step); the sweep plays effect number first, then adds step while the number stays within first..last (unsigned). When it leaves, it moves to the next record, or ends if the byte after the record is 255. 24003-24004 = record pointer (0 = none), 24005 = current effect number.
  52805,6 Advance by the step
  52814,10 Still within first..last: done
  52824,5 255 after the record: end of the sweep
  52831,15 Next record: start at its first number
  52847,6 Sweep over
@ 52854 label=sfx_pulse
c 52854 One speaker pulse
R 52854 A Effect number (index into #R64027)
D 52854 Raises the speaker bit, waits about 4 * v T-states (v = the table's word for A), and lowers it again: one pulse. All in-game effects are trains of these pulses, so their pitch is the rate of the calls and the width sets the timbre.
D 52854 Self-modifying flow: the fine delay (v AND 3 NOPs) is set by jumping into the NOPs at 52888 through IX.
  52855,6 HL = v (H = coarse count, L = fine)
  52861,17 L = (v AND 255) / 4; IX = 52888 + 3 - (v AND 3)
  52878,10 A = border colour from 24006, MIC bit set, speaker clear
@ 52888 label=sfx_nops
  52888,3 Entered through IX: the fine delay
  52893,9 Delay: C counts the fine part, then B passes of 63
  52902,4 Flip the speaker bit and OUT
  52906,6 B = coarse count; done after the falling edge
  52914,4 Rising edge done: delay for the pulse's width
i 52920
@ 53798 label=sfx_witch
c 53798 One pulse of the witches' cackle
D 53798 Plays effect number (24001 - 1) AND 31, counting down; called four times per frame of the witch animation (#R53693), so a room change plays 60 pulses sweeping 31, 30, ..., 0, 31, ... 4. Preserves all registers.
i 53823
@ 57664 label=irq
c 57664 IM 2 interrupt handler
D 57664 Reached through the vector at 65021 (JP 57664). Counts frames in 61248 (the random seed). If 24002 (front-end mode) isn't 0, plays one tick of that mode's tune through #R64019, which returns to 57696. Then, while 24000 isn't 0, one explosion pulse (#R57714).
D 57664 The tick takes 2.11 frames with interrupts off, so the interrupts in between are lost: the tune advances one tick every 3 frames (2 for a rest tick), and the main program gets what's left.
  57685,11 Mode 1-3: JP to the tune's tick entry, returning to 57696
@ 57696 label=irq_tail
@ 57714 label=sfx_explode
c 57714 Explosion: one pulse per frame
D 57714 24000 counts down from 50 (set by 55624 when it spawns an explosion, type 5); each interrupt plays effect 50 + (count AND 31), a falling sweep 67..50, 81..50. At power-on 24000 holds a byte left over from loading (101), so the title screen starts with 101 of these pulses, one per music tick.
R 57714 A 24000 (not 0)
i 57726
@ 64010 label=sfx_bounce
b 64010 Sweep descriptor: the bounce
D 64010 Effects 20, 22, ..., 30 (one record, then 255). Started by #R52781 from 53288, 54780, 54860 and 54899.
@ 64014 label=sfx_collect
b 64014 Sweep descriptor: collecting / scoring
D 64014 Effects 50 (record 1: 50..10 step -10 leaves at once), then 10, 20, ..., 50 (record 2), then the 255 at 64020. Started from 56514 and 56894.
@ 64019 label=irq_modes
w 64019 IRQ handler's tick entries, by 24002
D 64019 Entry 0 is never used (mode 0 doesn't dispatch); its bytes are #R64014's last record and end mark.
  64019,2 (mode 0: unused)
  64021,2 Mode 1: tune 1 (title, credits)
  64023,2 Mode 2: tune 3 (game over)
  64025,2 Mode 3: tune 2 (win)
@ 64027 label=sfx_widths
w 64027 Pulse widths for #R52854, by effect number (84 words)
D 64027 The pulse is about 4 * v T-states. Seven runs of 12, each falling about a semitone per entry.
  64027,168,12
i 64195
