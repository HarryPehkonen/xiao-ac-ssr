# PCB status — complete, and honest about what that means

The board is **generated**, not drawn: `tools/gen_pcb.py` places the parts,
`tools/route.py` routes them, `tools/check_board.py` gates the result. Nets come
from the schematic netlist export, so the board cannot disagree with the
schematic about connectivity.

## What works

- 18 footprints on a 150 × 45 mm outline: the 14 parts placed by the zone packer
  (mains / barrier / logic) plus the **4 M3 mounting holes**. No courtyard
  overlaps. The outline is sized to the packed parts — see "Board size" below.
- **11 of 11 nets routed** from `kicad-cli sch export netlist`: 137 track
  segments, 6 vias, 794 mm of copper (the longest net is GND at 158 mm).
  106 segments on F.Cu, 31 on B.Cu; widths used are 1.5 mm (mains), 0.6 mm
  (5 V/GND) and 0.4 mm (signal).
- `xiao-ac-ssr.kicad_dru` carries the isolation barrier as a machine-checked
  rule: **3 mm clearance between mains nets and everything else**, and a
  **1.5 mm minimum mains track width**. Both are DRC rules, not conventions —
  eroding either one fails the gate.
- DRC: **0 errors, 0 warnings.**
- Every footprint id carries its **library nickname** (`Resistor_THT:R_Axial_…`,
  not `R_Axial_…`), so "update footprint from library" works — the workflow a
  part swap needs. `FootprintLoad()` was dropping it on placement. See
  "The nickname defect this board inherited".
- **The committed board is the generated board**: `tools/check_regen.py`, the
  fifth gate, regenerates in a throwaway copy of `tools/` and compares every
  footprint and copper item against `xiao-ac-ssr.kicad_pcb` (18 and 143 today).

## Mounting holes

Four M3 clearance holes, one per corner, 5 mm inset from both edges:
`MountingHole:MountingHole_3.2mm_M3`, a non-plated 3.2 mm hole with no pad and
no net. Each owns a **6 mm-diameter copper-free disc** — no track, via or pad
edge within 3 mm of the hole centre — because an M3 screw head sits over it.
They carry `exclude_from_bom` / `exclude_from_pos_files`. The pass is the
dimmer's `a32a414` applied to this board, one generation later.

Measured on the committed board (the gate prints this):

| hole | position | nearest board edge | closest copper to the centre |
| --- | --- | --- | --- |
| H1 | (5, 5) | 5.00 mm | 6.051 mm (`L_IN`, 1.5 mm track) |
| H2 | (145, 5) | 5.00 mm | 7.969 mm (`J2.1`) |
| H3 | (5, 40) | 5.00 mm | 10.067 mm (`N_AC`) |
| H4 | (145, 40) | 5.00 mm | 14.778 mm (`J2.7`) |

What fell out of adding them:

