# BRINGUP.md — xiao-ac-ssr: assembly verification, first power-up, troubleshooting

One-channel inline AC **on/off** switch for a Seeed XIAO ESP32C3. Mains in at `J3`,
switched mains out at `J4`. Zero-cross opto-triac (`U2` MOC3063M) driving a
`Q1` BTA16-600SW. **It does not dim** — it switches at the zero crossing and only there.

Read this with multimeter in hand. Everything below works with a DMM; the oscilloscope is
**not** needed for this board (it is needed for the dimmer sibling, which has a firing angle
and a zero-cross detector to verify — this board has neither).

---

## Fabrication parts list (as ordered, DigiKey CA, 2026-11)

Four boards' worth, plus spares. `qty` is what was ordered; `need` is what four boards consume.

| qty | need | DigiKey PN | MPN | What it is / why |
|---|---|---|---|---|
| 4 | 4 | `497-BTA16-600SWRG-ND` | BTA16-600SWRG | Triac. **Logic-level gate (I_GT 10 mA)** — required, see DESIGN.md "Gate drive". A `-600B` standard-gate part does **not** work here. |
| 4 | 4 | `MOC3063M-ND` | MOC3063M | Zero-cross opto-triac, 600 V, DIP-6. onsemi grade (5 mA I_FT), so `R3` = 150 Ω stays valid. |
| 10 | 8 | `36-3512P-ND` | 3512P | Keystone fuse clips, 2 per board. The `F1` footprint is drawn for **this** clip pattern. |
| 5 | 4 | `283-2931-ND` | `BK/S505-3.15-R` | 3.15 A 250 V ceramic **high-breaking-capacity** (1500 A @ 250 VAC) time-lag 5×20 mm. A glass low-breaking fuse (e.g. Littelfuse 218) is *not* equivalent for mains service. |
| 4 | 4 | `495-6591-1-ND` | B72214S0151K551 | Varistor S14K150 (EPCOS/TDK), 14 mm disc. |
| 4 | 4 | `493-15239-1-ND` | UHE1E471MPD1TD | `C1` 470 µF 25 V, φ8 × 20 mm, **3.5 mm lead spacing**, 7000 h @ 105 °C. Fits the `D8.0mm_P3.50mm` footprint exactly. |
| 4 | 4 | `BC5229CT-ND` | K104K15X7RF5UH5 | `C2` 0.1 µF 50 V X7R radial, **5.0 mm lead spacing**, 3.0–3.8 mm body. |
| 4 | 4 | `1801-1N5819CT-ND` | 1N5819 | `D5` Schottky 40 V 1 A, DO-204AL (**DO-41**, through-hole) — matches the axial footprint. |
| 10 | 4 | `150XBK-ND` | MFR-25FBF52-150R | `R3` 150 Ω 1/4 W — sets the opto LED current. |
| 10 | 4 | `13-MFR-25FTE52-360RCT-ND` | MFR-25FTE52-360R | `R4` 360 Ω 1/4 W — gate resistor. |
| 5 | 4 | `1597-113991054-ND` | 113991054 | XIAO ESP32C3 module. Must be the **C3**, not S3/C6 — the pin↔GPIO map differs. |
| 2 | 2 | `1597-102010490-ND` | 102010490 | 7-pin male headers for the XIAO, **5-pack** — two packs = 10 headers, 8 used. |
| 10 | 8 | `S7005-ND` | PPTC071LFBN-RC | `J1`,`J2` 1×7 female sockets, 2.54 mm, vertical. The XIAO plugs into these. |
| 10 | 8 | `732-10955-ND` | 691137710002 | `J3`,`J4` 2-position side-entry screw blocks, 5.00 mm pitch, 16 A/300 V. |
| — | 4 | *(AliExpress)* | HLK-PM01 | `PS1` 5 V 0.6 A isolated AC-DC module. Not a DigiKey line. |

### Known footprint issue — `MOV1` (fix before the next fabrication run)

KiCad's own `Varistor.pretty/RV_Disc_D12mm_W4.5mm_P7.5mm` places its two pads **diagonally**:

```
(pad "1" thru_hole circle  (at 0 0)
(pad "2" thru_hole circle  (at 7.5 1.8)
```

Measured on the board: pad 1 at (6.53, 24.25), pad 2 at (14.03, 26.05) — 7.50 mm apart in x
**and 1.80 mm apart in y**, i.e. 7.71 mm diagonally. A straight-lead disc varistor (the ordered
S14K150 has coplanar leads 7.5 mm apart) therefore **cannot seat without bending one lead**.
The footprint is also drawn for a 12 mm disc while the part is 14 mm; lateral clearance is fine
(nearest foreign copper is 9.13 mm from the lead centre, a 14 mm disc needs 7.00 mm), so the
*only* defect is the staggered holes. Fix: redraw `MOV1` as a straight 7.5/0 pattern in
`tools/gen_pcb.py`, regenerate, and re-run `./tools/ci.sh`.

---

## A. Dead board — no power, no USB. Catches most assembly faults

