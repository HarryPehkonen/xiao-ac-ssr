# Design notes

One-channel inline AC solid-state switch: cord in (J3), load out (J4), a XIAO
ESP32C3 in two 7-pin sockets, a zero-cross opto-triac driving a snubberless
triac in the hot leg. Strictly on/off — no dimming, no phase control.

Same family as `xiao-ac-dimmer`. What is copied and what is replaced is listed in
README.md; this file is the reasoning, including the arithmetic behind the two
parts that changed and the answers to the open questions the work was scoped
with.

## Decisions, and why

1. **In-house zero-cross opto + triac, not a certified SSR puck on 5 V.** (The
   ticket's open question 1.) The board already *is* the encapsulated function
   minus the epoxy, and the gates can only verify what is on the board: an
   external puck puts the load current, the switching element and its thermal
   path inside a black box that this repo cannot check at all. Cost ~$1.50 for
   the opto + triac, versus $20–60 for a recognised-brand puck; and the cheap end
   of that market is exactly where the counterfeits live (Fotek-class parts
   tested at a fraction of their label). The honest counter-argument, kept
   because it is real: a puck carries UL/CSA *recognition* that a hobby board
   does not, and it moves the load current off this board — see decision 9 for
   why that matters if the load ever grows.
2. **Zero-cross opto (MOC3063M), not the dimmer's random-phase MOC3021M.** With
   no phase control there is nothing to time, so the opto may as well switch
   *near the zero crossing*: lower dI/dt into the load, no inrush from switching
   at the peak, and no zero-cross detector needed.
3. **The triac changes too: BTA16-600SW, not BTA16-600B.** This is the decision
   the ticket did not anticipate, and the arithmetic is in "Gate drive" below.
   Short version: a zero-cross opto only conducts inside a ±12 V (typ) / ±20 V
   (max) window, so the gate current it can deliver is the window divided by the
   gate resistor. The standard `B` triac needs up to 50 mA, which the window
   cannot reliably push through a sensible gate resistor; the `SW` logic-level
   part needs 10 mA and latches ~7 V into the crossing. Same footprint, same
   package, same price.
4. **360 Ω gate resistor** — onsemi's own figure-10 value, and the only value
   that satisfies both bounds at once (>=170 Ω to keep the off-window surge
   under the opto's 1 A rating; small enough that I_GT is reached inside the
   inhibit window).
5. **150 Ω LED resistor, not 220 Ω.** The MOC3063M is the 5 mA I_FT grade
   (15 / 10 / 5 mA for MOC3061/3062/3063), and I_FT rises ~1.5× at −40 °C, so
   the LED needs ≥7.5 mA in the worst case. 220 Ω gives 9 mA — barely enough
   warm, not enough cold. 150 Ω gives 12 mA and still costs the GPIO nothing
   (12 mA against a 20 mA recommended pin current). *Note for the sibling
   project: the dimmer drives a MOC3021M — a 15 mA I_FT part — through 220 Ω,
   which is ~9 mA. That looks like a real bug in the dimmer, and it is not fixed
   here; this repo only had to get its own LED right.*
6. **No snubber, and no zero-cross detector.** The ticket's reason ("zero-cross
   means no phase control, so no snubber") is the right conclusion for the wrong
   reason: a snubber is there for *commutation* dV/dt, which phase control has
   nothing to do with. The snubber is genuinely absent here because (a) the part
   is a *snubberless* triac — ST says of the W-suffix family "especially
   recommended for use on inductive loads, because of their high commutation
   performances" — and (b) the intended load is resistive. The boundary is
   recorded, not hidden: BTA16-600SW's static dV/dt is 40 V/µs, the lowest in
   the BTA16 family (CW 500, BW 1000). At 120 V the line only slews
   0.064 V/µs through a crossing, so that is ample for a lamp and *not* a claim
   about motors. For a hard inductive load: BTA16-600BW + R4 = 220 Ω (I_GT is
   50 mA on that part, so the window bound forces the smaller resistor; the surge
   is then 0.77 A, still under the opto's 1 A), or fit the snubber. onsemi's own
   wording is the standing warning: the 39 Ω + 0.01 µF is "often, but not always,
   necessary depending upon the particular triac and load used."
7. **Load type: zero-cross is right for both** (the ticket's open question 2),
   but the ticket's premise is backwards. "A zero-cross SSR fires at the worst
   instant for capacitive-input drivers" would be true of a *relay* or a
   random-phase switch: the worst instant for a capacitive load is closing at
   the voltage *peak*, into a discharged capacitor. Zero-cross fires at the
   voltage *minimum*, which is the gentle instant for incandescent (cold
   filament) and capacitive (inrush) loads alike. The real caveats are that the
   window is ±12 V typ rather than exactly zero, and that a driver's input
   capacitor may still hold charge from the previous half-cycle, so "near zero"
   is not zero. That is exactly the situation onsemi's snubber note is about —
   measure with the actual load, and bulb behaviour cannot be simulated anyway.
8. **Hot-only switching, continuous neutral, fused hot, MOV after the fuse,
   Schottky between the HLK's +5 V and VBUS.** Carried unchanged; the reasoning
   is the dimmer's and it is still right.
9. **The current ceiling stays at 3.15 A** (the ticket's open question 3) — not
   because the parts could not take more, but because the *copper* cannot be
   widened. The load current has to reach the triac's middle pad, and its two
   neighbours sit one 2.54 mm pitch either side. Measured geometry and IPC-2221
   arithmetic:

   | mains copper | IPC-2221 carry (1 oz, 10 °C rise) |
   | --- | --- |
   | 1.0 mm | 2.39 A |
   | **1.5 mm** | **3.21 A** |
   | 2.0 mm | 3.95 A |
   | 2.5 mm | 4.65 A |
   | 2.775 mm | 5.01 A |
   | 3.6 mm | 6.05 A |

   Between the middle pad's two neighbours there are 3.175 mm edge to edge, so
   pure DRC geometry would allow a 2.775 mm trace. The router's 0.5 mm grid plus
   its safety slack caps that at 2.067 mm — and on the real board **1.5 mm
   routes and 2.0 mm does not** (`10/11 nets, LOAD_L: no path J4.1 -> Q1.2,
   pad-veto 132/144, free 12 cells, no path`). So: 3.15 A fuse, 1.5 mm copper,
   ~378 W at 120 V / ~756 W at 230 V, same as the dimmer. To go higher you need
   either a necked pad entry in the router (a feature this board does not have;
   see `docs/ninny-brief.md`) or a device that keeps the load current off this
   board — which is the one real argument for decision 1's alternative.
10. **Copy the dimmer as a template repo, not a submodule** (open question 4).
    One repo, self-contained, no cross-repo build coupling; the shared parts are
    16 lines of tables in `gen_sch.py`. A submodule would have made the two
    boards share a router but also share its bugs and its fixes, and the router
    did in fact need fixing here (see `docs/PCB-NOTES.md`).
11. **Pin choice unchanged: D1 (GPIO3) drives the opto.** On an ESP32-C3, GPIO2,
    8 and 9 are strapping pins and a load on them can stop the board booting.
    D2 (GPIO4) was the dimmer's zero-cross input and is unused here, as is the
    3V3 pin — this board has no mains-referenced logic side at all, which is the
    whole point of the simplification.
12. **XIAO socket order, the 3.15 A fuse, the MOV, the HLK, the 470 µF bulk:**
    all carried over from the dimmer, including the instruction to confirm the
    5 V/GND pad order against the physical board with a continuity check before
    applying power.
13. **Firmware is trivial here.** No zero-cross ISR, no delay timer: one GPIO,
    high or low. ESPHome's plain `switch: gpio` (or ten lines of Arduino) is the
    whole program.

## Gate drive — the arithmetic behind decisions 3 and 4

Datasheet numbers used (onsemi MOC306x-M; ST BTA16/BTB16):

| symbol | value |
| --- | --- |
| MOC3063M I_FT (max LED trigger current) | 5 mA (×1.5 at −40 °C → 7.5 mA) |
| MOC3063M V_INH (above this it will not trigger) | 12 V typ, **20 V max** |
| MOC3063M V_TM (output on-state) | ≤ 3 V peak at 100 mA |
| MOC3063M I_TSM (peak repetitive surge) | 1 A (100 µs, 120 pps) |
| BTA16-600SW I_GT / V_GT | ≤ 10 mA / ≤ 1.3 V (quadrants I–III) |
| BTA16-600B I_GT | ≤ 50 mA (I–III), 100 mA in IV |

The opto's output, the 360 Ω resistor and the triac's gate are in series with
the load path, so the gate current available at the moment the opto turns on is

    I_G = (V_window − V_GT − V_TM) / R4

At the worst-case window (20 V) and worst-case drops: (20 − 1.3 − 3)/360 =
**43.6 mA**, four times the SW part's 10 mA. At the typical window (12 V):
(12 − 1.3 − 1.8)/360 = **24.7 mA**, still 2.5×. The triac latches when
I_GT × R4 is reached, i.e. 10 mA × 360 Ω = 3.6 V plus ~3.1 V of drops ≈ **6.7 V**
into the crossing — about 2.3° of phase on a 170 V peak. That is what "fires at
the zero crossing" actually means here.

The same arithmetic with the dimmer's `B` part: 50 mA × 360 Ω = 18 V plus 3.1 V
of drops = 21.1 V, *outside* the 20 V window the opto will even conduct in. A
zero-cross opto plus a standard-gate triac can fail to fire at all; the B part
would need R4 ≤ 338 Ω, and that leaves exactly zero margin at the window edge.
Hence the `SW`.

The other bound on R4 is the *other* end of the half-cycle: if the triac has not
latched by the time the line reaches its peak (170 V at 120 V rms), the current
is limited only by R4 — 170/360 = **0.47 A**, under the opto's 1 A I_TSM. Any
R4 below ~170 Ω would exceed it.

LED side: (3.3 − 1.5)/150 = **12.0 mA** against a 7.5 mA worst-case requirement,
with the LED's forward drop taken at its datasheet maximum rather than typical.

## What the gates prove

- `tools/check_netlist.py` — the netlist exported from the schematic equals the
  intent: **11 nets**, no extras, 13 pins deliberately open and nothing else.
- `kicad-cli sch erc --severity-all --exit-code-violations` — 0 violations.
- `tools/check_board.py` — `kicad-cli pcb drc`: **0 errors, 0 warnings**, with
  the 3 mm mains/logic barrier and the 1.5 mm mains width enforced as `kicad_dru`
  rules rather than as good intentions. It then checks the two rules DRC has no
  rule for: every footprint id names its library, and the four M3 mounting holes
  are 5 mm inset with a 3.2 mm non-plated drill, no net, and no copper within
  3 mm of the centre.
- `tools/check_regen.py` — the committed board is the generated board: 18/18
  footprints and 143/143 copper items identical after a regeneration in a
  throwaway copy of `tools/`. The board file itself is not byte-reproducible
  (pcbnew UUIDs, write order), so this compares geometry — the part a person
  would have had to edit. `docs/PCB-NOTES.md` has the measurement and the
  teeth demonstration.
- `tools/gen_pcb.py` — 11/11 nets routed from the schematic netlist, so the
  board cannot disagree with the design about connectivity.

## What is NOT proven

- **No safety claim of any kind.** Nothing here certifies the board for mains
  use. The barrier is the HLK-PM01, the opto and the layout; the enclosure, the
  GFCI first power-up and the 500 V insulation test are yours.
- **No simulation.** Unlike the dimmer there is no ngspice deck here, because
  the numbers that matter are datasheet limits (a DC driver-strength argument),
  not a curve. The claims in "Gate drive" are arithmetic against datasheet
  maxima, not measurements.
- **Bulb behaviour cannot be simulated** and is not claimed: inrush, flicker and
  buzz in LED drivers are bench measurements.
- **Thermal**: Q1's dissipation is the on-state drop times load current,
  ~1.0–1.2 V at 1 A. At the 3.15 A ceiling that is ~3.5–4 W, and the tab needs
  a real heatsink (~5 °C/W). The `A` in BTA16 means an **isolated tab**, so the
  heatsink needs no insulating pad — but keep it floating, connected to no net.
  In a sealed box the ambient is 40–50 °C, not 25 °C.
- **A triac fails short.** If Q1 or U2 dies, the load stays energised and
  software cannot turn it off. This board has no mechanical off switch: put one
  in the cord, or accept that the breaker is the off switch. This is inherent to
  the SSR choice and is not fixable in firmware.
- **Fab DFM**: a clean DRC is not a fab's design-rule check. Open the gerbers in
  a viewer before ordering.

## Open items / known weak points

- **The corner keepouts have never bound here.** They are on the board for the
  next placement change rather than for this one: on this board the corners were
  already clear and the routing is the pre-hole routing translated 3 mm, so
  nothing about the current copper depends on the keepout. The dimmer is where
  the inflation was measured against a real violation. Plastic (nylon) standoffs
  and a plastic box only — this is a two-wire appliance with no earth conductor,
  so there is nothing for earthed metal to bond to.
- **The 2.067 mm copper cap** is a router-model limit, not a physical one; see
  `docs/ninny-brief.md` for the necked-pad-entry slice that would lift it.
- **The bottom-layer pour is absent** (there is no pour at all): the barrier is
  easier to guarantee without one, and this board has no thermal need for it.
- **Q1 has no pre-latch protection** beyond the gate resistor; that is normal for
  this circuit and the opto's 1 A rating is the limit that matters.
- Cosmetically the board is a generated maze: 1.5 mm mains runs, a single-cell
  corridor into the triac's middle pad, and silkscreen references placed by
  `AutoPlaceFields()`. Review the rendered board and gerbers
  (`./tools/preview.sh`, then `./tools/gerbers.sh`), not a mental picture.