1. **The corner courtyards forced the packing in.** Each hole's courtyard
   reaches 3.45 mm back from its centre, so the packing strips start 9 mm from
   the top edge instead of hugging the outline. **Nothing else about the routing
   changed**: all 143 copper items on the new board are the old routing
   translated **+3.0 mm** in y, item for item (measured by comparing the two
   boards' copper sets). Still 11/11, still 0 errors and 0 warnings.
2. **The outline did not grow.** The holes sit at y = 5 and y = 40, and the only
   parts deep enough to reach the bottom pair's courtyards (y 36.55 … 43.45) are
   Q1/J4 in the mains strip and PS1 across the barrier — all between x = 19 and
   x = 99.4, clear of both corners. 150 × 45 mm stands. The corner-copper
   question in the card that requested this pass — "the SSR's copper spans
   nearly the full outline and I have not measured the corner clearance" —
   measured **empty**: the nearest copper to any hole is 6.05 mm from its centre,
   twice the 3 mm spec radius.
3. **The keepout is inflated by the copper that has to pass it.** Blocking cell
   *centres* at the 3 mm spec radius is not enough: a 1.5 mm mains track laid on
   the last free cell still puts its edge 0.75 mm inside the disc.
   `MOUNT_BLOCK_R` is the spec radius plus half the widest track plus the
   half-cell diagonal. On the dimmer this was measured as a real violation
   (LOAD_L's edge 2.86 mm from H1); on **this** board the corners were already
   clear, so the keepout never bound — it is carried because the placement is
   free to move again, not because it was needed here. A pure-function test pins
   the inflation so it cannot be quietly dropped.

## The nickname defect this board inherited

`xiao-ac-ssr` was generated from the dimmer's tools *before* the dimmer's
`a32a414`, so it inherited that board's footprint-library defect: **every one of
its 14 footprint ids had no `Lib:` prefix** (`TO-220-3_Vertical`, not
`Package_TO_SOT_THRU:TO-220-3_Vertical`). The geometry is embedded in the board
and fab is unaffected, but "update footprint from library" can never work
without the link — and that is the whole workflow for swapping a part.

This is what the new gate found on the *unmodified* board, before anything was
fixed — 19 failures, all real:

```
0 error(s), 0 warning(s)
19 board problem(s) DRC cannot see:
  FAIL  C1: footprint id 'CP_Radial_D8.0mm_P3.50mm' carries no library nickname, so 'update footprint from library' cannot work
  ...
  FAIL  0 mounting hole footprint(s) on the board, 4 in gen_pcb.MOUNTING
```

So the answer to the card's question — "check whether the library-nickname
defect was inherited too" — is **yes**, measured rather than assumed, and DRC
had said 0 errors and 0 warnings about it both times.


## Board size

**150 × 45 mm = 67.5 cm²**, down from **150 × 95 mm = 142.5 cm²**.

The board was built as the dimmer's sibling, so it inherited the dimmer's
outline — and with it the dimmer's dead band. Its 14 parts span **33.8 mm**
vertically (then y 6 → 39.8 mm; y 9 → 42.8 mm now that the mounting holes pushed
the packing down 3 mm), so 95 mm was carrying **55 mm of empty board** below the
last row (plus the router's unused corridors above and below it). Nothing had
flagged it, because the outline is an input to the pipeline, not a result of it.

The height is now sized around the packed parts (`BOARD_H` in
`tools/gen_pcb.py` carries the reasoning), by the same rule the dimmer's 57 mm
came from:

- **Height 45 mm.** 9 mm above the first row, 33.8 mm of parts, 2.2 mm below the
  last row. The **9 mm at the top** is what the mounting holes cost: their
  courtyards reach 3.45 mm back from y = 5, so the packing had to move down from
  y = 6 (see "Mounting holes"). It cost no copper — the routing is the old
  routing translated 3 mm.
- **Width stays 150 mm.** The parts span 135.7 mm, already ~10% over.
- **The floor is 40 mm.** Shrinking removes the router's spare corridors, so a
  smaller board is a *new* routing claim: 40, 41, 42, 43, 44 and 45 mm were each
  regenerated end-to-end and each reported **11/11 nets** with 0 DRC errors and
  0 warnings. 39 mm is where it starts warning. 45 is used rather than 40 —
  five spare millimetres are not worth chasing the minimum. (The 40 mm floor was
  measured *before* the mounting holes; 45 mm is re-measured *with* them and is
  unchanged, so it still stands as the shipped height.)
- **Nothing else changed:** the placement, the 3 mm barrier rule, the 137 track
  segments and 6 vias are the same as at 95 mm, and `check_regen.py` still finds
  the committed board identical to the generated one.

## Reproducibility — what is and is not exact

| artifact | reproducible? | how it is checked |
| --- | --- | --- |
| `xiao-ac-ssr.kicad_sch` | **byte-identical** | `ci.sh` regenerates and compares hashes |
| `xiao-ac-ssr.kicad_dru` | **byte-identical** | measured stable; regenerated by `gen_pcb.py`, not gated |
| `xiao-ac-ssr.kicad_pcb` | **geometry only** | `tools/check_regen.py` |

The board file is not byte-reproducible and cannot be made so cheaply: pcbnew
stamps a fresh UUID on every footprint, pad, track and text it creates, and
KiCad writes those items back in its own order. What *is* reproducible is the
board itself — measured: **18/18 footprints and 143/143 tracks+vias identical**
between two consecutive runs *and* identical to the committed board. So the gate
compares the geometry, which is the part a person would have had to edit to fake
something.

The gate has teeth: nudging `MOV1` 0.5 mm by hand in the committed
`xiao-ac-ssr.kicad_pcb` makes it exit 1 and name the part —

```
FAIL: footprints differ -- the committed board is not what the generator produces
  only in the committed board: ('MOV1', 'S14K150', 7.025, 24.25, 0.0, 0)
  only in the generated board: ('MOV1', 'S14K150', 6.525, 24.25, 0.0, 0)
```

…and so does moving a **mounting hole** 0.5 mm, which is the other half of the
same question (a hand-moved hole is caught here *and* by the geometry gate in
`check_board.py`, by two independent measurements):

```
FAIL: footprints differ -- the committed board is not what the generator produces
  only in the committed board: ('H1', 'MountingHole_3.2mm_M3', 5.5, 5.0, 0.0, 0)
  only in the generated board: ('H1', 'MountingHole_3.2mm_M3', 5.0, 5.0, 0.0, 0)
```

One more piece of churn, for the record: `gen_sch.py` writes a minimal
`.kicad_pro`, and KiCad rewrites it with its full set of board defaults whenever
a netlist export runs (i.e. on `gen_pcb.py`, not on `ci.sh`). The committed file
is the generator's minimal one, so the **gate** leaves a clean tree; a routing
run can leave `xiao-ac-ssr.kicad_pro` modified, and that diff is KiCad's
bookkeeping rather than anything the design depends on.

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

- **The corner keepouts have never bound here.** They are carried for the next
  placement, not for this one: on this board the corners were already clear
  (nearest copper 6.05 mm from a hole centre) and the routing is the pre-hole
  routing translated 3 mm. The *dimmer* is where the inflation was measured
  against a real violation. See "Mounting holes".
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
