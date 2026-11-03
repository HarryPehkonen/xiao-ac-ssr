# Lift the mains copper: teach the router a necked pad entry

## The repository

`xiao-ac-ssr` — a single-channel inline AC solid-state switch for a Seeed XIAO
ESP32C3 (mains cord in, load socket out, zero-cross opto + snubberless triac).
Everything is generated headless; there is no GUI on this machine.

| file | what it is |
| --- | --- |
| `tools/gen_sch.py` | generates `xiao-ac-ssr.kicad_sch` from a part/net table |
| `tools/check_netlist.py` | gate: exported netlist == intended netlist |
| `tools/gen_pcb.py` | places footprints (zone packer) and routes the board |
| `tools/route.py` | the maze router (A* over a 0.5 mm grid, two layers, vias) |
| `tools/check_board.py` | gate: `kicad-cli pcb drc` plus the rules DRC has none for — library nicknames, the mounting holes and their keepout; exit 0 = clean |
| `tools/check_regen.py` | gate: committed board == generated board (placement + copper) |
| `tools/tests/test_board_gate.py` | the gate's own teeth: each rule broken, one at a time |
| `tools/ci.sh` | the gate: schematic staleness + netlist + ERC + board DRC/rules + board regen + gate tests |
| `xiao-ac-ssr.kicad_pcb` | GENERATED — never hand-edit it |
| `xiao-ac-ssr.kicad_dru` | custom DRC rules (the mains isolation barrier, the 1.5 mm mains width) |

Toolchain: `kicad-cli` and `pcbnew` 9.0.2, the Python bindings only under
**`/usr/bin/python3`** (not a venv).

## The red test — this is the whole task

```
MAINS_WIDTH_MM=2.0 /usr/bin/python3 tools/gen_pcb.py && /usr/bin/python3 tools/check_board.py
```

That exits 1 today. `MAINS_WIDTH_MM` is an environment override in
`tools/route.py` that drives both the trace width and the `.kicad_dru` floor, so
"would a wider trace route?" is a single command rather than an edit/run/revert
dance. (Remember to regenerate at the default afterwards: the two commands above
leave a 2.0 mm board and its rule on disk.)

The board is gated and green **at 1.5 mm mains copper**. It is *not* green at
2.0 mm, and that is the thing to fix: the load current has to reach the triac's
**middle** pad, and the trace width is capped by the geometry of that one entry.

Write the failing test first. The end-to-end one is:

> with `WIDTH_MAINS = 2.0`, every net routes and DRC is clean (0 errors,
> 0 warnings).

Measured today at 2.0 mm: `10/11 nets, failed: {'LOAD_L': 'no path J4.1 -> Q1.2
[cells=144 pad-veto=132 copper-veto L0=0/L1=0 free L0=12/L1=12]'}` — the landing
pad's opening has 12 free cells per layer and still cannot reach them. Watch it
fail before you touch anything.

## Diagnosis already done — use it, do not redo it

- `Q1` is a TO-220: pads 1.905 mm wide on a **2.54 mm pitch**. Its *neighbours*
  are one pitch either side of the middle pad, so the gap between their pad
  edges is **3.175 mm**.
- Pure DRC geometry would allow a **2.775 mm** trace down the middle pad's
  column. The router's 0.5 mm grid plus its `QUANT` slack (0.354 mm, which
  deliberately charges each pad for grid quantisation) caps the *model* at
  **2.067 mm** — and reality caps it lower still: at 2.0 mm it does not route,
  because the neighbours' copper and the already-routed neighbours close the
  approach, not just the column itself.
- Measured, end to end: **1.5 mm routes (11/11, DRC 0/0); 2.0 mm does not.**
- `pad-veto=132 of 144` says the middle pad's opening is eaten almost entirely by
  its own two neighbours. A rectangle-inflated-by-slack keepout is the right
  model for *blocking*, and it is the wrong model for *opening*: the entry into
  a pad in a pin row is a channel **along** the row, not a box around the pad.

