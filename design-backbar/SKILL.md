---
name: design-backbar
description: "v1.7 · Design LVD press-brake backbar jigs from one STEP file. Use a supplied flat pattern or estimate unfolding from the formed part; check direct gauging first, then deliver only required backbar DXFs and a formed STEP with programming gauge tabs, plus a simple, commentable bend-sequence preview. Trimming is only applied when explicitly requested in a user message or preview comment."
---

# Design Backbar

## Contract

Accept **one STEP file**. Prefer its supplied flat pattern when present. Otherwise estimate the flat from the formed solid; do not demand another flat-pattern export before trying the supported unfolding route.

Deliver:
- **DXF:** one per required backbar plate, mm at 1:1, for 6 mm material.
- **STEP:** formed part with required gauge tabs merged into one valid solid, for CADMAN-B.
- **HTML review:** all bend operations in sequence, visible programming tabs, and a gauging status for every operation: BACKBAR, BACKBAR OPTION, DIRECT EDGE, DIRECT EDGE TRIAL, TRIM EDGE or TRIM EDGE TRIAL (TRIM when the contact edge borders a physical change). Show the matching backbar and dashed gauge line when required; retain pinned comments.

Keep estimated flat patterns, intermediate geometry, logs and JSON internal unless requested. **Finalize delivers one ZIP, never loose files**: the user approves the design in the HTML preview, so “finalize”, “package it” or “complete” means rerun with `--requirements` and `--package` and send only that ZIP. Use `--package` or `scripts/package_delivery.py:package_run` with the completed run's explicit `deliverables` manifest. Include only current selected-route DXFs, programming STEP, latest HTML/optional PNG and a brief README with unresolved trial checks; exclude superseded plates, unapproved alternatives and internal files. Never collect files by scanning old revision folders.

Keep three distinct geometry states: the original input blank, the revised physical blank, and the programming model with CAD-only tabs. Preserve the original before any authorised edit. The physical blank has **no programming tabs**. Its outline defines the jig pocket. The STEP tabs provide straight gauge edges for bending software. They do not enlarge the programmed gauge distance beyond the blank tip.

## Agreed changes must exist in delivered CAD

**A completed package must contain every agreed CAD change, verified in the exported STEP.** Packaging is a completion claim, not merely a ZIP operation. Maintain an internal inventory of agreed common bends, physical extensions/reshapes/trims and CAD-only tabs from the conversation; never drop an unfinished item to pass delivery.

Distinguish **proposed common operation**, **already common in input CAD**, and **commonised and verified after correction**. `--sequence` groups operations only; it does not move a bend. A valid solid, shared plate, matching labels, or looser acceptance tolerance does not establish completion.

When the user asks to make bends common, perform the necessary CAD correction within the agreed scope: keep a reference bend fixed, align the other actual bend geometry, rebuild the connecting flange, and retain thickness, intended radii and surrounding features. Use a part-specific geometry implementation when needed; the CLI does not automatically repair arbitrary bends. Measure affected hole centres, edges and dimensions before/after. Report consequential movements clearly. Do not substitute a report edit for the CAD work or ask again for permission already given.

Before delivery, reopen the exported STEP and check each agreed result. For common bends, verify bend identity, unfolded and formed/staged axes, angles, radii and fold sense. Never increase tolerance to rescue a failed correction. Highlight the corrected region and show before/after measurements even if the outer contour barely changes. Regenerate affected flat references, backbar pockets and reports from the corrected model; do not mix revisions.

Use `scripts/completion.py` and the inventory workflow in [references/completion.md](references/completion.md). Completed packaging fails when any agreed item is missing, unmeasured, out of tolerance or linked to stale files. Fix the cause; if blocked, state the unfinished change. Only an explicitly requested interim package may bypass completion, with **INCOMPLETE** in its filename and unresolved work in its README. Keep shop trial/import checks distinct from incomplete CAD work; verified CAD changes do not prove manufacturing readiness.

## Part identity and bend numbering

Reset part geometry, bend IDs, tooling assumptions and user exceptions when a new STEP is supplied. Never carry over a prior part’s trims, tab positions, sequence or short-contact approval. Resolve the current bracket/body before proceeding.

Follow the user’s annotated bend numbering. Match each label to geometry, then use `--bend-map` to assign those IDs before side, tab, trim or sequence options. Preserve IDs across preview, STEP tab ownership, DXFs and internal report. If no numbering is supplied, establish one consistent view and keep it through revisions; never renumber by operation order.

## Trimming and reshaping: user instruction only

