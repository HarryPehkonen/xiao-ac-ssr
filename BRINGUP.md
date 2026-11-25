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
| 4 | 4 | `495-1411-ND` | B72214S0151K101 | Varistor S14K150 (EPCOS/TDK), 14 mm disc, **straight leads, bulk**. Do NOT substitute the `K551` number: TDK's taping/packaging document lists it as `S14K150G5S5` — **crimped leads, style S5, taping mode G5** (hence DigiKey's cut-tape `-1-ND` suffix) — while `K101` is the bulk straight-lead part the electrical tables tabulate and the one the footprint was checked against. If `K551` parts are already on hand, compare the leads to Figure 1 (straight) versus Figure 4 (S5, crimped) before soldering. **As delivered, 2026-11-23: the order shipped `K551`** — DigiKey line 4 of the delivered order reads `495-6591-1-ND` / `B72214S0151K551`, i.e. the variant this row warns against; the `K101` swap was recorded here *after* the order was placed. So the four discs on hand are the crimped-lead ones: measure before soldering, and if the crimp fights the staggered holes, `495-1411-ND` ×4 is the straight-lead part. |
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

### `MOV1` — the staggered pads are CORRECT (do not "fix" them)

KiCad's `Varistor.pretty/RV_Disc_D12mm_W4.5mm_P7.5mm` places pad 2 at `(7.5, 1.8)`, i.e. the two holes are
7.71 mm apart on a diagonal rather than in one line. **That is the real part.** The datasheet's side view
(TDK/EPCOS SIOV StandarD series §3.2; outline `VAR0586-W-E`) shows the two leads offset **along the thickness
axis** — one at the front face, one at the back — straight and of equal length. The offset scales with the
body: ≈ (thickness − lead ⌀)/2, so (4.5 − 0.8)/2 = 1.85 mm against KiCad's 1.80.

An earlier revision of this document called this a defect and straightened the pads; that was wrong and it
was reverted. Straightening would have required bending a lead on a part that seats as designed, and it made
DRC report `lib_footprint_mismatch` — which is precisely the check that catches a footprint drifting from an
unmodified library part. **Treat that warning as guilty until proven.**

Note the ordering-code trap: digit 13 = 1 means "standard, straight leads", i.e. *uncrimped* — **not**
coplanar. A crimped/trimmed variant (digit 13 ≠ 1) is a different lead geometry.

---

## A. Dead board — no power, no USB. Catches most assembly faults

| # | Measurement | Expected | Measured |
|---|---|---|---|
| A0 | **Is it the right board?** `J1`→`J2` socket row spacing, centre to centre | **15.24 mm**, and 4 × 3.2 mm non-plated M3 holes, outline 150 × 45 mm. **≈6.1 mm means the fab built the pre-fix board** (before `b6e90ee`) and the XIAO cannot seat. | |
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

**Two axes, not one.** *Framework* is ESP-IDF (vendor-supported; every Espressif API page assumes
it) or Arduino-ESP32 (`digitalWrite`, `WiFi.h`, `esp_now.h` — far less ceremony). *Build system* is
what puts a binary on the board: PlatformIO (versions pinned per project in `platformio.ini`,
CLI-first and headless — `pio run`, `pio run -t upload`, `pio device monitor`, `pio test`) or the
Arduino IDE's GUI. PlatformIO drives either framework, so the two compose: `framework = arduino`
for speed now, `framework = espidf` later in the same project shape.
Flashing happens over USB-C with **mains disconnected**; the XIAO's USB and the HLK's 5 V are
isolated from each other by `D5` on this board, but do not test that distinction with mains live.

### Fail-safe defaults — decide these before writing the firmware

| condition | behaviour | why |
| --- | --- | --- |
| power-up / reset / brownout | **load OFF** — GPIO3 driven low before any radio init | a switch that boots "on" energises the load every time the mains blips |
| control link lost (no packet for N s) | **hold the last commanded state** | the load may be something that must not change state unannounced, and the triac gives no feedback either way |
| firmware hang | hardware watchdog reset → boots off again (row 1) | a hung loop must not be able to leave the load latched on and the link silent |
| the user wants it *actually* off | **the cord switch** | a triac fails short; no firmware can promise "off" |

Verify row 1 as part of section B, with the meter across `R3`: after a reset the LED current must
read ~0 mA (B2) and only rise to ~12 mA once the firmware commands it on. That measurement *is*
the boot state — it is not something to assume from the source.

## F. Safety

- First mains test on a **GFCI outlet**; never work on it live; the case is not a substitute for
  disconnecting.
- Your DMM must be **CAT II (or III) 600 V** rated. That is a rating on the instrument, not a
  range setting.
- The board switches the **hot** leg only and the neutral runs straight through (A2/A3 prove it).
- `Q1` has an insulated tab — it bolts to a heatsink with no insulating washer. In a sealed case,
  ambient derating is the limit on continuous current.
- 2.4 GHz needs a non-metallic window if the enclosure is metal.
