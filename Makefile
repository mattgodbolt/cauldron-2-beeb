# CAULDRON II — BBC Micro port
#
#   make          assemble build/cauldron2.ssd (+ build/cauldron2.json, the
#                 symbols, and build/listing.txt)
#   make run      boot it in jsbeeb, screenshot to shots/run.png
#   make check    every check (MODEL=Master to run them on a Master 128;
#                 default B-DFS1.2)
#   make disc     rebuild from a clean tree and copy the disc to
#                 cauldron2.ssd, which the README links
#   make fetch    download the Spectrum original into original/
#   make zx       load the original's tape into build/c2.z80, stopped at
#                 the game's entry (52180)
#   make disasm   the original's disassembly with the research's labels,
#                 build/c2.skool (from disasm/*.ctl)
#   make venv     the Python tools' environment (.venv: SkoolKit, Pillow, py65)
#   make passes   every scenario in tests/scenarios.txt on both machines,
#                 compared pass by pass (tools/zxpass.py, tools/beepass.mjs,
#                 tools/passcmp.py); fails if any differs
#   make rooms    every room 0-127 drawn by the viewer build (-D VIEWER=1,
#                 build/viewer.ssd) against the original's own drawing
#                 (tools/zxrooms.py): lit pixels, colours by the plan, and
#                 attributes; build/bbcrooms/contact.png
#   make sprites  random calls of 57194 and 57058 on both machines
#                 (tools/spritecases.py, tools/spritecheck.mjs)

