# DigiKey order — resolved part numbers

Verified against DigiKey CA on 2026-11-06 in two passes: each line read from the
product page's own data (DigiKey part number, manufacturer, unit price, "In-Stock: N"),
then **all 13 lines built into a live cart and read back out of it** — cart subtotal
**$70.26 CAD**. Quantities are **for 3 boards** — per-board counts times three, which
is where this list differs from "3 of everything".

| qty | DigiKey # | MPN | brand | unit | stock | BOM ref |
| --- | --- | --- | --- | --- | --- | --- |
| 3 | `497-BTA16-600SWRG-ND` | BTA16-600SWRG | ST | $3.18 | 1,982 | `Q1` triac |
| 3 | `MOC3063M-ND` | MOC3063M | onsemi | $1.99 | 8,958 | `U2` zero-cross opto |
| 6 | `36-3512P-ND` | 3512P | Keystone | $0.82 | 617 | `F1` fuse clip (2/board) |
| 3 | `5923-5ST3.15-R-ND` | 5ST 3.15-R | Bel Fuse | $1.08 | — | `F1` fuse element, 3.15 A 5×20 time-lag |
| 3 | `495-6591-1-ND` | B72214S0151K551 | TDK | $0.95 | 3,410 | `MOV1` S14K150, 14 mm disc |
| 3 | `1801-1N5819CT-ND` | 1N5819 | Taiwan Semi | $0.48 | 12,295 | `D5` DO-41 Schottky |
| 3 | `493-1043-ND` | UVR1C471MPD | Nichicon | $0.59 | — | `C1` 470 µF 16 V radial |
| 3 | `BC5229CT-ND` | K104K15X7RF5UH5 | Vishay | $0.43 | 13,123 | `C2` 100 nF 50 V X7R radial |
| 3 | `150XBK-ND` | MFR-25FBF52-150R | Yageo | $0.15 | 34,826 | `R3` 150 Ω ¼ W axial |
| 3 | `360QBK-ND` | CFR-25JB-52-360R | Yageo | $0.16 | 5,811 | `R4` 360 Ω ¼ W axial |
| 6 | `S7040-ND` | PPPC071LFBN-RC | Sullins | $0.82 | — | `J1`,`J2` 1×07 2.54 mm socket (2/board) |
| 6 | `277-1236-ND` | 1729018 | Phoenix | $1.41 | — | `J3`,`J4` MKDS 1,5/2-5,08 terminal (2/board) |
| 3 | `1597-113991054-ND` | 113991054 | Seeed | $8.31 | — | XIAO ESP32C3 |

Blank price/stock cells are the part numbers whose DigiKey page was not read; their
DigiKey numbers and unit prices above come from the cart, which is authoritative for
both. The MPN is the number to search; the DigiKey `-ND` number is what the cart shows
back, and it is **not always the number a search result uses** (`MFR-25FBF52-150R` →
`150XBK-ND`, `1729018` → `277-1236-ND`, `5ST 3.15-R` → `5923-5ST3.15-R-ND`).

**Not in this order:** `PS1` HLK-PM01 5 V 3 W — AliExpress, per the BOM.

## Corrections found in the second pass (2026-11-06)

1. **`R4` was a number the cart rejects.** The first pass had `CFR-25JT-52-360R`; Manual
   Entry will not resolve it. The sibling of the `R3` line that does resolve is
   **`CFR-25JB-52-360R` → `360QBK-ND`** (In-Stock: 5,811, $0.16).
2. **`R3` was on backorder.** `CFR-25JB-52-150R` (`150QBK-ND`) reads **Backorder** at
   DigiKey CA, and a backordered line holds the whole order. Replaced with the stocked
   metal film **`MFR-25FBF52-150R` → `150XBK-ND`** (34,826, $0.15): same ¼ W axial
   footprint, 1% instead of 5%, and minted. Swap back if carbon film is required.
3. **`Q1` part number in BOM.md is wrong.** BOM.md says `497-3389-5-ND` (page 669146);
   the live part number is **`497-BTA16-600SWRG-ND`**. The MPN `BTA16-600SWRG` is the
   durable identifier — search that, not the remembered `-ND`.
4. **`D5` value is `SS14` (SMD) against a `D_DO-41` through-hole footprint.** The
   ordered `1N5819` is the DO-41 part the footprint is drawn for; the BOM's own value
   disagrees with its own footprint. Order the through-hole part rather than change the
   board.

## The opto, decided

The BOM's first choices were both **out of stock at DigiKey CA** on the day of the
order: Lite-On `MOC3063M` (page 4307927) In-Stock: 0 / backorder only, and Everlight
`EL3063` In-Stock: 0 with backorders refused. The in-stock options were
`MOC3063M-ND` (onsemi, 8,958) and `VO3063-X006` (Vishay, 171, $2.58).

**Harri chose `MOC3063M-ND` (onsemi)**. It is a US brand (Malaysian assembly), against
the general non-US-origin preference, but it is the same function at a third of the
Vishay price and genuinely stocked — the origin rule is a tiebreaker, not an absolute.

Both are zero-cross; a random-phase part (`MOC3021M`, `VO3023`) is **not** a
substitute on this board — it drops into the same DIP-6 footprint and the board is
wrong.

## Why the list is in the repo instead of left in a cart

The cart was built and read back, but it is **not** handover-able: DigiKey's cart is
session-cookie scoped, and the Hermes cloud browser is killed by the provider's **hard
5-minute session lifetime** (not configurable — `browser_use` provider, managed mode).
A cart built in one window is empty in the next, logged in or not — measured, 12 lines
then `0 item(s)` after re-login. So either the whole fill → readback → checkout happens
inside one window, or the order is driven through a local Chromium (`/browser connect`),
which has no such cap. Procedure detail lives in the `electronic-parts-sourcing` skill.
