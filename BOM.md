# BOM — one board

Generated from the schematic, not typed from memory:

```bash
kicad-cli sch export bom --fields "Reference,Value,Footprint" \
  -o bom.csv xiao-ac-ssr.kicad_sch
```

16 parts. `bom.csv` is the source of truth for values and footprints; this file
adds the part of the BOM a generator cannot know: **where to buy it, and what it
costs to get it here.**

## The sourcing rule

> **Consolidate to the fewest orders first. Origin is a tiebreaker on price, not
> an absolute.** A US-origin part that saves a shipment wins; a $6 saving that
> creates a second shipment loses.

Two constraints in tension, both Harri's:

1. **Non-US origin preferred** — US-origin parts carry tariff and political
   cost. DigiKey's Canadian presence is welcome as a *channel* (one shipment,
   CAD pricing, traceability), not as a statement about origin.
2. **Shipping is per-supplier and it is not small.** DigiKey CA: **free delivery
   at $100 CAD or more; about $15 CAD below that** (their delivery page states
   the $100 threshold; the sub-$100 charge has been reported rising to $15).

So a BOM can carry more shipping than parts. Two ways out: **pad the order over
$100** (spares of the passives are nearly free, and more boards are coming), or
**accept the charge once** rather than paying it several times.

## Where each part comes from

| Source | Parts |
| --- | --- |
| **DigiKey CA** (one order) | `C1` 470 µF 16 V · `C2` 100 nF · `D5` SS14 · `F1` 5×20 mm fuseholder clip + 3.15 A slow-blow · `MOV1` S14K150 · `Q1` BTA16-600SW · `U2` MOC3063M · `R3` 150 Ω · `R4` 360 Ω · `J1`,`J2` 1×07 pin sockets · `J3`,`J4` 5.08 mm 2-pin terminal blocks |
| **AliExpress** | `PS1` HLK-PM01 5 V 3 W (about $1.79 CAD) |
| **Check the drawer first** | `U2` (a MOC3021M is *not* a substitute — see below) · all resistors · 100 nF / 470 µF caps · sockets |

**Check the drawer first, seriously** — but note that this board's two switching
parts are *not* interchangeable with the dimmer's. If you already have a
MOC3021M or a BTA16-600B in the drawer, neither goes on this board:

| part you might have | why it does not go here |
| --- | --- |
| MOC3021M (random phase) | it never waits for the zero crossing — it would switch at whatever phase the firmware happens to drive it, and there is no zero-cross detector on this board to time it with |
| BTA16-600B (standard gate) | I_GT up to 50 mA, and the zero-cross window cannot push that through a sensible gate resistor — see DESIGN.md, "Gate drive" |
| BTA16-600CW / BW (snubberless, 35 / 50 mA) | electrically fine if you accept R4 = 220 Ω (the window bound forces it), and *better* for inductive loads; the 10 mA `SW` is what this board is designed around |

## The two parts that changed, and what to order

| ref | order | note |
| --- | --- | --- |
| `U2` | **Lite-On MOC3063M** (DigiKey 4307927) | zero-cross, 600 V, **5 mA I_FT** grade, DIP-6 — Taiwanese origin *and* the cheapest of the three |
| `Q1` | **ST BTA16-600SW** — order code `BTA16-600SWRG`, DigiKey part number **497-3389-5-ND** (page 669146) | TO-220, 16 A, insulated tab, **I_GT 10 mA**, snubberless logic level |

Checked on DigiKey at the time of writing (single-unit list, USD — **verify at
order; the manufacturer order codes above are the durable part of this table**):

| part | brand | origin | unit | 50-off |
| --- | --- | --- | --- | --- |
| MOC3063M | **Lite-On** | TW | **$0.92** | — |
| MOC3063M | onsemi | US brand, Malaysian assembly | marketplace listing only (Rochester stock; 303,933 available) | — |
| VO3063 | Vishay | US-listed / European opto division | $1.33 | — |
| BTA16-600SWRG | **ST** | CH/IT/FR | **$2.14** | $1.03 |

So the pair is about **$3.06 USD**, and the origin-preferred opto is also the
cheap one — no tension to resolve. `EL3063` (Everlight, TW) is the third
same-spec option if Lite-On is out of stock; it is the same 5 mA I_FT zero-cross
DIP-6 pinout and the same footprint.

**The triac has no origin problem:** ST is Swiss-Italian-French and
`BTA16-600SWRG` is the part the datasheet's Table 4 is written around. There is
a `BTB16-600SW` (non-insulated tab) which is cheaper but needs an insulating pad
under any heatsink — take the `BTA`.

### Why not the DigiKey alternative for PS1

