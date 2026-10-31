#!/usr/bin/env python3
"""Compare two pass-by-pass logs and report the first difference.

    python3 tools/passcmp.py build/passes/zx_NAME.json build/passes/bbc_NAME.json [--no-buffers] [--more 8]

The logs come from tools/zxpass.py (the original) and tools/beepass.mjs
(the port): the variables 24000-25099 and a few table bytes at every
main-loop pass. The first pass that differs is reported with each byte's
original address and name, both values, and the next few bytes that
differ in that pass. Exit status 0 when the passes agree and both logs
ran as far, 1 otherwise.

Bytes that hold machine-specific values are skipped (IGNORE, each with
its reason); pointers into the tables are translated back through the
BBC log's symbols when it carries them (TRANSLATE).
"""
import argparse
import json
import sys

VARS0 = 24000

# (first, last, why): never compared.
IGNORE = [
    (24003, 24004, "sound sequence pointer (52781): an address, the BBC's differs"),
    (24040, 24041, "player area's row address word: the port may hold it differently"),
    (24050, 24051, "57415's saved SP: the Z80 stack trick, no BBC counterpart"),
    (24052, 24053, "57415's shift buffer pointer: an address into the buffers"),
    (25059, 25091, "the Spectrum loader's leftovers: the game never writes them"),
    (61248, 61249, "the random pointer: an address, and forced at the new game"),
]

# Table pointers: (first, region label, region's original start). The
# BBC's word, less the label, plus the start, is the original's.
TRANSLATE = [
    (24042, "r_tables", 57726, "RoomList, a pointer into the monster lists (61933-)"),
]

BUFFERS = (24225, 25058)

# Names from docs/research/core.md, player.md and monsters.md.
NAMES = {
    24000: "SndExplode", 24001: "CacklePitch", 24002: "irqTune",
    24003: "sndSeqPtr", 24004: "sndSeqPtr+1", 24005: "sndSeqVal",
    24006: "portFE", 24007: "attractCount", 24008: "attractPage",
    24009: "land_state", 24010: "last_attr", 24011: "roomBit",
    24012: "TeleTimer", 24013: "CackleDelay", 24014: "hit_attr",
    24015: "ReverseTimer", 24016: "ReverseMask", 24017: "CanFire",
    24020: "InputBits", 24021: "OtherSlot", 24022: "CurSlot",
    24024: "printAttr", 24025: "RedrawFlag", 24026: "bounce_v",
    24027: "bounce_level", 24028: "bounce_flip", 24029: "land_dir",
    24030: "Room", 24031: "PushBits", 24032: "CackleCount",
    24033: "CackleWait", 24034: "DeathTimer", 24035: "Lives",
    24038: "clipSkip", 24039: "clipLimit",
    24040: "row_addr", 24041: "row_addr+1",
    24042: "RoomList", 24043: "RoomList+1",
    24046: "(2650)", 24047: "(2650)+1", 24048: "(8384)", 24049: "(8384)+1",
    24050: "savedSP", 24051: "savedSP+1", 24052: "shiftBuf", 24053: "shiftBuf+1",
    59450: "MoveScripts (59450, poked)", 59582: "script 8's direction (59582)",
}
SLOT = ["count", "move", "moveidx", "dir", "xspd", "yspd", "x", "y", "xmax", "ymax",
        "drawnx", "drawny", "adelay", "anim", "aidx", "frame", "drawnframe", "width",
        "height", "respawn"]


def name(a):
    if a in NAMES:
        return NAMES[a]
    if 24054 <= a <= 24069:
        return f"RoomDone[{a - 24054}]"
    if 24070 <= a <= 24076:
        return f"Inventory[{a - 24070}]"
    if 24077 <= a <= 24196:
        s, off = divmod(a - 24077, 20)
        return f"slot{s}.{SLOT[off]}"
    if 24203 <= a <= 24222:
        return f"savedPlayer.{SLOT[a - 24203]}"
    if 24225 <= a <= 24426:
        return f"spriteBuf0+{a - 24225} (attrBuf+{a - 24225})"
    if 24427 <= a <= 24628:
        return f"spriteBuf1+{a - 24427} (attrBuf+{a - 24225})"
    if 24629 <= a <= 24864:
        return f"attrBuf+{a - 24225}"
    if 24995 <= a <= 25058:
        return f"sink+{a - 24995}"
    if 58804 <= a <= 58810:
        return f"score digit {a - 58804}"
    if 58813 <= a <= 58814:
        return f"magic digit {a - 58813}"
    if 61521 <= a <= 61572:
        return f"MagicRooms[{a - 61521}]"
    return ""