**Never suggest, consider as a default design step, or apply edge trimming automatically.** A nearly parallel edge is not permission to change the part. Report its measured angular mismatch if relevant, then design to the existing contour.

Use trimming only when explicitly requested in the user's message or a pasted preview comment. Apply the requested trim to the real blank, affected backbar pockets and formed STEP together. Record maximum material removal. Never reuse a previous part's trimming request on a new part.

`--trim-for N` implements the narrow request “trim the gauged free edge parallel to bend N.” It removes material back to the nearer end of a straight end edge (up to 2 mm automatically, never adds material). A larger or differently located user-requested trim needs explicit geometry implementation and checks; do not force this option to approximate unrelated changes.

For a requested extension, use the smallest local addition supported by the gauging need; measure it against the original contour rather than choosing a large arbitrary extension. For a requested reshape, adjust the local edge parallel to the bend while retaining corner radii and the part’s overall appearance. Do not substitute a large square extension or remove the backbar without checking gauging again. Use the existing conversation to establish whether the real blank changes or only CAD programming geometry changes; ask only if this remains ambiguous. The simple `--trim-for` operation does not guarantee preserved corner radii: implement and validate the requested contour explicitly when needed. A requested extension is not permission to trim.

## Workflow

1. Identify the current part and bend numbering. Record the agreed-change inventory and implement requested CAD corrections, then run the bundled script. Inspect every bend’s direct-gauge classification before discussing plates.
2. If a genuine parallel contact edge at least 10 mm long exists at the chosen end, use direct gauging: no plate, no tab and no +50 mm offset. Do not silently treat a nearly parallel edge as parallel.
3. For shorter parallel edges, report the measured contact as a direct-trial candidate; the 10 mm threshold is a default, not proof a backbar is essential. Use `--direct-trial N` only with explicit job-specific trial authorization. Otherwise label the plate BACKBAR OPTION. For remaining assisted bends, generate the contour pocket and only the necessary programming tab. An existing parallel edge at least the requested tab width can supply the CAD gauge reference without a new virtual tab. Reuse identical plates when their shape and position agree.
   Plan tabs collectively against every bend’s gauge limit, including direct edges. Search positions around the same gauging tip within the 10 mm height limit; keep the gauge line and tab width. Reuse one physical programming tab when its geometry agrees. Never move an explicitly positioned tab automatically; report conflicts without changing gauge distance. Do not add a redundant tab just because another bend uses the same backbar. Shared plates do not combine bend operations. Explicit common-bend groups are one operation with one gauge master; do not add a follower operation or duplicate tab.
4. If the user requests a trim or provides pinned comments, rerun with the appropriate option. Trimming must not be inferred from a near-parallel result.
5. Establish the dependency-safe sequence before presenting the report. Keep user-selected sequences if valid; flag violated dependencies. Check the report, STEP validation and preview. Render the preview or extract its SVGs for visual inspection. Highlight tabs clearly; never call an unvalidated result production-ready.
6. On finalize, pass the exported-CAD completion check and deliver the `--package` ZIP of the matching DXFs, formed STEP and HTML preview; do not send the files individually. State estimated unfolding assumptions and any bend-order or tooling constraints.

## Run

Use the scripts in this skill directory directly; do not copy a large code block from SKILL.md.

```bash
uv run --no-project --python 3.12 \
  --with 'cadquery-ocp>=7.8,<7.9' --with 'ezdxf>=1.3,<2' --with 'numpy>=1.26,<3' \
  python '<skill directory>/scripts/backbar.py' PART.step OUT
```

If these dependencies are already available, run plain Python. Without `uv`, install them into a task-local virtual environment. OCP 8 is unsupported. If dependencies cannot be installed, report the specific blocker.

Use a fresh output directory for each revision so old plates cannot leak into delivery. The console JSON and `OUT/report.json` are internal records; manufacturing files and the review preview are the only default deliverables.

### Options

