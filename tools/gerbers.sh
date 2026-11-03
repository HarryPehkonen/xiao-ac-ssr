#!/bin/sh
# Export fabrication data.  Nothing here is a safety certificate and nothing
# here has been checked by a fab's DFM rules -- open the gerbers in a viewer
# and read them before ordering.
#
#   ./tools/gerbers.sh          # writes build/gerbers/*.gbr, the drill files
#                               # and build/xiao-ac-ssr-gerbers.zip
set -eu
cd "$(dirname "$0")/.."
PROJECT=xiao-ac-ssr
OUT=build/gerbers
rm -rf "$OUT"
mkdir -p "$OUT"

kicad-cli pcb export gerbers --no-x2 --subtract-soldermask \
    -o "$OUT/" "$PROJECT.kicad_pcb"
kicad-cli pcb export drill --format excellon --drill-origin absolute \
    --excellon-zeros-format decimal --excellon-oval-format route \
    --generate-map --map-format gerberx2 -o "$OUT/" "$PROJECT.kicad_pcb"

( cd "$OUT" && python3 ../../tools/zipdir.py . "../$PROJECT-gerbers.zip" )
echo "wrote $OUT/ and build/$PROJECT-gerbers.zip"
ls -1 "$OUT"
