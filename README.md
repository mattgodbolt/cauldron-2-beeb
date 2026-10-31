# Cauldron II on the BBC Micro

A port, in progress, of Palace Software's *Cauldron II: The Pumpkin
Strikes Back* (ZX Spectrum, 1986: Steve Brown, Richard Leinfellner,
Richard Joseph) to the BBC Micro, in 6502 assembly built with
[baron](https://github.com/waitingforvsync/baron).

Unofficial. The original isn't in this repository: `make fetch`
downloads it from Spectrum Computing for the tools.

## Try it

The disc at the root, `cauldron2.ssd`, is the latest build worth trying:

- [Play it in jsbeeb (Master 128)](https://bbc.xania.org/?autoboot&model=Master&disc1=github:mattgodbolt/cauldron-2-beeb/cauldron2.ssd)
- Or boot it on a BBC Micro with 32K of sideways RAM, a Master 128, or in
  any emulator (SHIFT-BREAK).

Keys: **Z** left, **X** right, **:** up, **/** down, **RETURN** fire and
bounce, **ESCAPE** abort. The menu: 1 keyboard, 2 joystick, 3 define
keys, 4 play.

What works: the whole game, transcribed from the Spectrum's Z80: the
title, the menu and credits, every room, the pumpkin, monsters, magic,
the music and effects on the SN76489. Still to do: checking it pass by
pass against the original, speed, and fitting a 16K sideways RAM B.

## Building

Needs baron (`../baron/build/src/baron` or on the PATH), Python 3 with
[uv](https://github.com/astral-sh/uv), and Node.

```sh
make venv     # .venv: SkoolKit, Pillow, py65
make fetch    # the original, into original/
make          # build/cauldron2.ssd
make run      # boot it in jsbeeb, a screenshot in shots/run.png
make disc     # from a clean tree: copy the disc to cauldron2.ssd
```

See `CLAUDE.md` and `docs/` for how the port works and why
(`docs/decisions.md`).