| Option | Use |
|---|---|
| `--bend-map A,B,…` | Detected bend IDs listed in user-number order; apply before all other bend options. |
| `--sequence A+B,C+D,E` | Operation order; `+` groups simultaneous common bends. List every bend once. The first member owns the gauge, plate and tab. |
| `--common-line-tol MM` | Default 0.001 mm input common-axis limit; may tighten, never widen it to pass a correction. |
| `--direct-trial N` | Explicit job authorization for direct contact below the default 10 mm threshold; use the operation master. |
| `--requirements FILE` | Reviewed JSON inventory of every agreed CAD change; see completion reference. |
| `--package` | Finalize: completed ZIP; requires the inventory, exported-CAD checks and matching file hashes. |
| `--side N=+` / `--side N=-` | Use the other gauging end for bend N. Read its current sign first. |
| `--at N=X` | Place a tab's outer side X mm along the bend from the tip; signed coordinate. |
| `--tab-width MM` | Default 5 mm; only change when requested. |
| `--wrap MM` | 10–20 mm; default 20. |
| `--die-clear MM` | Assumed minimum bend-line-to-plate-front clearance; default 8. |
| `--flat N` | Select supplied flat body N if ambiguous. |
| `--trim-for N` | **Explicit user-requested trim only**, to make the gauged free edge parallel to bend N. |
| `--gauge-edge N=Y` | User-selected parallel edge Y mm from bend N's line on the chosen side (e.g. an ear tip nearer than the half-plane tip). Snaps within 0.05 mm; fails if no such edge. Usually paired with `--direct-trial N` when contact < 10 mm. |
| `--formed-ok N=A+B` | Waive a flat-region dependency for bend N when the user, or a measured check, shows bends A, B lie clear of N's gauging path (e.g. far along the bend axis). Reported in the step warnings with the axial distance; never applied silently. |

For common groups, set `--side`, `--at` and `--direct-trial` on the first member; follower overrides are rejected. Do not infer an option value from a screenshot dimension when exact geometry or comment coordinates are available.

## Shop standard

| Item | Value |
|---|---|
| Plate width × thickness | 100 × 6 mm |
| Finger slot | 50.2 mm wide × 20 mm deep, centred at rear |
| Blank tip to finger tip | 50 mm |
| Blank tip to plate rear | 70 mm |
| Wrap toward bend | 20 mm nominal; minimum 10 mm |
| Pocket clearance | 0.1 mm |
| Material each side of pocket | Minimum 10 mm |
| Tab width | 5 mm |
| Automatic maximum tab height | 10 mm |
| Tab end | Through blank tip, parallel to bend |

Keep these fixed unless the user changes the shop standard. A part that does not fit the fixed-width plate must be reported; never resize silently.

## Input handling and supported unfolding

For a supplied flat, use its separate bend-strip faces. If they have been merged, ask for an unmerged export or a formed-only file; do not guess bend locations from an undifferentiated flat.

For formed-only input, `scripts/unfold.py`:
- Rebuilds each flattened piece on the exact XY plane and rebuilds the merged outline from exact lines and arcs (span by span), joining collinear flange/bend-strip pieces. Imported (e.g. Rhino) spline trims otherwise break area checks, face fitting and pocket offsets. The rebuilt outline must stay within 0.002 mm of the unfolded outline; overlap checks use boundary areas, and tab volume uses Boolean differences, because integrated areas/volumes of imported trims can be off by ~1 mm³.
- Infers thickness from paired planar faces.
- Finds connected planar flanges and paired curved bend strips, including supported imported spline surfaces.
- Unfolds flange geometry by rigid transformations, preserving flange holes and contours.
- Determine the material side locally beside each tangent edge; a concave flange's centroid can lie on the wrong side of a notch.
- Estimates neutral bend widths from paired surface areas and tangent lengths with **K=0.50**; this is an estimate, not a material-specific calibrated allowance.
- Retains flange transforms so tabs and explicitly requested trims map back to the original folded geometry.
- Rejects curved tangent lines, incomplete/ambiguous topology, cyclic connections, overlaps and invalid blanks instead of fabricating a result.

One formed solid without an unambiguous match is required. Extra solids can be matched against a supplied flat; an ambiguous assembly needs the intended part identified. Do not claim support for arbitrary stampings, variable-thickness solids, hems or nondevelopable surfaces.

For a supplied flat, tab mapping must identify one unique formed flange. A symmetric or unsupported mapping must fail clearly rather than attach a tab to an arbitrary flange.

## Gauging and sequence

Prefer a free gauging end with no intervening bend; when both are free choose the nearer end. If neither end is free, prefer a genuine parallel contact edge, then the nearer end. Report which intervening bends must remain flat. Honor user-selected ends through `--side`.

Reject cyclic flat-region requirements and ask for different gauging ends. Report a dependency order for valid choices, clearly distinguished from a complete collision-checked bending sequence.

Design every tab against the real blank contour. Check all tabs together and each tab’s own gauge edge independently. Automatic tab choices must avoid projecting beyond another bend’s gauge line. If the bounded search fails, review tab location or gauging end; do not accept the conflicting automatic choice. For explicitly requested tab positions, report any conflict and the need to select the intended gauge edge in CADMAN-B; never shift the gauge distance. A short contact below 10 mm requires explicit job-specific trial authorization; do not make it a new default.

