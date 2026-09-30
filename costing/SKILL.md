---
name: costing
description: Estimate sheet-metal fabrication cost from uploaded PDF drawings, drawing images or CAD, with per-component raw material, laser cutting, bending, setup hours, pieces per hour, welding, finishing and assembly totals. Use when a user drops a drawing for costing, requests a manufacturing estimate, wants process and material cost breakdowns, or asks to see the saved material list, laser cut technology list or hourly resource rates.
---

# Costing

Route saved-list requests through "Saved lists" below before starting an estimate. For costing requests, return an immediately useful internal budget estimate in chat. Do not require STEP or a questionnaire before starting from a readable drawing. AUD excluding GST by default. Label provisional assumptions prominently; never describe a budget estimate as a supplier quotation.

Each rule lives in one reference file:

| File | Owns |
|---|---|
| `references/estimating.md` | Input precedence, drawing reading, BOM and hardware ownership, batch quantity, yield, cycle times, scenarios, revisions |
| `references/material-pricing.md` | Material price decision order, IXL baseline, proxies, scaling, units/GST, age |
| `references/laser-timing.md` | Gas selection, technology-based timing, program calibration and per-sheet handling |
| `references/laser-technology.json` | Extracted S235 oxygen/nitrogen technologies and job-specific program references; no PDF |
| `references/rates.json` | Saved resource rates, default resources, fallback throughputs, margin, e-coat reference |
| `references/calculator-contract.md` | Calculator input schema and output fields |
| `references/report-format.md` | Chat report layout, margin/selling presentation, inspection/packing absorption |

## Saved lists

Recognise natural-language list requests automatically; do not require a special command, slash syntax, drawing, STEP, quantity or questionnaire. These are read-only lookups, separate from summary/breakdown/nest. Read the current saved files; do not rely on recalled values. Return Markdown tables directly in chat, without running a costing, changing estimate inputs, researching replacement prices or creating a file unless requested. Recognise equivalent wording and plural forms, such as "show", "list", "display", "material prices", "laser cutting technology" and "hourly rates". If multiple lists are requested, show each. Apply explicit material/thickness/gas/resource filters; otherwise show the complete relevant list without asking.

| Natural-language request | Read | Table output |
|---|---|---|
| "Show me material list" | `references/ixl-material-baseline.json` and unit/source notes in `references/material-pricing.md` | Separate sheet and coil tables. Columns: Material code, Material, Thickness mm, Sheet size or coil width mm, Listed MOQ, Listed price with assumed unit. Include all saved entries unless filtered. State supplier, baseline month, unconfirmed price/GST/MOQ units and relevant source notes; never convert a coil price into a sheet price. |
| "Show me laser cut tech list" | `references/laser-technology.json` and `references/laser-timing.md` | Columns: Thickness mm, Technology, Gas, Lens inches, Fast/Medium/Slow speed mm/min, Fast/Normal piercing seconds. Preserve alternative technologies at the same thickness. Explain O2/N2, state source machine/material/manual vintage and show applicable saved timing fields (extra piercing/preflow/blow) with unresolved-unit status. Include a concise note on nitrogen for e-coat, oxygen otherwise on mild steel, 10 minutes total sheet handling and actual program-time precedence. |
| "Show me hourly rate" | Only `references/rates.json` resource definitions and hourly_rate_basis/resource_selection | Columns: Resource, Labour AUD/h, Machine AUD/h, Combined AUD/h. Combined = labour + machine once. Show every saved resource unless filtered; state user-supplied combined-rate basis and AUD excluding GST. Do not substitute a general costing-defaults list, setup times or margin for this request. |

A bare "list" that clearly follows one of these topics inherits that topic. If it clearly refers to available requests, show summary, breakdown, nest and these three natural-language requests. If context does not resolve "list", ask one short clarification. A lookup alone does not invoke the costing calculator requirement. When a user additionally requests an estimate or a change to it, run the costing workflow for that portion separately.

## Modes

The user picks a mode in plain words ("summary", "breakdown", "nest"; `/costing <mode>` is an alias); quantity, MOQ and file apply as usual. Keep the same inputs and calculator results across modes in a conversation; switching mode only changes presentation unless inputs change.

| Mode | Output |
|---|---|
| summary | Summary only, per `report-format.md` "Summary mode": roll-up table, batch line, unpriced items. |
| breakdown (default when no mode is given) | Full authoritative report per `report-format.md`: roll-up, one table per Part and Assembly, notes. Also use this mode for follow-ups such as “give me a breakdown”, “pieces per hour”, or “setup time”; retain the prior estimate's inputs unless the user changes them. Never replace it with an abbreviated operation table. |
| nest | Laser nest page: run `scripts/nest.py … --html <part>-nest.html --title "<part> Nest" --sheet-price <$/sheet>` (shop 1200 × 2400 usable sheet per `estimating.md`, even when priced on IXL 1220 × 2440). Write it to the user's connected/output folder so it is attached; do not publish it as an artifact unless asked, and do not claim it rendered without seeing it. Give the file path and per-sheet counts, utilisation and $/part in chat. The page is self-contained (no CDN); each blank is drawn once and placed by reference, so keep it under 250,000 bytes (the script reports the size). Needs STEP outlines (see `estimating.md`). |

## Workflow

Read each reference file at the step that first needs it, once.

1. Read `estimating.md`, then the drawing (text and every sheet visually) and reconcile the BOM. For a STEP-only input, run `scripts/step_geometry.py` first.
2. Read `rates.json`. For laser work, read `laser-timing.md` and matching `laser-technology.json` entries before building the laser cycle. State the batch quantity (default 100, provisional) and build a route per component, then assembly operations once.
3. Read `material-pricing.md` and `ixl-material-baseline.json`. Price material; estimate yield per `estimating.md` (true-shape `scripts/nest.py` when STEP outlines exist, else dimensioned flat envelopes).
4. Read `calculator-contract.md`. Write schema-2 input and run `python3 scripts/calculate.py INPUT.json --out RESULT.json` (prints headline totals only; open RESULT.json for the per-row tables of the base case). It must succeed before every costing report and follow-up costing revision (saved-list lookups are exempt); verify row sums, batch/unit totals and margin from its output. Run low/base/high and batch-size scenarios where `estimating.md` requires them.
5. Read `report-format.md`. Report in chat exactly per it: cost roll-up first, then one table per Part and Assembly.
6. For revisions, run `python3 scripts/compare.py PREVIOUS_RESULT.json CURRENT_RESULT.json` and explain every changed cost.
7. End with the few inputs most likely to change the result (usually batch size, factory rates, nest yield or coating quote). Deliver the estimate before asking optional questions. Create spreadsheets/documents only when requested.

## Setup and messages

`calculate.py` and `compare.py` are standard library. STEP geometry and nesting need `scripts/requirements.txt` (the CAD engine): before installing, tell the user it takes about a minute. If it cannot install (no network), say so plainly and continue from the drawing with dimensioned flat envelopes.

Report a script error or warning as one plain sentence plus the next action, never raw output or internal field names.

A worked example is in `examples/bracket/`.