## What to build

1. **Tests, starting with one that fails today.** Your *first* test must be red —
   the 2.0 mm end-to-end routing test above. Then the pure-function tests:
   - a pad's entry channel is a rectangle **one grid cell wide**, running along
     the pin row's direction, centred on the pad's own column, and it must be
     opened (not vetoed) for that pad's own net only;
   - the channel respects the neighbours: its free span at 2.0 mm equals
     `gap - 2*(clearance + half-width)`, and it is empty (no channel) when that
     number goes negative — assert the *empty* case too, because that is the
     one that must fail loudly rather than produce a short;
   - a rotated rectangular pad (a resistor on its side) produces an axis-aligned
     box of the right extents, and a round pad (a via) a square of its diameter;
   - `_to_segments` merges collinear grid steps into one segment, turns a corner
     into two, splits at a layer change, and never emits a zero-length run.
2. **Make 2.0 mm route.** `/usr/bin/python3 tools/check_board.py` must exit 0
   with `WIDTH_MAINS = 2.0` **and** with `WIDTH_MAINS = 1.5` — the existing board
   must stay clean, not be traded for the new one.
3. **If and only if both pass**, raise the fuse and the `.kicad_dru` rule to
   match (2.0 mm is IPC-2221 3.95 A at a 10 °C rise; the fuse then becomes 3.5 A
   or 4 A) and update `README.md`, `BOM.md` and `DESIGN.md` decision 9 in the
   same commit. If 2.0 mm cannot be made to pass honestly, **leave everything at
   1.5 mm** and say so — a rate-the-ceiling claim needs the board to prove it.
4. Update the numbers in `docs/PCB-NOTES.md` either way, including this run's
   real output.

## Hard constraints — do not do any of these

- Do **not** edit the isolation rule in `xiao-ac-ssr.kicad_dru`. The 3 mm
  mains/logic barrier is the point of the board. Weakening it is not a fix.
- Do **not** relax the router's clearance constants (`CLEAR_NORMAL`, `QUANT`) to
  make DRC pass. The floor is **measured**: 0.25 mm margin produced 12 shorts
  against `no-net` pads, 0.5 mm is clean but wastes the space dense pin columns
  need, 0.4 mm holds.
- Do **not** delete parts, pads or nets, and do not change the net list in
  `tools/gen_sch.py`.
- Do **not** move Q1 to "fix" the width — the triac sits beside the outlet
  deliberately (it is what makes LOAD_L short). If a placement change really is
  needed, say so in the report rather than making it silently.
- Do **not** hand-edit `xiao-ac-ssr.kicad_pcb`. It is generated; the fix belongs
  in `tools/route.py` so regeneration reproduces it.
- Do **not** commit. Leave the working tree for review.
- **Explore in `/tmp`, never in the repo.** A previous slice of this project
  wrote seven throwaway prototype scripts into the tree; they would have shipped
  in the patch. Keep the tree to the change itself.
- **Run the acceptance command after every source write.** It takes seconds:
  `time /usr/bin/python3 tools/gen_pcb.py && /usr/bin/python3 tools/check_board.py`.
  The gate is the only feedback that matters here; use it constantly.

## Acceptance

- Both `WIDTH_MAINS = 2.0` and `WIDTH_MAINS = 1.5` route completely and are
  DRC-clean (0 errors, 0 warnings).
- `./tools/ci.sh` passes — all five gates, including `check_regen.py`, which
  means the committed board still matches the generator after your change (two
  unrelated routes succeeding is the failure mode where a fix is really a
  different layout).
- The new router tests pass, including the empty-channel case.
- `git diff --stat` shows **no** change to `xiao-ac-ssr.kicad_dru` and no change
  to the nets in `tools/gen_sch.py`.
- If the fuse changed, the three docs changed with it.

## Report back

What you changed and why; the real command output for both widths; anything you
could not fix and what you tried. If 2.0 mm still will not route, say so plainly
— do not make the gate pass by any other means.