Validate common groups with `scripts/operations.py`: axes must be parallel and collinear within the stated tolerance and known bend rotations must match. Retain measured offsets in the report. The exported-STEP completion check independently measures analytic bend axes, inner radii, rotation and fold sense. If analytic identification or staged geometry is unsupported, keep the change unresolved until measured custom verification is implemented. Tooling and a simultaneous stroke remain unverified; do not infer them from shared plates or parallel lines alone. Show each group once, highlight all its bend segments, and allow its members to form together when checking flat-region dependencies.

Preserve bend-order warnings on direct-gauge bends too. A parallel edge may still sit beyond another bend.

Keep the following per-bend information in the internal engineering record; provide dimensions only when requested:
- Programmed bend-to-tab-edge distance.
- Actual bend-to-finger-tip distance, **program distance +50 mm**.
- Plate front to bend line; ask the user to check against the die in use.
- Wrap and measured pocket clearance.
- Tab width, near/far heights and zero offset from its intended gauge line.
- Shared plate identity, warnings, or any failed operation.

For direct-gauge bends, record contact length and gauge distance with **no jig offset**. Never label a direct-gauge bend as requiring a backbar.

## Simple sequence preview

Use `scripts/sequence_preview.py`, called by `backbar.py`, as the default review. Show the part large with one selectable row per operation, its bend IDs and gauging status. Label a short-contact fallback **BACKBAR OPTION**, and an authorized direct trial **DIRECT EDGE TRIAL**. Selecting an operation highlights the bend and its contact edge or programming tab. Show only the matching contour backbar for that operation; identify a shared plate consistently while keeping separate rows and gauge distances for separate operations. A common-bend group gets one row, one shared gauge reference and no follower step.

Render the current physical blank with its holes and rounded corners and overlay CAD-only tabs in orange. Always show a top banner: green **Physical blank: UNCHANGED** or red **Physical blank: N CHANGE(S)**. Whenever physical geometry changes, show the **Physical part changes** section below the bend sequence: dashed grey original contour, blue material added, red material removed, numbered locations, closeups and measured local offsets. Retain numbered markers in operation views. State that these changes affect the real blank and formed CAD. Never rely on a note alone or confuse CAD-only tabs with physical additions.

Use `preview(..., operations=groups, original_blank=original)` so `scripts/physical_changes.py` computes Boolean differences from the actual contours. Custom reshapes must pass the preserved original in the same coordinate frame and update the package report's `physical_blank_changed`. The CLI does this automatically for `--trim-for`; other contours require explicit geometry implementation. Label sampled offsets as approximate; do not imply exact maxima. Show a dashed red gauge-reference line through the blank/tab tip, parallel to the bend, exactly **50 mm from the rear finger-slot shoulder**. Transform this line with the backbar geometry; do not confuse it with the bend line or the finger contact at the slot shoulder. Direct-edge steps show no plate or jig-offset line.

Keep tab dimensions, coordinates and full calculation tables out of the main view. Keep the folded-part reference and concise unresolved trial checks available below it. Clearly label the flat layout as a reference, not a progressive folded simulation. Retain comment pins; include the selected bend and display-coordinate frame in copied comments. Do not interpret display coordinates as the old tab-detail bend frame.

Picture first: operators read the drawing, not text. Each step view shows bend badges with angle (red = this step, grey ✓ = already bent, white = still to come), a gauge-distance arrow labelled with the program distance, the contact edge (green = existing edge, thick red = trimmed edge), a hatched **keep fingers clear** zone for material beyond a direct gauge line, a TRIAL tag on authorized short contacts and a PLATE B#/B# label on shared plates. Direct steps carry an *Existing part edge · no trim* or *Trimmed edge · real blank changed* label; near-parallel edges that were not used are labelled with their measured angle and *not trimmed*. Do not draw backgauge fingers or step-list thumbnails.

Inspect assisted, shared and direct-edge selections; verify no stale plate remains on direct steps, no clipped geometry, correct bend IDs, and visible tabs and dashed lines. A preview-only styling change does not require rewriting validated CAD/DXFs.

## Validation

