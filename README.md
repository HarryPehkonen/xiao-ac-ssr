# xiao-ac-ssr

One-channel inline AC **solid-state switch** (on/off, no dimming) for a Seeed
Studio XIAO ESP32C3 (or any XIAO on the same 14-pad footprint). Mains cord in
one end, load socket out the other, and a zero-cross opto-triac driving a
snubberless triac switches whatever is plugged in between them. Plug-in
bench/room scale — not house wiring.

Same family as [`xiao-ac-dimmer`](https://github.com/HarryPehkonen/xiao-ac-dimmer):
the whole mains front end, the XIAO sockets, the generator/router pipeline and
the gates are copied; the switching element and everything that existed only to
support *dimming* are replaced.

**Status: schematic and board complete and machine-checked. The board is
150 × 45 mm (67.5 cm²), 11/11 nets routed, DRC clean — 0 errors, 0 warnings.
Gerbers exported but not yet eyeballed in a gerber viewer and not yet checked by
a fab's DFM rules.**

## Ordering — DigiKey CA (as ordered 2026-11, four boards)

Part numbers as actually ordered and verified against this board's footprints. `qty` is what was
ordered for four boards; `need` is what four boards consume. HLK-PM01 (`PS1`) is an AliExpress part,
not a DigiKey line.

| qty | need | DigiKey PN | MPN | Role |
|---|---|---|---|---|
| 4 | 4 | `497-BTA16-600SWRG-ND` | BTA16-600SWRG | `Q1` triac — **logic-level gate (I_GT 10 mA)**, required by the zero-cross window |
| 4 | 4 | `MOC3063M-ND` | MOC3063M | `U2` zero-cross opto-triac, DIP-6, 5 mA I_FT (sets `R3` = 150 Ω) |
| 10 | 8 | `36-3512P-ND` | Keystone 3512P | `F1` fuse clips, 2 per board — the footprint is drawn for this pattern |
| 5 | 4 | `283-2931-ND` | `BK/S505-3.15-R` | `F1` fuse: 3.15 A 250 V ceramic **HBC** (1500 A @ 250 VAC) time-lag 5×20 mm |
| 4 | 4 | `495-6591-1-ND` | B72214S0151K551 | `MOV1` S14K150 varistor, 14 mm disc |
| 4 | 4 | `493-15239-1-ND` | UHE1E471MPD1TD | `C1` 470 µF 25 V, φ8 × 20 mm, 3.5 mm pitch, 7000 h @ 105 °C |
| 4 | 4 | `BC5229CT-ND` | K104K15X7RF5UH5 | `C2` 0.1 µF 50 V X7R radial, 5.0 mm pitch |
| 4 | 4 | `1801-1N5819CT-ND` | 1N5819 | `D5` Schottky 40 V 1 A, DO-41 (through-hole) |
| 10 | 4 | `150XBK-ND` | MFR-25FBF52-150R | `R3` 150 Ω 1/4 W — opto LED current |
| 10 | 4 | `13-MFR-25FTE52-360RCT-ND` | MFR-25FTE52-360R | `R4` 360 Ω 1/4 W — gate resistor |
| 5 | 4 | `1597-113991054-ND` | 113991054 | XIAO ESP32C3 (**C3**, not S3/C6) |
| 2 | 2 | `1597-102010490-ND` | 102010490 | 7-pin male headers for the XIAO (5-pack) |
| 10 | 8 | `S7005-ND` | PPTC071LFBN-RC | `J1`,`J2` 1×7 2.54 mm sockets |
| 10 | 8 | `732-10955-ND` | 691137710002 | `J3`,`J4` 5.00 mm 2-position screw blocks (16 A/300 V) |

**`MOV1` is correct as drawn — do NOT "fix" it.** KiCad's `Varistor.pretty/RV_Disc_*` footprints stagger
their two pads (the D12/W4.5/P7.5 variant: `pad 2 at (7.5, 1.8)`), and the datasheet shows exactly that
geometry: in the side view the two leads are offset **along the thickness axis** — one at the front face,
one at the back — both straight and of equal length. The offset matches the body: ≈ (thickness − lead ⌀)/2,
i.e. (4.5 − 0.8)/2 = 1.85 mm against KiCad's 1.80 (the pattern holds across the family: (4.2 − 0.8)/2 = 1.70
vs 1.63, (5.1 − 0.8)/2 = 2.15 vs 2.30). Sources: TDK/EPCOS SIOV StandarD series §3.2 "Standard, straight
leads" (Figure 1) and the side-view outline `VAR0586-W-E`.

Consequence for the gates: the footprint is an **unmodified library part**, and DRC enforces that — moving a
pad makes `lib_footprint_mismatch` fire immediately. Treat that warning as *guilty until proven*: it fired
here when a "fix" straightened the pads to what looked like a line, and the correct resolution was to revert
the change, not to silence the check. "Straight leads" in the ordering code (digit 13 = 1) means *uncrimped*,
**not** coplanar.

