# Authoritative costing report

Use this section order: **Cost roll-up**, Part 1, further genuine parts if any, then Assembly. The roll-up gives a quick answer; the later tables show the calculation. A manufactured part or bought-complete component gets a numbered Part section. Loose hardware belongs to the stage that installs it, even if the drawing gives it a separate BOM item number. Give each detailed Part and Assembly exactly **one contiguous Markdown table** as its visible boundary. Use the **same five columns and one header row** throughout that table: Item, Setup, Output / quantity, Rate / unit price, Cost/part or Cost/assembly. Group rows display only bold **PROCESS** or **MATERIAL & HARDWARE** in the first column, with the other cells empty; the table row boundary supplies a line under each label. Do not introduce a second header with new column meanings halfway through. Process throughput goes in column 3 and hourly rate in column 4; sheet yield/hardware quantity goes in column 3 and $/sheet or $/pc in column 4. The final row of each Part table is a bold **TOTAL** label without repeating the Part number, and a bold value right aligned in the fifth cost column. For an Assembly with unpriced required costs, use **KNOWN-COST TOTAL** instead of implying a complete manufacturing total. Always present the complete report as Markdown tables directly in chat; never substitute an image, PDF or file. Markdown tables do not reliably support enlarged or text-underlined cells across chat clients, so use the table's horizontal row boundaries and bold group/total rows instead of inline HTML tags. Only supply an additional formatted file if the user explicitly asks for one. Use a Markdown horizontal rule (`---`) between adjacent sections. Never leave a total as left-aligned prose or add a cost twice.

Lead with drawing/revision, batch quantity and AUD excluding GST. Use the tables below, omitting inapplicable rows. Distinguish per physical part from per completed assembly; keep installed child hardware within its owning stage. Process routes display forward operation order (OP10, OP20, OP30). Setups are included in process costs.

## Cost roll-up — read this first

Use a compact three-column table before any process detail. Show one row for each completed Part, one row for the direct Assembly addition, and separate rows for unresolved cost, known-cost subtotal, margin and provisional selling price. The explanatory middle column may show short arithmetic, but do not repeat every operation. For multiple parts, show one row per genuine part, each multiplied by its assembly quantity. The Assembly addition excludes completed Part costs. Sum only completed Part contributions plus Assembly addition to get the known-cost subtotal; the displayed Part and Assembly detail farther down is evidence, not another charge.

| Cost level | What is included | AUD/assembly |
|---|---|---:|
| Part 1 — support bracket | Process $… + sheet $… + installed studs $… | $… |
| Assembly addition | Weld/mark $… + weld nuts $… | $… |
| E-coat | Supplier charge pending | Unpriced |
| **Known-cost subtotal** | Part 1 + Assembly addition | **$…** |
| Nominal pricing margin, 28% | Based on known costs only | $… |
| **Provisional selling price** | Excludes unpriced E-coat | **$…** |

Use unrounded calculator figures for each roll-up total; rounded subamounts might differ by $0.01. When all rows are priced, label the manufacturing cost and final selling price without provisional qualifiers. Do not turn this into a second long BOM table. Include a short source/assumption note below the detailed Assembly tables, not inside the roll-up.

---

## Part 1 — name / part number

State quantity per assembly, material grade/thickness and make/buy status.

| Item | Setup | Output / quantity | Rate / unit price | Cost/part |
|---|---:|---:|---:|---:|
| **PROCESS** | | | | |
| OP10 Laser | … h × … setups | … pcs/h | $…/h | $… |
| OP20 Bend | … h × … setups | … pcs/h | $…/h | $… |
| OP30 Install studs | … h × … setups | … pcs/h | $…/h | $… |
| **MATERIAL & HARDWARE** | | | | |
| HA250 sheet, thickness, sheet dimensions | — | … pcs/sheet | $…/sheet | $… |
| M6 clinch studs | — | 2 pcs/part | $…/pc | $… |
| **TOTAL** | | | | **$…** |

The Part 1 TOTAL includes its process, raw material and owned hardware rows once. A bought-complete part has no invented process rows; show its purchase in the Material group. Repeat this structure for Part 2 only when a further actual part exists. For nested subassemblies, show genuine children before the parent and roll each child into its immediate parent once.

---

## Assembly — name / part number

