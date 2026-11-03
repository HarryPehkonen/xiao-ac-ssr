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

The board has **no mounting holes yet** — the dimmer has had four since `a32a414`
and this board, built before that, never picked them up. Adding them
is a small change to `tools/gen_pcb.py`, not a redesign:

- 4 × M3 clearance holes (3.2 mm drill) in the corners, **5 mm inset** from the
  board edge, each with a 6 mm copper keepout so no net comes near the screw.
- The mounting pads stay **isolated** — connected to no net, no copper ring
  under the screw head.
- **Nylon standoffs, not metal.** This is a two-wire appliance with no earth
  conductor, so there is nothing for a metal standoff or a metal enclosure to be
  safely bonded to. Plastic standoffs and a plastic box avoid the question
  entirely.
- Adding holes means re-running the router: the corner keepouts change the
  available corridors. Cheap now that the gate is known-good.

## Mechanical — board outline

**150 × 45mm (67.5cm²)**, down from 150 × 95mm (142.5cm²). The 14 parts span
33.8mm top to bottom (y 6 → 39.8mm), so the old 95mm left a **55mm dead band
along the bottom edge** — more than half the board. The outline was inherited
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

## Ordering note — the current ceiling

`F1` stays at 3.15 A, which is what 1.5 mm/1 oz copper carries at a 10 °C rise
(IPC-2221). Do **not** simply fit a bigger fuse to drive a bigger load: the fuse
protects the copper, and the copper cannot be widened past the triac's middle
pad on this board (measured: 1.5 mm routes, 2.0 mm does not — DESIGN.md, decision
9). A bigger load wants the load switched off-board, or a necked pad entry added
to the router (`docs/ninny-brief.md`).