Assembly verification, first power-up and troubleshooting — with expected meter readings — live in
[`BRINGUP.md`](BRINGUP.md).

## Why an SSR and not a relay

Mechanical relay contact life at rated load is ~10⁵ operations; 100
activations a day reaches that in a few years, and the contacts weld rather
than fail safe-ly. A triac has no moving contacts. (Seeed's own XIAO relay
module quotes 1.5 × 10⁴ operations at 10 A/250 VAC *resistive* — electrical
endurance, not the headline mechanical number.)

The one thing a triac does **worse** than a relay is fail: it fails **short**,
so the load stays on and software cannot turn it off. See *Safety* below.

## No dimming, therefore much less circuit

Relative to the dimmer, this board **deletes** the H11AA1 zero-cross detector,
both 47 k detector legs, the 10 k pull-up, the 100 Ω + 100 nF triac snubber and
the phase-control firmware — six parts and five nets, all of them on the mains
side. What replaces them:

| | dimmer | this board |
| --- | --- | --- |
| opto | MOC3021M, *random phase* | **MOC3063M, *zero cross*** |
| triac | BTA16-600B, I_GT 50 mA | **BTA16-600SW, I_GT 10 mA, snubberless** |
| gate resistor | 1 k | **360 Ω** (onsemi's own figure-10 value) |
| LED resistor | 220 Ω | **150 Ω** |
| snubber | 100 Ω + 100 nF | none — not needed, see DESIGN.md |
| zero-cross input | H11AA1 on D2 | none; D2 is unused |

The two parts that changed are not cosmetic. A zero-cross opto only conducts
inside a ±12 V (typ) / ±20 V (max) window around the crossing, so the current it
can push into the triac's gate is bounded by that window divided by the gate
resistor. See DESIGN.md for the arithmetic — it is why the *standard* triac
(BTA16-600B, I_GT up to 50 mA) is the wrong part in this position.

## The schematic is generated

`xiao-ac-ssr.kicad_sch` is written by `tools/gen_sch.py`. The circuit lives
there as a table of parts and nets; the generator draws each symbol, a stub wire
per pin and a label naming that pin's net. Open the result in KiCad 9 to review
it like any other schematic.

That indirection is deliberate: a hand-drawn schematic cannot be verified, and
a generated one can (see Gates).

## Gates

```sh
./tools/ci.sh
```

1. **Generator == committed file.** Regenerating leaves `xiao-ac-ssr.kicad_sch`
   and `symbols/xiao-ac.kicad_sym` byte-identical, so neither the committed
   schematic nor the symbol library it draws `J1`/`J2` from is ever stale.
2. **Netlist == intent.** `tools/check_netlist.py` exports a netlist with
   `kicad-cli` and asserts it against the intended netlist: every net present
   with exactly the intended pins, no unintended net at all (that would be a
   short), only the deliberately open pins reported unconnected, and every pin
   of the two XIAO socket rows carrying the *module's* pin name — `D0..D6` on
   `J1`, `VBUS, GND, 3V3_OUT, D10, D9/BOOT, D8, D7` on `J2` — so the schematic
   and its netlist say which pin is which instead of leaving it to a comment.
3. **ERC clean.** `kicad-cli sch erc` reports 0 violations.
4. **Board DRC clean.** `tools/check_board.py` — 0 errors, 0 warnings, including
   the 3 mm mains/logic clearance rule in `xiao-ac-ssr.kicad_dru`.
5. **Board == generator.** `tools/check_regen.py` regenerates the board in a
   throwaway copy of the tools and compares every footprint and every copper
   item against the committed board — 18 footprints (14 parts + 4 mounting
   holes) and 143 tracks+vias today.
   The board file is not *byte*-reproducible (pcbnew stamps fresh UUIDs and
   writes items in its own order), so this compares geometry, which is the part
   a person would have had to edit. `docs/PCB-NOTES.md` has the measurement.
6. **The gates' own tests.** `tools/tests/test_board_gate.py` breaks each
   rule that check 4 enforces — a moved or renamed hole, a track or pad inside
   the keepout, a hole tied to a net, a plated or undersized hole, a footprint
   id with no library nickname, a missing hole — and asserts `check_board.py`
   reports it. `tools/tests/test_pin_names.py` does the same for check 2's pin
   names: a renamed pin, the rows back to `Pin_1..Pin_7`, a renumbered row.
   A rule that has never been seen to fail is not a gate.

Fabrication data:

```sh
./tools/gerbers.sh          # build/gerbers/ + build/xiao-ac-ssr-gerbers.zip
```

## Circuit in one paragraph

Cord hot goes through a 3.15 A fuse, then feeds an MOV, the HLK-PM01's AC input
and the triac's A1; neutral runs straight through to the outlet, unswitched. The
HLK's isolated 5 V reaches the XIAO's VBUS pad through a Schottky diode. GPIO3
(D1) drives the MOC3063M's LED through 150 Ω; the opto's output waits for the
line to cross zero, then pushes current through 360 Ω into the BTA16-600SW's
gate, and the triac conducts the rest of the half-cycle. Part-by-part reasoning,
including the gate-drive arithmetic and what is deliberately *not* proven:
DESIGN.md.

## Bill of materials (all through-hole, 16 parts)

| Ref | Part | Note |
| --- | --- | --- |
| PS1 | HLK-PM01 | isolated 100–240 VAC → 5 V 0.6 A |
| F1 | 5×20 mm fuse clip + 3.15 A slow-blow | hot leg only |
| MOV1 | S14K150 varistor | 150 VAC rating |
| Q1 | BTA16-600SW | TO-220, snubberless logic level, I_GT 10 mA |
| U2 | MOC3063M | *zero-cross* opto-triac, DIP-6 |
| D5 | SS14 | Schottky, VBUS feed |
| R3 | 150 Ω | opto LED from 3.3 V (≈12 mA vs 5 mA I_FT) |
| R4 | 360 Ω | triac gate |
| C1 | 470 µF 16 V | 5 V bulk |
| C2 | 100 nF | XIAO decoupling |
| J1, J2 | 2 × 1×07 2.54 mm socket | XIAO: J1 = D0..D6, J2 = 5V..D7 |
| J3, J4 | 2-pole 5.08 mm screw terminal | cord in / load out |

Where to buy each one, and why: BOM.md.

## Safety — read before powering anything up

- The hot is switched and fused; the neutral is never broken and never fused
  on its own. Mains and logic copper are separated by a 3 mm rule *and* a routed
  isolation slot; nothing on the logic side is ever referenced to mains.
- **A triac fails short.** If Q1 or U2 dies, the load stays energised and no
  software can turn it off. Put a mechanical switch (or a switched cord) between
  the wall and this box, or accept that the only off switch is the breaker.
  A relay fails open instead; this is the price of a moving-contact-free switch.
- **Never work on it live. First power-up on a GFCI/RCD outlet. Never flash
  firmware with mains connected.** Insulation test (500 V) before first
  power-up if a megger is available.
- 3.15 A suits a ~60 W lamp; the ceiling is ~378 W at 120 V because that is what
  1.5 mm mains copper carries at a 10 °C rise (IPC-2221). Larger loads need the
  fuse, the copper *and* the triac's heatsinking rechecked — and the copper is
  currently the binding limit (see DESIGN.md, "the current ceiling").
- Size for **inrush**, not steady wattage: LED drivers and motors pull 10–20×.
  The triac is a 16 A part and will take it; the fuse is slow-blow for the same
  reason.
- Nothing here is a safety certification. The insulation barrier is the
  HLK-PM01, the opto and the layout, and the enclosure is yours. Plastic
  standoffs and a plastic box, never earthed metal.

## Files

```
xiao-ac-ssr.kicad_sch      generated schematic (the reviewable design)
xiao-ac-ssr.kicad_pcb      generated board -- never hand-edit
xiao-ac-ssr.kicad_dru      the 3 mm mains/logic barrier and the 1.5 mm mains width
xiao-ac-ssr.kicad_pro      project + netclass settings
symbols/xiao-ac.kicad_sym  the socket rows' symbols, pins named D0..D6 / VBUS..D7
sym-lib-table fp-lib-table so the libraries resolve without global config
tools/kicadlib.py          s-expression reader, symbol flattening (extends)
tools/gen_sch.py           the circuit + schematic generator
tools/gen_pcb.py           placement + board generator
tools/route.py             the maze router
tools/check_netlist.py     gate: exported netlist == intended netlist (and pin names)
tools/check_board.py       gate: kicad-cli pcb drc, exit 0 = no violations
tools/check_regen.py       gate: committed board == generated board (geometry)
tools/ci.sh                the gates
tools/gerbers.sh           fab output (gerbers, drill, zip)
tools/preview.sh           schematic svg/pdf + board svg, for human eyes
tools/zipdir.py            zip the gerber bundle (zip(1) is not installed here)
docs/PCB-NOTES.md          board status, and what the router needed
docs/ninny-brief.md        the next slice, briefed for a test-first agent
DESIGN.md                  engineering decisions and open items
BOM.md                     sourcing and mechanical notes
```

## Requirements

KiCad 9 (`kicad-cli`) and its Python bindings for the board step; ngspice is not
needed for this board:

```sh
sudo apt-get install kicad kicad-symbols kicad-footprints
```

Regenerate: `python3 tools/gen_sch.py`, then `/usr/bin/python3 tools/gen_pcb.py`
(the `pcbnew` bindings are not in a venv here).