- Require one valid, non-overlapping flat outline.
- Measure 0.1 mm clearance against the actual working contour (estimated if unfolded).
- Reject split or invalid plates; do not silently export only the largest piece.
- Require each tab to join one unambiguous flange and its edge to agree with the gauge line within 0.001 mm.
- Check that each tab fusion leaves one valid solid before adding the next tab or merging faces. A zero-distance contact alone does not establish a solid join.
- Require final formed STEP to contain one valid solid, with tab-added volume agreeing with tab area × thickness within max(0.1 mm³, 0.1% of tab volume).
- Merge coplanar tab/flange faces and collinear edges before STEP export, using 0.0000001 mm linear and 0.0000001 rad angular tolerances. Preserve bounds within 0.001 mm and volume within max(0.1 mm³, 0.1%) capped at 0.5 mm³; reject a split or invalid result. Record face counts before and after merging.
- Verify every tab is retained after STEP readback by intersecting its reference solid with the exported part. Require its volume within max(0.1 mm³, 0.1% of tab volume). Report strict surface/edge analysis warnings separately: a basic valid-solid result does not prove SolidWorks/CADMAN-B import compatibility. Do not dismiss residual warnings or claim application validation without a confirmed import.
- Construct `BRepCheck_Analyzer(shape, True, False, True)` for strict checks on both the unmodified source and exported result. State source warnings separately; do not misattribute them to unfolding or tab addition. Do not claim a STEP repair fixes an unfolding-direction error.
- If the user supplies a repaired file confirmed to import, preserve its exact bytes; re-export only as a separate, explicitly unconfirmed candidate.
- Read the exported STEP back; require one valid solid and volume difference within **max(0.5 mm³, 0.001% of part volume)**. Report the actual difference and limit. This accounts for STEP surface-integration precision; never loosen the threshold to rescue a failed run.
- Reopen the final STEP and verify each agreed edit against its recorded criteria. Use `verify_common_step` for supported common bends; retain measured before/after results and feature identity. A source or in-memory check is insufficient.
- Audit DXFs and inspect the rendered preview, including dimension labels and visible tab placement. Bind all current deliverables to the verified STEP before packaging; any later file change requires a new check.

If a check fails, fix the cause or report the precise limitation. Do not present stale outputs from an earlier run as successful current deliverables.

## Review comments

The user enables **Comment mode**; the edge under the cursor highlights. A click pins a note that records **what** was clicked — edge ID, existing/trimmed, line/arc, length, angle to the step's bend and distance from its bend line — or the backbar plate (DXF name) or CAD-only tab, plus display coordinates. Quick buttons prefill intent: *Gauge B# on this edge*, *Backbar on this side*, *Move tab here*, *Request trim ⚠* (edges) and *Move/Remove tab* (tabs). **Copy all** fills a plain-text box, selects it and tries the clipboard; if blocked, the user presses Ctrl+C/⌘C. Use the recorded edge facts first; transform display coordinates only when no feature was recorded. A *Request trim* note is an explicit trim request; any other note is not.

- Change gauging end: rerun `--side N=` with the opposite sign.
- Gauge on a picked parallel edge: `--gauge-edge N=Y` with the recorded distance (plus `--direct-trial N` below 10 mm contact, which the note itself authorizes for this job only when it says so).
- A requested end that creates a dependency cycle: report each conflicting dependency with its measured axial distance; use `--formed-ok` only when the flagged bend is clear of the gauging contact/plate region, and say so.
- Move tab: transform the pin from the named display frame to that bend’s local frame before deriving `--at N=X`. Only older tab-detail views already report coordinates along the bend from the blank tip. Preserve requested tab positions exactly.
- Request a parallel-edge trim: only then use `--trim-for N` and report removal.
- Other explicit geometry changes: implement in the reusable geometry workflow, validate and regenerate all affected outputs. Never patch only the displayed picture or a DXF independently of its STEP and contour source.

## Limits to state when relevant

The script does not simulate punch/die collisions, backgauge reach or finger height, complete bending sequence, operator handling, or CADMAN-B's automatic choice of gauge edge. The 8 mm die clearance is an assumption. Verify estimated jig fit on a real blank.

Confirm tooling for each new part; do not inherit another part's die, punch or tab coordinates. For a V die, half the nominal opening is only an opening-edge reference, not the complete die-body envelope. Use an explicitly stated clearance assumption and retain at least 10 mm pocket wrap; report when both cannot be achieved. Import confirmation and tool-body clearance remain prerequisites to calling a package manufacturing-verified, even when the user requests a final ZIP.

## Maintenance

Keep instructions concise and geometry in `scripts/`. Test trim-edge naming, sliver filtering, outline rebuild, edge-aware comments and user gauge edges (tests/test_revision17.py), ordinary and short parallel contacts, angled edges, supplied flats, formed-only inputs, common-group validation, explicit physical-change highlighting, package manifests, missing agreed changes, stale exports and refusal cases. Include a two-ear regression: a valid solid with a 0.091 mm bend offset must fail completion; aligned exported geometry must pass. Test the real job against this check as well when its files are available. Never hard-code sample face numbers or part-specific bend counts. Preserve the no-trim default in both code and instructions.
