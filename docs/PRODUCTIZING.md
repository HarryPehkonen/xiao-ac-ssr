# From board to "finished product" — what approval actually requires

The enclosure is a weekend. The **approval** is the project. This file records what the rules
are, so the question does not have to be re-researched later. It is engineering guidance, not
legal advice; the certification body or the electrical authority has the last word.

## The rule that decides the plan

Canadian Electrical Code **Rule 2-024**: equipment used in an electrical installation must be
*approved*, and "approved" means **certified by an SCC-accredited certification body** or
**field evaluated by an SCC-accredited inspection body**. Alberta's safety-codes bulletin is
blunter: *no person shall **manufacture**, install, sell or offer for sale any equipment related
to electrical systems for use in Alberta unless it has been certified by a certification body,
or inspected by an inspection body.*

And the clause that kills the obvious shortcut — Ontario's Rule 2-022(5), which is the same
principle wherever it is written down:

> If assembled electrical equipment consists of or incorporates approved component(s), the
> electrical equipment shall not be deemed to be approved unless the whole electrical equipment
> as assembled is approved.

So **a certified SSR inside a certified enclosure, wired by you, is not an approved product.**
Individual listed components remove the "unapproved component" problem; they do not approve the
assembly.

## Three routes, and what each costs

1. **Field evaluation — CSA SPE-1000.** The Model Code for the field evaluation of electrical
   equipment. An SCC-accredited inspection body (Intertek, CSA, UL, ESA, LabTest, QPS, TÜV …)
   inspects the unit, evaluates it against SPE-1000, and applies a serialized label plus a report
   that the electrical authority accepts. Built for custom/one-off/limited-run equipment, done
   on site or in a lab, much faster than certification. The economic catch, in one provider's own
   words: **a field evaluation is priced per unit, every unit, every time.** Right answer for a
   handful of units; wrong answer for a product line.
2. **Certification — the real product route.** Test samples, safety + EMC (+ radio if not a
   certified module), a listing mark, and an ongoing factory follow-up service. Months, not
   weeks, and order-of-magnitude five figures for the first model before tooling — quotes vary
   and are free, so get two or three. This is the only route that scales.
3. **Do not build the mains device at all.** Buy the certified thing: a listed smart
   plug/relay module driven over the network, or a listed chassis SSR/contactor, and let the
   interesting part (the control logic) live in low voltage. Zero certification burden for
   personal use, and it becomes a product decision only if the *combination* is sold.

### Route 3 in practice — and the load ceiling that comes with it

The whole mains side becomes one purchase: a **listed** (look for cUL/cULus/CSA/ETL on a
Canadian purchase) 15 A smart plug with a **local** control path and **metering**. Confirmed
candidates: TP-Link **Kasa KP115** (UL, 15 A / 1800 W, energy monitoring, local protocol — no
cloud needed, and it keeps working with the internet blocked) and Shelly's **UL-marked** line
(Plus 1PM UL / 1PM Gen4 UL, ~$26–27 USD; their local API, MQTT and on-device scripting suit
custom logic better). Roughly **$25–45 CAD**, and the controller on the other side needs no
approval at all if it runs from a listed Class 2/LPS supply — that exemption sits next to the
approval rule.

**The ceiling is the heater, and it is not the plug's fault.** "15 A" is a peak number: the
wiring rules derate continuous loads to 80 %, i.e. **12 A / 1440 W**, and a 1500 W heater draws
**12.5 A for hours**. This is the canonical "do not put a space heater on an adapter" case —
many heater manuals forbid adapters outright, and electrician-facing guidance says plug heaters
straight into the wall. Under ~1200 W a listed metering plug is routine; at 1500 W the honest
answer is a heater with its own thermostat and timer, plugged straight in.

**Metering is the upgrade over this board.** The plug reports actual power, so the control logic
can tell "commanded off" from "actually off" — the one failure mode a fuse cannot see.

**Confirmed model, and the cloud-free path.** The one Shelly that is both UL-marked and a *plug*
is the **Shelly Plug US Gen4** ($21.24 USD on Shelly's US store at the time of writing, reg
$24.99; 2-pack $44.99). NEMA 5-15 in and out, 15 A, "max output power 1800 W (**resistive load
only**)", duty type S1, 10 000 switching cycles, and it meters volts, amps, watts, energy and its
own internal temperature. Wi-Fi + BLE + Zigbee, ESP-Shelly-C68F, with on-device scripting, MQTT,
webhooks and a documented local RPC API (HTTP/WebSocket).

