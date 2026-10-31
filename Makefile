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

PYTHON  ?= .venv/bin/python
BARON   ?= $(firstword $(wildcard ../baron/build/src/baron) baron)
# Baron, failing on a warning too (every disc builds with --warn 2).
ASM      = BARON=$(BARON) tools/asm.sh
# The jsbeeb model the test tools use (tools/beeb.mjs reads CAULDRON_MODEL).
MODEL   ?= B-DFS1.2
export CAULDRON_MODEL = $(MODEL)
TARGET   = build/cauldron2.ssd
DISC     = cauldron2.ssd
SOURCES  = $(wildcard src/*.6502)
# Made from the original by the tools, never committed.
GENERATED = build/data/title.bin
# Stamped into !BOOT, so a disc says what it is: UTC build time and the
# commit, with + if the tree had changes.
BUILD   := $(shell date -u '+%Y-%m-%d %H:%M UTC') $(shell git rev-parse --short HEAD 2>/dev/null || echo NOGIT)$(shell git diff --quiet HEAD -- . ':(exclude)$(DISC)' 2>/dev/null || echo +)

.DELETE_ON_ERROR:
.PHONY: all run check disc fetch zx disasm venv clean

all: $(TARGET)

$(TARGET): $(SOURCES) $(GENERATED) tools/mksyms.py | build
	@python3 tools/lint_labels.py > /dev/null || python3 tools/lint_labels.py
	python3 tools/mksyms.py build/syms.6502 build/stubs.6502 $(SOURCES) $(wildcard build/data/*.6502)
	$(ASM) -D 'BUILD="$(BUILD)"' -o $@ --title CAULDRON2 --opt 3 --warn 2 --symbols $(@:.ssd=.json) -v -log0 build/listing.txt src/main.6502

build/data/title.scr: original/CauldronII.tap tools/tapblock.py
	@mkdir -p build/data
	python3 -I tools/tapblock.py $< 6 $@

# (and title.6502, its palette program; title.png, the picture)
build/data/title.bin: build/data/title.scr tools/mkscreen.py
	python3 tools/mkscreen.py $< $@ --png $(@:.bin=.png)

check: $(TARGET)

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

venv:
	uv venv .venv && uv pip install --python .venv/bin/python skoolkit pillow py65

clean:
	rm -rf build
