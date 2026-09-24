Illustrative report for `input.json` (fictional drawing EX-001 Rev A). Figures are the calculator output; regenerate this file if the input or rates change.

EX-001 Rev A · batch 100 assemblies (provisional default) · AUD excluding GST

## Cost roll-up — read this first

| Cost level | What is included | AUD/assembly |
|---|---|---:|
| Part 1 — EX-001-01 Bracket | Process $4.13 + sheet $1.33 + installed studs $0.36 | $5.82 |
| Assembly addition | Weld $5.65 + weld nuts $0.48 | $6.13 |
| E-coat | Supplier charge pending | Unpriced |
| **Known-cost subtotal** | Part 1 + Assembly addition | **$11.96** |
| Nominal pricing margin, 28% | Based on known costs only | $4.65 |
| **Provisional selling price** | Excludes unpriced E-coat | **$16.61** |

---

## Part 1 — EX-001-01 Bracket

1 per assembly · HA250 2.0 mm · make

| Item | Setup | Output / quantity | Rate / unit price | Cost/part |
|---|---:|---:|---:|---:|
| **PROCESS** | | | | |
| OP10 Laser | 0.25 h × 1 | 200 pcs/h | $210.97/h | $1.58 |
| OP20 Bend | 0.25 h × 1 | 100 pcs/h | $149.81/h | $1.87 |
| OP30 Install studs | 0.10 h × 1 | 180 pcs/h | $103.22/h | $0.68 |
| **MATERIAL & HARDWARE** | | | | |
| HA250 2.0 mm, 2440 × 1220 | — | 54 pcs/sheet | $72.00/sheet | $1.33 |
| M6 clinch studs | — | 2 pcs/part | $0.18/pc | $0.36 |
| **TOTAL** | | | | **$5.82** |

---

## Assembly — EX-001 Mounting bracket assembly

| Item | Setup | Output / quantity | Rate / unit price | Cost/assembly |
|---|---:|---:|---:|---:|
| **PROCESS** | | | | |
| OP10 Weld four nuts | 0.25 h × 1 | 20 assemblies/h | $107.68/h | $5.65 |
| OP20 E-coat — supplier finish | — | — | — | Unpriced |
| **COMPLETED PARTS & HARDWARE** | | | | |
| Part 1 — EX-001-01 Bracket, including studs | — | 1 part/assembly | $5.82/part | $5.82 |
| M6 weld nuts | — | 4 pcs/assembly | $0.12/pc | $0.48 |
| **KNOWN-COST TOTAL** | | | | **$11.96** |
| Pricing margin dollars at 28% | | | | $4.65 |
| **Provisional selling price, excluding unpriced items** | | | | **$16.61** |

---

Batch of 100 — known cost $1,195.81; nominal margin dollars $465.04; provisional selling value $1,660.85.
Per-assembly cost at 50 / 100 / 500 — $13.23 / $11.96 / $10.94.
Weld scenario (47% of known cost, fallback cycle): low 30/h $10.16 · base 20/h $11.96 · high-cost 15/h $13.75 known cost/assembly; provisional selling $14.12 / $16.61 / $19.10.

Routine inspection and packing (120 assemblies/h, B54 $103.22/h) is absorbed in margin: labour equivalent $0.86/assembly, leaving $3.79 (effective margin 22.8% of the provisional selling price).

Material: **Estimated from IXL baseline** — HA3PO 2.0 mm (IXL-Steel-Price-Sept26.xlsx, Production Material IXL row 7, BIXL 703400) used as a pricing proxy for the specified HA250; unit/GST basis assumed pending confirmation. Yield 54/sheet is an envelope estimate (180 × 240 flat), not a nest. MOQ 20 sheets would be a procurement outlay, not charged here. Cycle times are provisional fallbacks. Hardware prices are illustrative. No scrap allowance; e-coat unpriced.

Inputs most likely to change this: batch size, weld cycle (47% of known cost), e-coat quote, nest yield.