| # | Measurement | Expected | Measured |
|---|---|---|---|
| A1 | Fuse continuity (fuse out of the clips) | short / ~0 Ω | |
| A2 | **Neutral in → neutral out** | ~0 Ω (a straight conductor: neutral is never switched) | |
| A3 | **Hot in → hot out**, SSR off | open / high (the triac is off) | |
| A4 | **Mains-side copper ↔ 5 V / logic-side copper** | OL or >20 MΩ. *Anything else: stop, you have a bridge across the isolation barrier.* | |
| A5 | `U2` opto LED, pins 1–2 (diode test) | ~1.2 V one way, open the other | |
| A6 | Across `MOV1` | essentially open at meter voltage (a shorted MOV is dead) | |
| A7 | Neutral→hot at the input terminals (with the load unplugged) | high — the MOV reads essentially open | |

A2/A3 together verify the design rule *switch the hot, keep the neutral continuous* — the most
safety-relevant property of an inline switch, and a 10-second check.

## B. Logic side — no mains. Verify the drive path before anything gets hot

Power the XIAO from **USB with mains disconnected**.

| # | Measurement | Expected | Measured |
|---|---|---|---|
| B1 | Across `R3` (150 Ω), GPIO3 **high** | ~2.1 V → **~12 mA** into the opto LED (the MOC3063 needs ~5 mA to trigger) | |
| B2 | Across `R3`, GPIO3 **low** | ~0 V | |
| B3 | `U2` pin 1 to pin 2, powered | ~1.2 V (LED conducting) when high | |

B1 is the number to write down: it proves GPIO → R3 → LED end to end with no mains present.

## C. Mains and load — with a **real load**, never open-circuit

Use a GFCI outlet, and an incandescent or other resistive lamp as the load.

> **Why a real load:** a triac needs **holding current** to stay on. With nothing connected it
> reads as "not switching" even when the board is perfect. This is the most common false
> diagnosis on a triac board.

| # | Measurement | Expected | Measured |
|---|---|---|---|
| C1 | HLK output, USB unplugged (at the XIAO 5 V pin) | ~4.7 V (5 V minus the `D5` Schottky drop) | |
| C2 | Across `Q1` MT1–MT2, GPIO3 **low** | full mains (~120 V AC) | |
| C3 | Across the load, GPIO3 **low** | ~0 V, lamp off | |
| C4 | Across `Q1` MT1–MT2, GPIO3 **high** | **~1–1.5 V** (on-state drop) | |
| C5 | Across the load, GPIO3 **high** | mains, lamp on | |

C2/C4 *are* the functional verification: the switch state is legible as the voltage across the
triac. Nothing else is needed to prove the board works.

## D. Triage

| Symptom | Next check |
|---|---|
| B1 shows ~0 V with GPIO high | Wrong GPIO in firmware (must be **D1 = GPIO3**), or the opto is in backwards (pin 1 marking), or a bad `R3` joint. |
| LED driven (B1 ≈ 12 mA) but the triac never turns on | Load not connected / no holding current; or an open joint on the gate or MT1. |
| Triac always on | Shorted triac, or a solder bridge across MT1–MT2 — A3 finds it cold. |
| Works, then drops out under load | Thermal or overload: check the fuse, then the tab temperature. |
| Triac hot to touch in service | Normal is warm: ~1–3 V drop at load current = 3–5 W. Too hot to hold (>70 °C case) means load or heatsink, not a marginal part. |

## E. Firmware and toolchain (nothing installed yet)

The board's control input is trivial: **drive D1 (GPIO3) high to turn the load ON, low to turn it
OFF.** Active high — the GPIO sources the LED current through `R3`.

Recommended toolchain for the C3 on a headless Debian box: **ESP-IDF v5.x**, installed from
Espressif's installer (it brings its own Python venv and toolchain, so nothing system-wide is
touched):

```bash
# one time
mkdir -p ~/esp && cd ~/esp
git clone -b v5.5 --recursive https://github.com/espressif/esp-idf.git
cd esp-idf && ./install.sh esp32c3
# every session
. ~/esp/esp-idf/export.sh
idf.py set-target esp32c3
idf.py build && idf.py -p /dev/ttyACM0 flash monitor
```

Minimal control for bring-up (a blink of the load, ~1 Hz):

```c
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define TRIGGER_GPIO 3          /* XIAO D1 */

void app_main(void) {
    gpio_reset_pin(TRIGGER_GPIO);
    gpio_set_direction(TRIGGER_GPIO, GPIO_MODE_OUTPUT);
    while (1) {
        gpio_set_level(TRIGGER_GPIO, 1);
        vTaskDelay(pdMS_TO_TICKS(1000));
        gpio_set_level(TRIGGER_GPIO, 0);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

Alternatives if ESP-IDF feels heavy: PlatformIO (same C, simpler build) or Arduino-ESP32
(`digitalWrite`) — both work, but ESP-IDF is the vendor-supported path and needs no wrapper.
Flashing happens over USB-C with **mains disconnected**; the XIAO's USB and the HLK's 5 V are
isolated from each other by `D5` on this board, but do not test that distinction with mains live.

## F. Safety

- First mains test on a **GFCI outlet**; never work on it live; the case is not a substitute for
  disconnecting.
- Your DMM must be **CAT II (or III) 600 V** rated. That is a rating on the instrument, not a
  range setting.
- The board switches the **hot** leg only and the neutral runs straight through (A2/A3 prove it).
- `Q1` has an insulated tab — it bolts to a heatsink with no insulating washer. In a sealed case,
  ambient derating is the limit on continuous current.
- 2.4 GHz needs a non-metallic window if the enclosure is metal.