def ignored(a):
    return any(lo <= a <= hi for lo, hi, _ in IGNORE)


def state(p):
    """{original address: value} for one pass."""
    out = {VARS0 + i: v for i, v in enumerate(p["vars"])}
    out.update({int(a): v for a, v in p["extra"].items()})
    return out


def translate(zx, bbc, symbols):
    """Put the original's value into the BBC's pointer words that can be
    translated; the rest of those words are skipped."""
    skip = set()
    for a, label, origin, _ in TRANSLATE:
        if label not in symbols or a not in bbc:
            skip |= {a, a + 1}
            continue
        w = bbc[a] | (bbc[a + 1] << 8)
        if w == 0 and zx.get(a, 0) | zx.get(a + 1, 0) == 0:
            continue  # (no list yet: zero on both)
        w = (w - symbols[label] + origin) & 0xFFFF
        bbc[a], bbc[a + 1] = w & 0xFF, w >> 8
    return skip


def spans(addrs):
    out, addrs = [], sorted(addrs)
    for a in addrs:
        if out and out[-1][1] == a - 1:
            out[-1][1] = a
        else:
            out.append([a, a])
    return " ".join(f"{lo}" if lo == hi else f"{lo}-{hi}" for lo, hi in out)


def fmt(a, zv, bv):
    n = name(a)
    return f"  {a}{' ' + n if n else ''}: zx {zv} bbc {bv}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zx")
    ap.add_argument("bbc")
    ap.add_argument("--no-buffers", action="store_true",
                    help=f"skip the sprite and attribute buffers ({BUFFERS[0]}-{BUFFERS[1]})")
    ap.add_argument("--more", type=int, default=8, help="differing bytes to list after the first")
    args = ap.parse_args()
    za, ba = (json.load(open(f)) for f in (args.zx, args.bbc))
    symbols = ba.get("symbols", {})
    tag = za.get("scenario", "?")
    if za.get("scenario") != ba.get("scenario"):
        print(f"passcmp: different scenarios: {za.get('scenario')} and {ba.get('scenario')}")
        return 1

    missing = ba.get("missing", [])
    if missing:
        print(f"passcmp {tag}: not compared, the BBC has no symbol for: {spans(missing)}")

    zp, bp = za["passes"], ba["passes"]
    for i in range(min(len(zp), len(bp))):
        zs, bs = state(zp[i]), state(bp[i])
        skip = translate(zs, bs, symbols)
        diffs = []
        for a in sorted(zs):
            if a in skip or ignored(a) or a not in bs:
                continue
            if args.no_buffers and BUFFERS[0] <= a <= BUFFERS[1]:
                continue
            if zs[a] != bs[a]:
                diffs.append(a)
        if diffs:
            print(f"passcmp {tag}: pass {zp[i]['pass']} differs (frame zx {zp[i]['frame']}, "
                  f"bbc {bp[i]['frame']}), {len(diffs)} bytes:")
            for a in diffs[:1 + args.more]:
                print(fmt(a, zs[a], bs[a]))
            if len(diffs) > 1 + args.more:
                print(f"  ... and {len(diffs) - 1 - args.more} more")
            return 1

    n = min(len(zp), len(bp))
    if len(zp) != len(bp):
        short, other = ("bbc", "zx") if len(bp) < len(zp) else ("zx", "bbc")
        log = ba if short == "bbc" else za
        ran = f"the {n} passes both ran agree; {short} stopped there" if n else f"{short} logged no passes"
        print(f"passcmp {tag}: {ran} ({log.get('stopped', '?')}), {other} ran {max(len(zp), len(bp))}")
        return 1
    print(f"passcmp {tag}: {n} passes agree ({za.get('stopped', '?')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
