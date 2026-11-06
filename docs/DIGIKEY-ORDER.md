# DigiKey order — resolved part numbers

Verified against DigiKey CA product pages on 2026-11-06 (each line read from the
page's own data: DigiKey part number, manufacturer, unit price, "In-Stock: N").
Quantities are **for 3 boards** — per-board counts times three, which is where
this list differs from "3 of everything".

| qty | DigiKey # | MPN | brand | unit | stock | BOM ref |
| --- | --- | --- | --- | --- | --- | --- |
| 3 | `497-BTA16-600SWRG-ND` | BTA16-600SWRG | ST | $3.18 | 1,982 | `Q1` triac |
| 3 | `MOC3063M-ND` | MOC3063M | onsemi | $1.99 | 8,958 | `U2` zero-cross opto |
| 6 | `36-3512P-ND` | 3512P | Keystone | $0.82 | 617 | `F1` fuse clip (2/board) |
| 3 | `5ST 3.15-R` | 5ST 3.15-R | Bel Fuse | $1.08 | — | `F1` fuse element, 3.15 A 5×20 time-lag |
| 3 | `495-6591-1-ND` | B72214S0151K551 | TDK | $0.95 | 3,410 | `MOV1` S14K150, 14 mm disc |
| 3 | `1801-1N5819CT-ND` | 1N5819 | Taiwan Semi | $0.48 | 12,295 | `D5` DO-41 Schottky |
| 3 | `UVR1C471MPD` | UVR1C471MPD | Nichicon | — | — | `C1` 470 µF 16 V radial |
| 3 | `BC5229CT-ND` | K104K15X7RF5UH5 | Vishay | $0.43 | 13,123 | `C2` 100 nF 50 V X7R radial |
| 3 | `CFR-25JB-52-150R` | CFR-25JB-52-150R | Yageo | — | — | `R3` 150 Ω ¼ W axial |
| 3 | `CFR-25JT-52-360R` | CFR-25JT-52-360R | Yageo | — | — | `R4` 360 Ω ¼ W axial |
| 6 | `PPPC071LFBN-RC` | PPPC071LFBN-RC | Sullins | — | — | `J1`,`J2` 1×07 2.54 mm socket (2/board) |
| 6 | `1729018` | 1729018 | Phoenix | — | — | `J3`,`J4` MKDS 1,5/2-5,08 terminal (2/board) |
| 3 | `1597-113991054-ND` | 113991054 | Seeed | $8.31 | — | XIAO ESP32C3 |

Blank price/stock cells were resolved by part number (Manual Entry) rather than
read off a product page; they are real numbers, not unknown part numbers.

**Not in this order:** `PS1` HLK-PM01 5 V 3 W — AliExpress, per the BOM.

## Two corrections to BOM.md

1. **`Q1` part number is wrong there.** BOM.md says `497-3389-5-ND` (page 669146);
   the live part number is **`497-BTA16-600SWRG-ND`**. The MPN `BTA16-600SWRG` is
   the durable identifier — search that, not the remembered `-ND`.
2. **`D5` value is `SS14` (SMD) against a `D_DO-41` through-hole footprint.** The
   ordered `1N5819` is the DO-41 part the footprint is drawn for; the BOM's own
   value disagrees with its own footprint. Order the through-hole part rather than
   change the board.

## The opto, decided

The BOM's first choices were both **out of stock at DigiKey CA** on the day of the
order: Lite-On `MOC3063M` (page 4307927) In-Stock: 0 / backorder only, and
Everlight `EL3063` In-Stock: 0 with backorders refused. The in-stock options were
`MOC3063M-ND` (onsemi, 8,958) and `VO3063-X006` (Vishay, 171, $2.58).

**Harri chose `MOC3063M-ND` (onsemi)** and already has it in his cart. It is a US
brand (Malaysian assembly), against the general non-US-origin preference, but it is
the same function at a third of the Vishay price and genuinely stocked — the origin
rule is a tiebreaker, not an absolute.

Both are zero-cross; a random-phase part (`MOC3021M`, `VO3023`) is **not** a
substitute on this board — it drops into the same DIP-6 footprint and the board is
wrong.
