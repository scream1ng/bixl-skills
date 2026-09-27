---
name: costing
description: Estimate sheet-metal fabrication cost from uploaded PDF drawings, drawing images or CAD, with per-component raw material, laser cutting, bending, setup hours, pieces per hour, welding, finishing and assembly totals. Use when a user drops a drawing for costing, requests a manufacturing estimate, or wants process and material cost breakdowns.
---

# Costing

Return an immediately useful internal budget estimate in chat. Do not require STEP or a questionnaire before starting from a readable drawing. AUD excluding GST by default. Label provisional assumptions prominently; never describe a budget estimate as a supplier quotation.

Each rule lives in one reference file:

| File | Owns |
|---|---|
| `references/estimating.md` | Input precedence, drawing reading, BOM and hardware ownership, batch quantity, yield, cycle times, scenarios, revisions |
| `references/material-pricing.md` | Material price decision order, IXL baseline, proxies, scaling, units/GST, age |
| `references/rates.json` | Saved resource rates, default resources, fallback throughputs, margin, e-coat reference |
| `references/calculator-contract.md` | Calculator input schema and output fields |
| `references/report-format.md` | Chat report layout, margin/selling presentation, inspection/packing absorption |

## Modes

The user picks a mode in plain words ("summary", "breakdown", "nest"; `/costing <mode>` is an alias); quantity, MOQ and file apply as usual. Keep the same inputs and calculator results across modes in a conversation; switching mode only changes presentation unless inputs change.

| Mode | Output |
|---|---|
| summary | Summary only, per `report-format.md` "Summary mode": roll-up table, batch line, unpriced items. |
| breakdown (default when no mode is given) | Full authoritative report per `report-format.md`: roll-up, one table per Part and Assembly, notes. |
| nest | Laser nest page: run `scripts/nest.py … --html <part>-nest.html --title "<part> Nest" --sheet-price <$/sheet>` (shop 1200 × 2400 usable sheet per `estimating.md`, even when priced on IXL 1220 × 2440). Write it to the user's connected/output folder so it is attached; do not publish it as an artifact unless asked, and do not claim it rendered without seeing it. Give the file path and per-sheet counts, utilisation and $/part in chat. The page is self-contained (no CDN); each blank is drawn once and placed by reference, so keep it under 250,000 bytes (the script reports the size). Needs STEP outlines (see `estimating.md`). |

## Workflow

Read each reference file at the step that first needs it, once.

1. Read `estimating.md`, then the drawing (text and every sheet visually) and reconcile the BOM. For a STEP-only input, run `scripts/step_geometry.py` first.
2. Read `rates.json`. State the batch quantity (default 100, provisional) and build a route per component, then assembly operations once.
3. Read `material-pricing.md` and `ixl-material-baseline.json`. Price material; estimate yield per `estimating.md` (true-shape `scripts/nest.py` when STEP outlines exist, else dimensioned flat envelopes).
4. Read `calculator-contract.md`. Write schema-2 input and run `python3 scripts/calculate.py INPUT.json --out RESULT.json` (prints headline totals only; open RESULT.json for the per-row tables of the base case). It must succeed before reporting; review its totals. Run low/base/high and batch-size scenarios where `estimating.md` requires them.
5. Read `report-format.md`. Report in chat exactly per it: cost roll-up first, then one table per Part and Assembly.
6. For revisions, run `python3 scripts/compare.py PREVIOUS_RESULT.json CURRENT_RESULT.json` and explain every changed cost.
7. End with the few inputs most likely to change the result (usually batch size, factory rates, nest yield or coating quote). Deliver the estimate before asking optional questions. Create spreadsheets/documents only when requested.

## Setup and messages

`calculate.py` and `compare.py` are standard library. STEP geometry and nesting need `scripts/requirements.txt` (the CAD engine): before installing, tell the user it takes about a minute. If it cannot install (no network), say so plainly and continue from the drawing with dimensioned flat envelopes.

Report a script error or warning as one plain sentence plus the next action, never raw output or internal field names.

A worked example is in `examples/bracket/`.