Mean Well IRM-03-5 (`1866-3020-ND`) is the electrical equivalent (5 V 3 W 0.6 A,
85–305 VAC in) and DigiKey stocks it, but: it is a US-brand part at about $8.17
CAD after tariff against $1.79; the swap costs **footprint change plus rerouting
PS1's pads and a re-check of the 3 mm barrier**; and the HLK-PM01's footprint is
already in the design. DigiKey publishes no Hi-Link parts at all. **HLK-PM01
input range: 100–240 VAC, universal** — listings titled "220V to 5V" are using
the Chinese-market convention; it works on North American 120 V mains. Max input
current <0.2 A.

## Mechanical — mounting

Four M3 clearance holes are on the board: one per corner, **5 mm inset** from the
board edge, `MountingHole:MountingHole_3.2mm_M3` — a **non-plated 3.2 mm** hole
with no pad, so nothing is bonded and nothing sits under the screw head. Each
owns a **6 mm copper keepout** (no track, via or pad edge within 3 mm of the hole
centre) and the router blocks that disc, not just the hole.

This is the dimmer's `a32a414` pass applied to this board, which was generated
from the dimmer's tools before it and so had no holes at all:

- The mounting pads stay **isolated** — connected to no net, no copper ring
  under the screw head.
- **Nylon standoffs, not metal.** This is a two-wire appliance with no earth
  conductor, so there is nothing for a metal standoff or a metal enclosure to be
  safely bonded to. Plastic standoffs and a plastic box avoid the question
  entirely.
- Both the holes and the keepout are gated: `tools/check_board.py` checks the
  position, the 3.2 mm non-plated drill, the net and the copper clearance on the
  saved board, and `tools/tests/test_board_gate.py` breaks each of those rules
  one at a time to prove the check has teeth.
- The corner courtyards pushed the packing down 3 mm, and nothing else changed:
  the routing is the pre-hole routing translated 3 mm, item for item. The board
  did **not** grow — see `docs/PCB-NOTES.md`.

## Mechanical — board outline

**150 × 45mm (67.5cm²)**, down from 150 × 95mm (142.5cm²). The 14 parts span
33.8mm top to bottom (y 9 → 42.8mm; y 6 → 39.8mm before the mounting holes
pushed the packing down), so the old 95mm left a **55mm dead band along the
bottom edge** — more than half the board. The outline was inherited
from the dimmer, which had raised its own height to 95mm while the router was
failing; this board was generated from that state, so it inherited the dead band
without ever having had the failure. See `BOARD_H` in `tools/gen_pcb.py`, and
`docs/PCB-NOTES.md` for the measured floor.

## Mechanical — thermal

`Q1` (BTA16-600SW) is the only real heat source. Its dissipation is the on-state
drop times load current, roughly 1.0–1.2 V at 1 A:

| Load | Dissipation | Verdict |
| --- | --- | --- |
| 60 W lamp (~0.5 A) | ~0.6 W | No heatsink. ~35 °C rise on a TO-220 in free air |
| 100 W lamp (~0.85 A) | ~1.0 W | Borderline. ~60 °C rise; a small clip-on heatsink is cheap insurance |
| Board ceiling, 3.15 A | ~3.5–4 W | **Real heatsink required.** ~5 °C/W, tab-mounted |

- **BTA (isolated tab), not BTB.** The `A` part's tab is electrically isolated,
  so a heatsink needs no insulating pad. Keep it heatsink **floating** —
  connected to no net.
- In an **enclosed box** the ambient is 40–50 °C, not 25 °C. Derate accordingly;
  the numbers above assume free air.
- `PS1`, `MOV1` and the fuse are thermally irrelevant at this power level.
- Ventilation in the box is worth more than a bigger heatsink.

## What this board can switch

Both bounds come from parts, not from opinion:

- **Ceiling: 3.15 A ≈ 375 W at 120 V** — `F1`'s rating and the 1.5 mm mains copper (3.21 A by
  IPC-2221, 1 oz, 10 °C rise). The triac is a 16 A part and is never the limit.
- **Floor: about 10 W at 120 V** — a triac only stays on above its holding current, and it only
  latches above its latching current: `BTA16-600SW` is `I_H` 15 mA, `I_L` 25–30 mA max, which at
  120 V is 2–4 W. Below that the load may refuse to latch or drop out at the next zero crossing.
  Very small LED lamps are the usual victims; test them rather than assuming.

| load | `I(rms)` | in `Q1` | ΔT on a bare TO-220 | verdict |
| --- | --- | --- | --- | --- |
| 60 W lamp | 0.50 A | ~0.7–1.0 W | 40–60 °C | no heatsink needed |
| 100 W lamp | 0.83 A | ~1.0–1.4 W | 60–85 °C | works; in a sealed box add a clip-on heatsink or a vent — `T_j` max is 125 °C |
| 375 W (the ceiling) | 3.12 A | ~4 W | — | real heatsink required (~5 °C/W, tab-mounted) |
| 1500 W | 12.5 A | ~18 W | — | **not this board.** 4× the fuse; and 12.5 A is past the 80 % continuous rule on a 15 A branch circuit (12 A / 1440 W) |

