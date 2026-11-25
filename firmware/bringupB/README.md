# firmware/bringupB — driving GATE_DRV for BRINGUP section B

A PlatformIO project whose only job is to **hold, flip or blink `GATE_DRV`**, so section B of
[`BRINGUP.md`](../../BRINGUP.md) can be measured with a multimeter instead of chased with a scope.
No libraries, no radio, no credentials.

```sh
cd firmware/bringupB
pio run -t upload          # mains disconnected, USB-C only
pio device monitor         # 115200; s = status, 1 = on, 0 = off, b = blink
```

Or just press the **BOOT** button: short presses cycle BLINK → HOLD_ON → HOLD_OFF. Holding the
state is the point — a static reading beats watching a 1 Hz square wave on a DMM.

## What it drives, and where to measure

`GATE_DRV` is the XIAO's **D1 = GPIO3**, on **`J1` pad 2**, through **`R3` (150 Ω)** into the
MOC3063's LED (`U2` pins 1–2).

| socket pad | module label | GPIO | net on this board |
| --- | --- | --- | --- |
| `J1.1` | D0 | GPIO2 | unused |
| **`J1.2`** | **D1** | **GPIO3** | **`GATE_DRV` → `R3` pad 1** |
| `J2.1` | 5V (VBUS) | — | `+5V_XIAO` |
| `J2.2` | GND | — | `GND` |
| everything else | — | — | unconnected |

`R3` is axial and rotated on the board, so its two pads are one above the other:

- **pad 1 — `GATE_DRV`, the GPIO end — is the lower pad**
- **pad 2 — `MOC_A`, the LED end — is the upper pad**

Put the **red probe on pad 1** and you read a positive voltage when GPIO3 is high.

## Expected readings

| state | across R3 | means |
| --- | --- | --- |
| HIGH | **~1.8–2.1 V** → 12–14 mA | (3.3 V − ~1.2 V LED) / 150 Ω. The MOC3063 needs ~5 mA to trigger, so there is ~2.5× margin |
| low | **~0 V** | no LED current |
| `U2` pin 1 → pin 2, HIGH | ~1.2 V | the LED itself conducting (BRINGUP B3) |

**A blank XIAO reads 0 V across R3 and that is not a fault.** With no application firmware,
GPIO3 is an unconfigured input — it drives nothing. B1 needs this sketch (or any sketch that
asserts the pin) before it can pass.

## Notes

- **There is no light to watch.** The XIAO ESP32C3 has no user LED — its only LED is the charge
  indicator, which is hardware, not firmware — so this project reports over serial and through the
  pin. "Blinking" here means `GATE_DRV` toggling at 1 Hz: one serial line per second, and across
  `R3` an alternation between ~1.8–2.1 V and ~0 V. Read it with `pio device monitor`, not `cat` —
  the monitor asserts DTR the way the board's USB-CDC expects, and a raw read gets throttled output.
- **No radio on purpose.** The ESP32's WiFi transmitter draws ~250 mA bursts in the same ground
  system as a 12 mA measurement, and it would put noise on every reading of `R3`. It is also why
  this project has no credentials: there is nothing to hard-code.
- **Fail-safe order.** `digitalWrite(PIN_GATE, LOW)` runs immediately after `pinMode`, before the
  console and before any delay, so a reset can never leave the load energised. The production
  firmware needs the same discipline plus a task watchdog (BRINGUP section E).
- **The 3.3 V rail is the XIAO's own** (`TLV75733P`, 500 mA), so section B runs on USB alone — no
  `PS1`, no mains, nothing to insulate.
- **Pin choice.** D1/GPIO3 has no strapping role and no on-board load, and the module's antenna is
  on a U.FL pigtail, so it is one of Seeed's "safe general" pins.
- **Reproducibility.** Built and verified on 2026-11-25 with **PlatformIO Core 6.2.0 / espressif32
  @ 8.0.0 / Arduino-ESP32 core 3.3.12** (RISC-V toolchain 14.2.0): `firmware.bin` 276,448 B,
  RAM 4.1%, flash 20.2%. `platform` is pinned to 8.0.0 in the ini so a machine in five years
  builds the same binary; bump it deliberately, not by accident.