PYTHON  ?= .venv/bin/python
BARON   ?= $(firstword $(wildcard ../baron/build/src/baron $(HOME)/dev/baron/build/src/baron) baron)
# Baron, failing on a warning too (every disc builds with --warn 2).
ASM      = BARON=$(BARON) tools/asm.sh
# The jsbeeb model the test tools use (tools/beeb.mjs reads CAULDRON_MODEL).
MODEL   ?= B-DFS1.2
export CAULDRON_MODEL = $(MODEL)
TARGET   = build/cauldron2.ssd
DISC     = cauldron2.ssd
SOURCES  = $(wildcard src/*.6502)
# Made from the original by the tools, never committed.
DATA      = build/data/gamedata.6502 build/data/roomdata.6502 build/data/font.6502
GENERATED = build/data/title.bin $(DATA)
# The tunes from the original (tools/mkmusic.py; src/sound.6502).
GENERATED += build/data/music.6502
VIEWER    = build/viewer.ssd
# Until game.6502 has the original's entry, the disc shows a room (room.6502's demo).
DEMO     := $(shell grep -qs '^\.z52180' src/game.6502 || echo "-D DEMO_ROOM=1")
# Stamped into !BOOT, so a disc says what it is: UTC build time and the
# commit, with + if the tree had changes.
BUILD   := $(shell date -u '+%Y-%m-%d %H:%M UTC') $(shell git rev-parse --short HEAD 2>/dev/null || echo NOGIT)$(shell git diff --quiet HEAD -- . ':(exclude)$(DISC)' 2>/dev/null || echo +)

.DELETE_ON_ERROR:
.PHONY: all run check disc fetch zx disasm venv clean passes rooms sprites music front

all: $(TARGET)

$(TARGET): $(SOURCES) $(GENERATED) tools/mksyms.py | build
	@python3 tools/lint_labels.py > /dev/null || python3 tools/lint_labels.py
	python3 tools/mksyms.py $(if $(SOFT),--soft) build/syms.6502 build/stubs.6502 $(SOURCES) $(wildcard build/data/*.6502)
	$(ASM) -D 'BUILD="$(BUILD)"' $(DEMO) -o $@ --title CAULDRON2 --opt 3 --warn 2 --symbols $(@:.ssd=.json) -v -log0 build/listing.txt src/main.6502

# The viewer: the same game, but a key after the title goes to the viewer
# (room.6502), which draws the rooms for the checks. Its own symbols.
$(VIEWER): $(SOURCES) $(GENERATED) tools/mksyms.py | build
	python3 tools/mksyms.py $(if $(SOFT),--soft) build/syms.6502 build/stubs.6502 $(SOURCES) $(wildcard build/data/*.6502)
	$(ASM) -D 'BUILD="$(BUILD)"' -D VIEWER=1 -o $@ --title VIEWER --opt 3 --warn 2 --symbols $(@:.ssd=.json) -log0 build/viewer.txt src/main.6502

# The oracle: every room drawn by the original's own code.
build/zxrooms/room_127.scr: build/c2.z80 tools/zxrooms.py tools/zx.py
	$(PYTHON) tools/zxrooms.py

$(DATA) &: build/c2.z80 build/zxrooms/room_127.scr tools/mkdata.py tools/colours.py tools/mksyms.py
	$(PYTHON) tools/mkdata.py

build/data/title.scr: original/CauldronII.tap tools/tapblock.py
	@mkdir -p build/data
	python3 -I tools/tapblock.py $< 6 $@

# (and title.6502, its palette program; title.png, the picture)
build/data/title.bin: build/data/title.scr tools/mkscreen.py
	python3 tools/mkscreen.py $< $@ --png $(@:.bin=.png)

check: $(TARGET) rooms sprites music front

rooms: $(VIEWER) build/zxrooms/room_127.scr
	node tools/roomcheck.mjs
	$(PYTHON) tools/roomcmp.py

sprites: $(VIEWER) build/zxrooms/room_127.scr
	$(PYTHON) tools/spritecases.py make
	node tools/spritecheck.mjs
	$(PYTHON) tools/spritecases.py cmp

build/data/music.6502: build/c2.z80 tools/mkmusic.py tools/zxmusic.py
	@mkdir -p build/data
	$(PYTHON) tools/mkmusic.py $< $@

# The music check's disc: the tunes stepped by the interrupt as 57664
# would, with nothing else (src/sound.6502's MUSICCHECK).
build/musiccheck.ssd: $(SOURCES) $(GENERATED) tools/mksyms.py | build
	python3 tools/mksyms.py build/syms.6502 build/stubs.6502 $(SOURCES) $(wildcard build/data/*.6502)
	$(ASM) -D MUSICCHECK=1 -D 'BUILD="$(BUILD) musiccheck"' -o $@ --title CAULDRON2 --opt 3 --warn 2 --symbols $(@:.ssd=.json) src/main.6502

# The music against tools/zxmusic.py's decode of the original's
# (tools/musicmodel.py), from the chip's bytes in jsbeeb.
music: build/musiccheck.ssd
	node tools/musiccheck.mjs

# The front end's test disc: its own printer and clear in place of the
# drawing's (src/frontend.6502's FETEST).
build/fetest.ssd: $(SOURCES) $(GENERATED) tools/mksyms.py | build
	python3 tools/mksyms.py build/syms.6502 build/stubs.6502 $(SOURCES) $(wildcard build/data/*.6502)
	$(ASM) -D FETEST=1 -D 'BUILD="$(BUILD) fetest"' -o $@ --title CAULDRON2 --opt 3 --warn 2 --symbols $(@:.ssd=.json) src/main.6502

# The menu, the keys, game over and the win (tools/fecheck.mjs).
front: build/fetest.ssd
	node tools/fecheck.mjs



# Always from a clean tree, so the stamp names the commit the disc holds.
disc:
	@git diff --quiet HEAD -- . ':(exclude)$(DISC)' || { echo "commit first: the stamp would say +"; exit 1; }
	rm -f $(TARGET)
	$(MAKE) $(TARGET)
	cp $(TARGET) $(DISC)

run: $(TARGET)
	node tools/play.mjs 'f5,!run' shots/ --disc $(TARGET) --until shown

build:
	mkdir -p build

fetch:
	tools/fetch_original.sh

original/CauldronII.tap:
	tools/fetch_original.sh

zx: build/c2.z80

# The tape's loader runs to the game's entry once a key is pressed after
# SCREEN$ (PAUSE 0).
build/c2.z80: original/CauldronII.tap | build
	.venv/bin/tap2sna.py --press 7:SPACE -s 52180 $< $@

disasm: build/c2.skool

build/c2.skool: build/c2.z80 $(wildcard disasm/*.ctl)
	.venv/bin/sna2skool.py -c disasm $< > $@

# The original's logs are cached: each depends on the snapshot and its own
# scenario line (build/passes/NAME.scn, rewritten only when the line
# changes). The port's are made afresh every time.
SCENARIOS = $(shell awk '{ sub(/\#.*/, "") } NF { print $$1 }' tests/scenarios.txt)

.PRECIOUS: build/passes/%.scn
build/passes/%.scn: tests/scenarios.txt
	@mkdir -p build/passes
	@awk '{ sub(/\#.*/, "") } $$1 == "$*"' $< > $@.new
	@cmp -s $@.new $@ || mv $@.new $@; rm -f $@.new

build/passes/zx_%.json: build/passes/%.scn build/c2.z80 tools/zxpass.py
	$(PYTHON) tools/zxpass.py $* -o $@

passes: $(TARGET) $(SCENARIOS:%=build/passes/zx_%.json)
	@failed=; for s in $(SCENARIOS); do \
	    node tools/beepass.mjs $$s -o build/passes/bbc_$$s.json; \
	    python3 tools/passcmp.py build/passes/zx_$$s.json build/passes/bbc_$$s.json || failed="$$failed $$s"; \
	done; \
	if [ -n "$$failed" ]; then echo "passes: differ:$$failed"; exit 1; fi

venv:
	uv venv .venv && uv pip install --python .venv/bin/python skoolkit pillow py65

clean:
	rm -rf build
