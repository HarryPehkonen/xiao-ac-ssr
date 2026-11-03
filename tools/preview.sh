#!/bin/sh
# Render the schematic and the board for human review.
#
# Everything this writes is GENERATED and gitignored (svg/, *.pdf): the
# .kicad_sch and .kicad_pcb are the sources of truth.  This exists so a person
# can look at the thing without opening KiCad -- and so the review question
# "does the board look like the design?" has an answer that costs one command.
#
#   ./tools/preview.sh
set -eu
cd "$(dirname "$0")/.."
OUT=svg
mkdir -p "$OUT"

kicad-cli sch export svg --exclude-drawing-sheet -o "$OUT/sch" \
    xiao-ac-ssr.kicad_sch
kicad-cli sch export pdf --exclude-drawing-sheet \
    -o "$OUT/xiao-ac-ssr-schematic.pdf" xiao-ac-ssr.kicad_sch

# Front copper + silkscreen, back copper separate: the two layers are what a
# person needs to check the mains runs and the barrier by eye.
kicad-cli pcb export svg --mode-single --layers F.Cu,F.Silkscreen,Edge.Cuts \
    -o "$OUT/pcb-front.svg" xiao-ac-ssr.kicad_pcb
kicad-cli pcb export svg --mode-single --layers B.Cu,Edge.Cuts \
    -o "$OUT/pcb-back.svg" xiao-ac-ssr.kicad_pcb
kicad-cli pcb export drill --format excellon -o "$OUT/" \
    xiao-ac-ssr.kicad_pcb > /dev/null

echo "wrote $OUT/ (schematic svg + pdf, pcb front/back svg)"
ls -1 "$OUT"
