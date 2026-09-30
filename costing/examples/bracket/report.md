Illustrative report for `input.json` (fictional drawing EX-001 Rev A). Figures are the calculator output; regenerate this file if the input or rates change.

EX-001 Rev A · batch 100 assemblies (provisional default) · AUD excluding GST

## Cost roll-up — read this first

| Cost level | What is included | AUD/assembly |
|---|---|---:|
| Part 1 — EX-001-01 Bracket | Process $4.17 + sheet $1.33 + installed studs $0.36 | $5.86 |
| Assembly addition | Weld $5.65 + packing $0.53 + weld nuts $0.48 + dispatch $0.90 | $7.57 |
| E-coat | Supplier charge pending | Unpriced |
| **Known-cost subtotal** | Part 1 + Assembly addition | **$13.43** |
| Nominal pricing margin, 28% | Based on known costs only | $5.22 |
| **Provisional selling price** | Excludes unpriced E-coat | **$18.65** |

---

## Part 1 — EX-001-01 Bracket

1 per assembly · HA250 2.0 mm · make

| Item | Setup | Output / quantity | Rate / unit price | Cost/part |
|---|---:|---:|---:|---:|
| **PROCESS** | | | | |
| OP10 Laser program | 0.25 h × 1 | 200 pcs/h | $210.97/h | $1.58 |
| Laser sheet load/unload | — | 2 sheets/batch, 10 min/sheet | $210.97/h | $0.70 |
| OP20 Bend | 0.25 h × 1 | 180 pcs/h | $149.81/h | $1.21 |
| OP30 Install studs | 0.10 h × 1 | 180 pcs/h | $103.22/h | $0.68 |
| **MATERIAL & HARDWARE** | | | | |
| HA250 2.0 mm, 2440 × 1220 | — | 54 pcs/sheet | $72.00/sheet | $1.33 |
| M6 clinch studs | — | 2 pcs/part | $0.18/pc | $0.36 |
| **TOTAL** | | | | **$5.86** |

---

## Assembly — EX-001 Mounting bracket assembly

| Item | Setup | Output / quantity | Rate / unit price | Cost/assembly |
|---|---:|---:|---:|---:|
| **PROCESS** | | | | |
| OP10 Weld four nuts | 0.25 h × 1 | 20 assemblies/h | $107.68/h | $5.65 |
| OP20 E-coat — supplier finish | — | — | — | Unpriced |
| OP30 Manual packing | 0.10 h × 1 | 240 assemblies/h | $103.22/h | $0.53 |
| Pallet | — | 1/batch | $30.00/batch | $0.30 |
| Freight | — | 1/batch | $60.00/batch | $0.60 |
| **MATERIAL & HARDWARE** | | | | |
| Part 1 — EX-001-01 Bracket, including studs | — | 1 part/assembly | $5.86/part | $5.86 |
| M6 weld nuts | — | 4 pcs/assembly | $0.12/pc | $0.48 |
| **KNOWN-COST TOTAL** | | | | **$13.43** |
| Pricing margin dollars at 28% | | | | $5.22 |
| **Provisional selling price, excluding unpriced items** | | | | **$18.65** |

---

Batch of 100 — known cost $1,342.88; nominal margin dollars $522.23; provisional selling value $1,865.11.
Per-assembly cost at 50 / 100 / 500 — $15.71 / $13.43 / $11.61; sheet handling and dispatch recalculated for each batch.
Weld scenario (42% of known cost, fallback cycle): low 30/h $11.63 · base 20/h $13.43 · high-cost 15/h $15.22 known cost/assembly; provisional selling $16.16 / $18.65 / $21.14.

Routine inspection (240 assemblies/h, B54 $103.22/h) is absorbed in margin: labour equivalent $0.43/assembly, leaving $4.79 (effective margin 25.7% of the provisional selling price). Packing is priced separately.

Material: **Estimated from IXL baseline** — HA3PO 2.0 mm (IXL-Steel-Price-Sept26.xlsx, Production Material IXL row 7, BIXL 703400) used as a pricing proxy for the specified HA250; unit/GST basis assumed pending confirmation. Yield 54/sheet is an envelope estimate (180 × 240 flat), not a nest. MOQ 20 sheets would be a procurement outlay, not charged here. Laser program throughput is a provisional fallback of 200 parts/h; handling assumes two sheets at 10 minutes total each. Gas/technology and removal method need confirmation; the 200 parts/h figure is specific to this example. Hardware prices are illustrative. No scrap allowance; e-coat unpriced. Cartons excluded. Pallet and freight are budget defaults.

Inputs most likely to change this: batch size, weld cycle (42% of known cost), laser program and nest yield, e-coat quote.