`R_th(j-a)` = 60 °C/W is the datasheet's own TO-220 figure, no heatsink; `I_TSM` is 160–168 A for
20 ms, so inrush (a cold lamp filament, a motor start) is never the thing that limits you.
Continuous current is.

By load type:

- **Resistive** (lamps, heaters, elements) — what the board is for. It switches at the zero
  crossing and only there, which is why it is quiet and why it cannot dim.
- **Inductive** (fans, small motors, transformers) — the `SW` suffix is ST's recommendation for
  inductive loads (commutation `(dI/dt)c` 8.5 A/ms, no snubber). Note its *static* `dV/dt` is the
  family's lowest at 40 V/µs; a `CW`/`BW` part has 500/1000 V/µs and costs R4 = 220 Ω, as the
  swap table above says. This board has no RC snubber across `Q1`.
- **Capacitive-input SMPS** as the load — the awkward case: zero-cross turn-on into an empty
  capacitor is worst-case inrush. The triac survives it; the load may not.
- **Never DC** — a triac has no commutation of its own and latches on until the current stops.

## Reaching 1500 W — what it would actually take

1500 W at 120 V is **12.5 A**. Four separate limits move, and the heatsink is only one of them.

**Thermal.** `Q1` dissipates ~13.5 W (datasheet model, `V_TO` 0.85 V + `R_D` 25 mΩ) to ~17.5 W
(Figure 2's max curve) at 12.5 A. With `R_th(j-c)` = 2.1 °C/W for the insulated BTA, holding the
junction at 110 °C in 50 °C box air needs a heatsink of **~2 °C/W** — a 100 mm-class finned
extrusion, not a clip-on. A **fan only helps if the box breathes**: in a sealed box it stirs the
same air, and 15 W in a 100 × 70 × 40 mm box raises the internal air 45–110 °C above room
(45 °C at h = 12 W/m²K, 109 °C at h = 5). That cooks `C1` (7000 h @ 105 °C) and passes the
module's 85 °C rating. **At this power the enclosure decides, and ventilation is not optional.**

**Copper — the limit that makes it a different board.** 12.5 A by IPC-2221, external layer:

| copper | 10 °C rise | 30 °C rise |
| --- | --- | --- |
| 1 oz | 9.8 mm | 5.0 mm |
| 2 oz | 4.9 mm | 2.5 mm |
| 3 oz | 3.3 mm | 1.7 mm |

This board's router tops out at **1.5 mm** today, and `docs/ninny-brief.md` exists to teach it a
necked pad entry for **2.0 mm = 3.95 A ≈ 475 W** — that is the entire scope of the improvement.
1500 W is not a widening; the load current has to leave the PCB.

**Fuse, terminals, cord, branch circuit.** `F1` 3.15 A → 16 A HBC in the same 5×20 clips; the
Phoenix MKDS 1,5 is rated 13.5 A (93 % of it at 12.5 A) so a 20–24 A block is the right swap; 12 AWG
cord; and 12.5 A is **past the 80 % continuous rule on a 15 A circuit** (12 A / 1440 W), so a 20 A
branch circuit is part of the requirement.

**The two sane routes to 1500 W.**

1. **Switch a contactor coil** — a 20 A definite-purpose contactor draws ~5–10 VA on its coil, needs
   no heatsink, and this board switches it within its existing limits (a coil is exactly the
   inductive load the `SW` part is specified for). 1500 W never touches the PCB.
2. **Drive an external SSR** — a 40 A chassis puck (~$15–25). Note it brings its own thermal job:
   at 12.5 A and `V_TM` ~1.6 V it dissipates ~20 W, so it needs a ~2 °C/W heatsink too.

Either way the board becomes the pilot. Adding a fan and a heatsink to *this* board fixes the
smallest of the four limits and leaves copper, fuse and branch circuit exactly where they were.

## Ordering note — the current ceiling

`F1` stays at 3.15 A, which is what 1.5 mm/1 oz copper carries at a 10 °C rise
(IPC-2221). Do **not** simply fit a bigger fuse to drive a bigger load: the fuse
protects the copper, and the copper cannot be widened past the triac's middle
pad on this board (measured: 1.5 mm routes, 2.0 mm does not — DESIGN.md, decision
9). A bigger load wants the load switched off-board, or a necked pad entry added
to the router (`docs/ninny-brief.md`).
