# Parked — state of this board (2026-11-12)

**Status: design and gates complete; fabrication ordered (JLCPCB quote configured, not yet paid).**
The resume point is the fab order, then parts and assembly.

## Where it stands

- Board: 150 × 45 mm, 2 layers, 1.6 mm, FR-4 (TG135), through-hole throughout.
- **All gates green** (`./tools/ci.sh`): DRC 0 errors / 0 warnings, the nickname + mounting-hole +
  socket-pattern rules, netlist pin names, and the board-provenance gate. The committed
  `.kicad_pcb` matches what `tools/gen_pcb.py` + `tools/route.py` produce.
- Gerbers exported (`tools/gerbers.sh` → `build/xiao-ac-ssr-gerbers.zip`) and uploaded to JLCPCB,
  whose parser read them back as *"2 layer board of 45x150mm"*.
- JLCPCB quote verified field by field: 2 layers, 1.6 mm, **1 oz**, FR-4 TG135, Green / White
  silkscreen, **LeadFree HASL**, tented vias, **Remove Mark** (no order number printed on the
  board), flying-probe test, no gold fingers / castellation / edge plating / blind slots,
  Single PCB, 1 design, qty 10.
- Parts: the DigiKey cart was reviewed line by line for four builds; the varistor line was
  corrected to the straight-lead part (`495-1411-ND` / `B72214S0151K101`) — see `BRINGUP.md`.
  The HLK-PM01 supply comes from AliExpress, not DigiKey.

## Do next, in order

1. **Pay the JLCPCB order** with **Confirm Production file → Yes** (free DFM review and a
   confirmation step before they build). Keep **Global Standard Direct Line** for shipping — it
   avoids UPS's customs brokerage fee into Canada — and re-check that line on the payment page,
   because the form resets to an express carrier when the quote refreshes.
2. **Eyeball the gerber layers.** Still outstanding, and the one check the repo's gates cannot do.
3. **Order the parts**, applying the `495-1411-ND` varistor swap plus the sockets and terminal
   blocks that were added to the cart.
4. **Assemble four boards**, then bring up per `BRINGUP.md`: GFCI outlet only, 500 V insulation
   test before first power-up, never probe while live.

## Traps already recorded (do not re-litigate)

- **`MOV1`'s staggered pads are correct.** The part's leads are offset along the **thickness
  axis** — visible in the datasheet's *side* view, not the front view. Do not "straighten" the
  footprint. DRC's `lib_footprint_mismatch` is the signal to re-verify a deviation, not an
  obstacle to remove.
- **This is the SSR board, not the dimmer.** Same triac footprint, same 6-pin opto footprint, same
  size class — different parts. Here: `BTA16-600SW` (logic level) + `MOC3063M` (zero-cross) +
  360 Ω / 150 Ω. The dimmer is `BTA16-600B` + `MOC3021M` (random phase) + 1 kΩ / 220 Ω. Swapping
  them fits the holes perfectly and produces a board that does not work.
- **`5x20 mm` is not a fuse spec.** `F1` is a ceramic high-breaking-capacity part (1500 A @
  250 VAC); a glass low-breaking fuse of the same size and rating is not equivalent on mains.

## Resuming after a long gap

```bash
git pull && ./tools/ci.sh     # expect: gates OK, 0 errors, 0 warnings
./tools/gerbers.sh            # rebuild the fab package if anything changed
# then continue at "Do next" above
```

Design rationale lives in `DESIGN.md`; the on-disk board notes are in `docs/PCB-NOTES.md`.
Taking it to a finished, approved product (the Code's approval rule, SPE-1000 field evaluation,
the applicable standards, and why the XIAO is the wrong part for that) is in
`docs/PRODUCTIZING.md`.
