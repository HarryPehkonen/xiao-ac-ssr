# PCB status — complete, and honest about what that means

The board is **generated**, not drawn: `tools/gen_pcb.py` places the parts,
`tools/route.py` routes them, `tools/check_board.py` gates the result. Nets come
from the schematic netlist export, so the board cannot disagree with the
schematic about connectivity.

## What works

- 14 footprints placed by the zone packer (mains / barrier / logic) on a
  150 × 95 mm outline. No courtyard overlaps.
- **11 of 11 nets routed** from `kicad-cli sch export netlist`: 137 track
  segments, 6 vias, 794 mm of copper (the longest net is GND at 158 mm).
  106 segments on F.Cu, 31 on B.Cu; widths used are 1.5 mm (mains), 0.6 mm
  (5 V/GND) and 0.4 mm (signal).
- `xiao-ac-ssr.kicad_dru` carries the isolation barrier as a machine-checked
  rule: **3 mm clearance between mains nets and everything else**, and a
  **1.5 mm minimum mains track width**. Both are DRC rules, not conventions —
  eroding either one fails the gate.
- DRC: **0 errors, 0 warnings.**

## The two router bugs this board found

Both were found by measuring, not by guessing, and both were real modelling
faults in the code copied from the dimmer:

1. **Net ordering.** The router ordered nets by the *shortest* pad-to-pad hop,
   with 2-pad nets first. That put `TRIAC_G` (whose far hop is 20 mm) ahead of
   `LOAD_L` (41 mm across, but only a 16 mm local hop) — and TRIAC_G's 1.5 mm
   trace up the side of the triac then sealed `LOAD_L`'s only escape from
   Q1.2. Now ordered by the **longest** hop: a net with one tight pair and one
   far pad still has to reach the far pad, and that is what blocks other pads.
2. **Pad keepouts were discs sized for a signal track.** `_pad_disc` used
   `max(pad size)/2` as a radius and assumed the routing track's half-width was
   `WIDTH_SIGNAL/2` = 0.2 mm, whatever the net. A TO-220 pad is a
   1.905 × 2.0 mm **rectangle** whose corner is 1.38 mm from the centre, not
   1.0 mm, and a mains trace is 1.5 mm wide, not 0.4 mm — about 0.9 mm of
   unmodelled metal per side. Measured consequence on this board: `LOAD_L` ran
   within **0.02 mm** of Q1.1's pad (4 clearance errors; 28 shorts and 26
   solder-mask bridges in the 2.8 mm experiment). Pads now block as
   **bounding boxes** inflated by the board clearance *plus the routing net's
   own half-width* plus the grid's half-diagonal, and the same box model is used
   when opening a pad for its own net. Bounding boxes also handle rotated pads
   (a resistor on its side) for free.

The dimmer's board can pick both fixes up by copying `tools/route.py`; nothing
in them is specific to this circuit.

## The mains-width experiments (measured)

The trace has to reach the triac's **middle** pad, and its two neighbours sit one
2.54 mm pitch either side: 3.175 mm edge to edge. Tried, end to end:

| mains width | IPC-2221 carry (1 oz, 10 °C) | result |
| --- | --- | --- |
| 1.5 mm | 3.21 A | **11/11 routed, DRC 0/0** — this is what shipped |
| 2.0 mm | 3.95 A | 10/11: `no path J4.1 -> Q1.2, pad-veto 132/144, free 12 cells, no path` |
| 2.8 mm | 5.05 A | 10/11, plus 28 shorts and 26 mask bridges from the pad-entry modelling above |

Pure DRC geometry would allow 2.775 mm there; the 0.5 mm grid plus its safety
slack caps the model at 2.067 mm; reality caps it lower still, because the
neighbours' copper and the already-routed neighbours close the approach. The
ceiling is therefore copper- and geometry-bound at the family's 3.15 A, not
triac-bound: the BTA16 is a 16 A part. See DESIGN.md decision 9 and
`docs/ninny-brief.md` for what it would take to lift it.

## What does not work yet

- **No mounting holes.** Four M3 holes in the corners with 6 mm copper keepouts
  are a small change to the placement table, but they move the corner
  corridors and the router has to be re-run and re-gated. See BOM.md.
- **No copper pour on either layer.** Deliberate: the 3 mm barrier is easier to
  guarantee without one and this board has no thermal need for it.
- **The approach into Q1.2 is a one-cell corridor** in the router's grid, i.e.
  the trace arrives straight down the pad's own column. That is the correct
  geometry for a middle pad in a pin row, and it is stable *for this placement*
  — but it is the thing to re-check first if the placement ever changes.
- **Routing quality**: 137 segments for 11 nets, with several short zig-zags
  where the maze router steps around a via or a pad. Not beautiful; DRC-clean,
  and the generator reproduces it exactly.
- **Silkscreen**: reference designators are placed by `AutoPlaceFields()` and it
  does not clear every overlap. `check_board.py` reports 0 warnings here, but
  the silkscreen was never *designed*, only auto-placed.

## Gerbers

```sh
./tools/gerbers.sh        # build/gerbers/ (27 files) + build/xiao-ac-ssr-gerbers.zip
```

Exported and present, 52 KB zipped. **Not yet opened in a gerber viewer, and not
DFM-checked against any fab's rules.** Do that before ordering; a clean DRC is
not a fab's design-rule check.

## Safety status (unchanged, and not affected by any of the above)

DRC clean is still not a safety certificate. The barrier is geometry the tool
checks; the parts, the creepage standard, the enclosure, the GFCI test and the
500 V insulation test are what make it survivable. And a triac fails **short**:
put a mechanical switch in the cord. See DESIGN.md.
