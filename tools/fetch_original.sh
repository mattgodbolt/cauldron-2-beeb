#!/bin/sh
# Fetch the Spectrum original and its reference material from Spectrum
# Computing (ZXDB entry 851) into original/, and check them against
# tools/SHA256SUMS once recorded. Not committed: they are not ours to
# redistribute.
set -e
mkdir -p "$(dirname "$0")/../original"
cd "$(dirname "$0")/../original"
SC=https://spectrumcomputing.co.uk
get() { [ -f "$2" ] || curl -sfL "$1" -o "$2"; }
# getzip URL DEST: the zip's one tape, under the name given.
getzip() {
    [ -f "$2" ] && return
    curl -sfL "$1" -o fetch.zip
    member=$(unzip -Z1 fetch.zip | grep -iE '\.(tap|tzx)$' | head -1)
    unzip -p fetch.zip "$member" > "$2" && rm fetch.zip
}
getzip "$SC/pub/sinclair/games/c/CauldronII-ThePumpkinStrikesBack.tap.zip" CauldronII.tap
getzip "$SC/pub/sinclair/games/c/CauldronII-ThePumpkinStrikesBack.tzx.zip" CauldronII.tzx
sha256sum -c --quiet ../tools/SHA256SUMS