| Item | Setup | Output / quantity | Rate / unit price | Cost/assembly |
|---|---:|---:|---:|---:|
| **PROCESS** | | | | |
| OP10 Weld seven nuts | … h × … setups | … assemblies/h | $…/h | $… |
| OP20 E-coat — supplier finish | — | — | — | $… or Unpriced |
| OP30 Drawing-required marking, if separate | … h × … setups | … assemblies/h | $…/h | $… |
| **COMPLETED PARTS & HARDWARE** | | | | |
| Part 1 — name, including its hardware | — | … parts/assembly | $…/part | $… |
| Part 2 — only if another real part exists | — | … parts/assembly | $…/part | $… |
| M6 weld nuts | — | 7 pcs/assembly | $…/pc | $… |
| Other assembly material — name, if applicable | — | … units/assembly | $…/unit | $… |
| **TOTAL** or **KNOWN-COST TOTAL** when items remain unpriced | | | | **$…** |
| Pricing margin dollars at 28% | | | | $… |
| **Final selling price** or **Provisional selling price, excluding unpriced items** | | | | **$…** |

---

Follow with one short line: Batch of Q — cost $…; nominal margin dollars $…; selling value $…. When the batch quantity is the provisional default, add one line: Per-assembly cost at 50 / 100 / 500 — $… / $… / $…. Use unrounded calculations for totals. Round displayed money to two decimals normally; show more precision only when needed to explain quantity multiplication. Selling price = cost/(1-margin), not cost×(1+margin); do not add a margin to child parts before rolling them into Assembly. For cost-only requests omit the margin and selling rows.

Margin: default to `rates.json` `default_gross_margin` (28%) unless the user specifies another margin or asks for cost only; set it through the calculator `gross_margin`.

Routine inspection and packing (deliberate user preference, stated only here): default to at least 120 finished assemblies/h (30 s maximum combined) on the B54 `manual` resource unless measured data or a special requirement warrants another rate. Enter it as a root process row with `absorbed_in_margin: true`; it is commercially absorbed within margin, not a manufacturing-cost row, and not shown in the Assembly table. Below the Assembly totals, state its labour equivalent from `absorbed_per_assembly` and the `effective_margin`. The displayed 28% is a pricing margin on the costed route, **not realised gross margin**: show dollars remaining after absorption and the effective percentage of selling price. This disclosure is what keeps real work from being silently treated as free. Drawing-required marking remains a separately costed process unless its time is demonstrated within another cycle. Cost special inspection, packaging materials, dedicated stations or outsourced services explicitly and retain true gross-margin accounting.

## Summary mode

For `/costing summary`: lead line (part/job, batch quantity, AUD ex GST), then one table with a row per Part showing its main contributors in short arithmetic (e.g. laser 2.94, bend 5.18, deburr 0.72, sheet 3.79), a row per bought hardware line, one Assembly addition row, bold **Cost** and bold **Selling price** (margin %) rows. Below it, at most four bullets: comparison with the previous batch/estimate if one exists, procurement (whole sheets and supplier MOQ outlay, combining parts that share one sheet spec), unpriced items, and the effective margin after absorbed inspection/packing. No per-Part tables. The totals must equal the full-report totals.

## Accounting and presentation checks

- Show setup, finished pcs/h and hourly rate on each priced process row. A supplier finish with a per-unit price has no internal machine rate; show its unit charge in the process cost cell and explain its supplier basis. Show "Unpriced" for unresolved costs, never zero.
- Show sheet grade, thickness, sheet dimensions, $/sheet, parts/sheet and calculated $/part on the raw material row. A sheet yield is an envelope estimate unless a true nest is available. Show hardware price **per piece**, quantity and extended cost. Do not show the sum of hardware as a fake unit price.
- Keep studs installed on a bracket within that bracket. Keep weld nuts installed during assembly in Assembly material beside the assembly weld process. The calculator may model hardware SKUs as buy children, but these do not become standalone numbered Part sections. Never duplicate hardware already rolled into a displayed part.
- Sum root-owned process/material costs plus immediate child rolled costs once. Do not sum every nested rolled total. Check every displayed part total against calculator BOM output and the Assembly subtotal against calculator per_assembly.
- Explain supplier minimum/batch fee allocations and any shared setup/co-nest costs briefly. Do not add setup a second time. Keep one-off tooling and whole-sheet/MOQ procurement outlay separate from recurring unit cost.
- When recurring costs remain unpriced, label margin and selling price provisional and based on known costs only. End with concise material/cycle assumptions, scrap/rework treatment, exclusions and unresolved supplier costs.

For a revised estimate, add:

| Changed item | Previous basis | Revised basis and reason | Cost change/assembly |
|---|---|---|---:|

Reconcile all row deltas to the manufacturing-cost change. Show margin change and selling-price change separately; do not call a selling-price difference a manufacturing-cost difference. Include setup and supplier-minimum effects. Keep added, removed, newly priced and newly unpriced rows visible. Compare one-offs separately. Never overwrite an assumption merely to match a target price.
