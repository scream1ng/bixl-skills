---
name: draft-pfc
description: v1.0 · Draft and revise process flow charts (PFCs) from D365 BOM spreadsheets or draft calc parts tables using the IXL form. Preserve component branches, materials, hardware and operation sequence; include supplied CAD isometric views; deliver a complete HTML review with pinned comments before approved Excel export. Use for BOM-to-PFC, manufacturing flow charts and PFC revisions. Not for costing, CAD design or inspection check lists.
---

# Draft PFC

Turn a BOM into a company-form process flow chart through three stages: source interpretation, complete HTML review, then approved Excel. Keep this skill self-contained: use its bundled form, logo, renderer and comment controller. No other personal skill is required.

## Read only what the stage needs

| Stage/input | Read |
|---|---|
| Every job | [BOM rules](references/bom-rules.md), [job format](references/job-format.md) |
| Preview or layout revision | [Presentation](references/presentation.md) |
| Supplied CAD/drawing or requested isometric views | [Isometric views](references/isometric-views.md) |
| Final Excel or output verification | [Validation](references/validation.md) |

Run bundled commands from this skill directory, with job paths supplied explicitly. Do not read script source unless adapting a supported mapping or diagnosing a failure. Use available spreadsheet/PDF tools only to inspect or render outputs.

## Change boundaries

Ordinary generation or “change this PFC” edits the job only. Change permanent rules/templates only when the user requests a skill update or confirms that scope. Preserve stable node keys, original BOM rows, source hashes, evidence and requested revision history. Never promote one part's codes, quantities, solid indices, finish, dimensions or cameras to defaults. The reference workbook establishes presentation, not universal process facts.

## 1. Interpret the source and build the draft

Use the supplied D365 BOM or calc parts table as the primary input; `import` detects which. A calc parts table is the pre-system draft BOM: code/description rows, finished part first, each process row ending in its stage word (see BOM rules). CAD, route sheets and drawings are optional evidence. With only CAD or a drawing, ask for the BOM or calc table; never write a chart by hand. Ask only if missing information prevents a meaningful draft; otherwise keep TBC and a concise review decision. Inspect sheets and identify the BOM by headers.

```bash
python scripts/pfc.py import "INPUT - BOM.xlsx" --job JOB
# Works for a D365 BOM or a calc workbook. Add --sheet "BOM" only when needed to select one table.
```

Inspect `JOB/spec.json` before presenting it. The parser is a first pass. Verify owning levels, child-to-parent production flow, independent component branches and the actual consuming/joining stage for material and hardware. Consolidate setup, machine and operator records into physical operations; keep surcharge/cost rows as evidence. Keep packing consumables together. Derive units/carton only from a clear carton quantity and its owning lot.

Preserve item codes exactly. Infer operation names from machine/service evidence, not suffixes alone. Use supplied numeric route operation IDs when available; otherwise propose 10, 20, 30… per route, restarting independent branches, and retain that basis in the spec. Refine provisional ordering/consumption links from route evidence or feedback. Never invent processes, material, transport, storage locations, inspection limits or suppliers from costing records. An inspection symbol does not establish acceptance criteria.

If CAD is supplied, identify the main part, secondary components, hardware and finished assembly from exact solids and current drawing evidence. Render all relevant views before sharing the complete review. Record source identity, solid selection, camera and finish; use the same PNG bytes in preview and Excel. Omit unsupported pictures or retain a source-proven drawing crop rather than fabricating geometry.

## 2. Complete the HTML review and revise

```bash
python scripts/pfc.py preview JOB/spec.json
```

Inspect and deliver the single `preview.html`, retaining `preview-rN.html`. Complete the graph, renders and review card in one pass before asking for review. Keep it self-contained and strictly below 1,000,000 bytes. Do not send a preview ZIP, provisional Excel, source records or partial picture-by-picture previews unless requested.

Preserve the source form's page border and layout order, but enlarge process boxes beyond the source form and spread rows down the page so symbols sit in one row with clear gaps (`spaced()` in `pfc.py`); keep gold symbols with blue outlines, boxed legend, typography and paragraph spacing. Keep main-route arrows on a shared vertical axis and branches horizontal/vertical. Keep the current logo. Prefer isometric pictures outside process boxes: main part middle, small secondary component right, hardware left, finished assembly bottom right. Preserve clear space around arrows and labels.

Use one compact right-hand comment card: title/revision, **Comment mode**, **Copy comments**, and concise **To confirm** decisions. Click a process, material, image or arrow to place C1/C2, type in the anchored box, reopen/collapse with the pin and delete with renumbering. Hide empty comments/status; omit Download comments and repeated instructions. Keep revision, fingerprint, stable node key and normalized position in copied/persisted notes. Clipboard failure must expose selectable text. Comments are feedback, never executable patches or approval.

Apply pasted feedback to the matching revision/key. Preserve source/evidence, increment `revision`, append a concise `history` entry, remove approval and regenerate. Use measured-coordinate `layout.boxes` only for deliberate placement changes; review the routed arrows again. Fix known overlap, clipping or omitted labels before presenting. The bundled exporter supports the measured single-page form with up to five main stages and simple side branches. More complicated routes require an inspected additional-sheet mapping; do not silently stretch the form, shrink away legibility or omit items.

## 3. Approve, export and verify Excel

Explicit approval of the current preview, or a request to finalize it, authorizes export. Record the actual user wording:

```bash
python scripts/pfc.py approve JOB/spec.json --note "actual user wording"
python scripts/pfc.py export JOB/spec.json
```

An edit request, screenshot, comments or silence is not approval. Spec, source, CAD/drawing, render, template, script, logo or preview changes invalidate the recorded binding. Test approvals never authorize a user job. Correct export/layout defects already within the user's finalization request without repeatedly asking, unless process content changes.

Export macro-free `.xlsx` with editable native boxes, text, connectors and embedded isometrics. Preserve the entire A1:X52 form grid, border cells, row/column dimensions, original print margins/centering and A4 portrait fit-to-page settings. Keep a single-sheet page number at 1; the preview revision is separate. Never execute source macros or claim VBA preservation.

Reopen and render the workbook, then follow validation. Verify every source item and operation, branch, packing detail, symbol, logo, render and full page. Correct defects before delivery. A saved print flag or another application's PDF does not prove Windows Excel printer settings. Report the exact limitation if export/render dependencies are unavailable. Deliver the workbook and requested preview; finalization is document generation, not a production release.

## Execution and handoff

Import, preview and Excel export use the Python standard library only, so they run the same in Claude, ChatGPT and a local shell. The exporter fills the bundled form directly and writes native DrawingML shapes. Optional CAD isometric rendering uses cadquery, numpy and Pillow from `scripts/render-requirements.txt`. If they cannot be installed, omit the pictures and say so instead of failing the job.

Keep the job's original sources, `spec.json`, render config/images, preview revisions, feedback and approved workbook together. Resume from this record; validate hashes before reusing it. Move paths relative to the job, not by changing evidence. HTML alone is not editable BOM/CAD authority. Keep job outputs and temporary tests outside this skill.

After code changes, run `python -m unittest discover -s tests -v` and `node tests/test_comments.cjs`. Validate the skill in place before saving permanent updates.
