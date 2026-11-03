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

**Status: schematic and board complete and machine-checked. Gerbers exported
but not yet eyeballed in a gerber viewer and not yet checked by a fab's DFM
rules.**

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
   byte-identical, so the committed schematic is never stale.
2. **Netlist == intent.** `tools/check_netlist.py` exports a netlist with
   `kicad-cli` and asserts it against the intended netlist: every net present
   with exactly the intended pins, no unintended net at all (that would be a
   short), and only the deliberately open pins reported unconnected.
3. **ERC clean.** `kicad-cli sch erc` reports 0 violations.
4. **Board DRC clean.** `tools/check_board.py` — 0 errors, 0 warnings, including
   the 3 mm mains/logic clearance rule in `xiao-ac-ssr.kicad_dru`.

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
| J1, J2 | 2 × 1×07 2.54 mm socket | XIAO |
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
sym-lib-table fp-lib-table so the libraries resolve without global config
tools/kicadlib.py          s-expression reader, symbol flattening (extends)
tools/gen_sch.py           the circuit + schematic generator
tools/gen_pcb.py           placement + board generator
tools/route.py             the maze router
tools/check_netlist.py     gate: exported netlist == intended netlist
tools/check_board.py       gate: kicad-cli pcb drc, exit 0 = no violations
tools/ci.sh                the gates
tools/gerbers.sh           fab output (gerbers, drill, zip)
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