Cloud is optional and switchable at the device rather than tied to an account: the unit boots
into its own access point, you browse **192.168.33.1**, join it to the network, and **decline the
cloud prompt** — then in its web UI, *Settings → Cloud: off* (the default is **on**, so this is the
step not to miss) and Bluetooth off with it. Everything afterwards is LAN: local RPC, MQTT, UDP,
webhooks, on-device schedules. For a guarantee rather than a promise, put it on an IoT VLAN with
no internet route — and accept the trade: no firmware updates and no time sync, so keep the
scheduling logic on your side.

For a Canadian purchase, check the mark carries the **"c"** (cUL/cULus) or is CSA/ETL. A US-only
UL mark is not Canadian approval. The other UL-marked Shellies (Plus 1PM, 1PM Gen4 UL,
Pro 1/1PM/2PM, the wall dimmers, the input-only i4) are *installed components* — behind a switch,
in a DIN panel, or in a wall — so they put the assembly back in your hands and are not
plug-and-play.

## The standards the box would have to be "approved for"

Which one applies is the certification body's first call, because it follows from what the thing
*is*:

| what you built | standard |
| --- | --- |
| a plug-in device with a switched **outlet** on it | **UL 498B** *Receptacles with Integral Switching Means* (the receptacle itself: UL 498) |
| a **solid-state control** that switches an appliance's power (a zero-cross triac on a heater) | **UL 244A** *Solid-State Controls for Appliances*; **UL/CSA/IEC 60730-1** *Automatic Electrical Controls* — 60730-1 explicitly covers smart-enabled controls |
| smart-device electronics / a power supply inside | **UL 62368-1** (AV/ICT safety; it replaced 60950-1) |
| a **control panel** rather than a cord-connected appliance | **UL 508A / CSA C22.2 No. 286** *Industrial Control Panels* |
| the cord | **UL 817** cord sets — use a moulded one |
| the radio | **FCC Part 15.247** and **ISED RSS-247/RSS-Gen** (RSS-102 for exposure) |

## The XIAO is the wrong building block for a certified product

Two independent reasons, both avoidable by moving to a certified module on this project's own PCB
— which also removes the socketed dev-board assembly and the 15.24 mm seating question:

1. **Radio.** The XIAO ESP32C3 is *chip-down*: a bare ESP32-C3 plus its own PCB antenna, so it
   carries **no modular approval** and the finished product needs its own FCC/ISED authorization.
   The module that would confer one is the **ESP32-C3-MINI-1**: FCC ID `2AC7Z-ESPC3MINI1`,
   IC `21098-ESPC3MINI1`, **Modular Approval (MA)**, RSS-247 Issue 3. With it the product may be
   labelled *"Contains FCC ID: 2AC7Z-ESPC3MINI1"* — provided the module's own conditions are met
   (antenna unchanged, no co-location, the grant's RF-exposure separation, host compliance for
   everything the grant does not cover).
2. **Component status.** A dev board is not a UL-recognized component; a certification body
   evaluates it as an unlisted component inside the assembly. A production design should not be
   built on one.

## Build list for a credible finished unit

- Moulded **cord set** (UL 817) entering through a **strain relief / cord grip** that passes a
  pull test — not a hole with a knot.
- **Tool-required closure**, no accessible live parts, and the 3 mm isolation barrier maintained
  to the enclosure, not just between tracks.
- Output either a **listed receptacle** (UL 498B territory) or a captive moulded cord — the
  captive cord is simpler and dodges the switched-receptacle rules.
- **A mechanical disconnect in the cord.** This is DESIGN.md's own rule — a triac fails **short**
  — and for a product it is the difference between a fault and a fire.
- **Thermal rise test** on the closed enclosure with the worst-case load; `C1` (105 °C) and the
  module (85 °C) set the ceiling, and the enclosure sets the ambient.
- **Markings**: model, ratings, certification mark, radio IDs, "no user-serviceable parts".

## The heater hazard a fuse cannot cover

If a 1500 W heater is the load, the failure to design against is a **short-circuited SSR**. The
load current is normal, so the fuse does nothing; the heater simply stays on with the controller
believing it is off. Mitigations are a thermal cutout at the load, a series mechanical device, or
current monitoring that can tell "commanded off" from "actually off". The fuse protects the board.
It does not protect anyone from a shorted triac feeding a heater.
