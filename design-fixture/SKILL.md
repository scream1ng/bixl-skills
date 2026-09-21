---
name: design-fixture
description: Design and revise welding or checking fixtures from STEP geometry or dimensioned drawings, with an interactive concept preview before an explicitly requested verified delivery package. Supports laser-cut ribs, weld blocks, and solid printed checking fixtures.
---

# Design Fixture

One self-contained CAD workflow. Measure with OCP; never infer manufactured geometry or approval from a picture. Bundled scripts, hardware and references have no dependency on another skill.

## Route once

If fixture purpose is missing (including a bare invocation or geometry upload), ask one quick question: **“Weld fixture or Check fixture?”** Do not start fixture design until answered. Infer the construction default without another question unless ambiguity materially changes the job.

| Purpose | Default | Explicit alternative |
|---|---|---|
| Weld | `laser_rib`: 5 mm laser-cut ribs | `block`: machined/welded blocks |
| Check (`checking`) | `laser_rib`: 5 mm laser-cut ribs | `printed_solid`: solid plastic |

Reject weld + printed and checking + block for delivery. Explore only if the user explicitly requests a **concept-only exception**, recorded with its reason; never finalize that exception through this skill.

## Phases and context budget

1. **Survey and concept:** read [concept workflow](references/concept-workflow.md), [measured workflow](references/workflow.md), and [project record](references/project-record.md). For STEP read [survey](references/step-first.md). Create the specification yourself from measured geometry, not scaled example dimensions.
2. **Locate/support:** read each reference only when its feature is in the job: [construction/operation](references/construction-operation.md) for ribs, bracing, pins and load/unload; [assembly locating](references/assembly-locating.md) only for more than one part; [hole/slot locating](references/hole-slot-locating.md) only when locating from holes or slots; [locators and seating](references/locating-hardware.md) for pins, bushes or checking-fixture seating. Preserve 3-2-1 logic, no lone ribs (every upright crossed by a perpendicular member), suitable round/diamond pins, real bushes/manual withdrawal, practical bracing and supported clamp forces. Design so the whole workpiece lifts straight out away from the big part's primary datum with clamps open and removable pins withdrawn. For GH-201-B read [clamping](references/clamping.md); the scripts read its [hardware record](references/hardware/gh-201-b.json), so open it only for a value you need. Start from the standard mount plate with cap tabs into its cheeks. Use the actual 14-component CAD. Its supplied tilted-spindle pose is **not verified closed**. Never fake closure or equate mounting height with operating clearance.
3. **Datum scheme review (required before any concept):** run `scripts/workflow.py datum` and show the returned `datum-preview.html` — the 3-2-1 points and clamp on the bare part, no ribs, blocks or clamp bodies. Markers drag in their own face plane and hand back an exact mm patch; never read dimensions off the picture. **Comment mode** pins a numbered note to a clicked point on the part; **Copy all** hands back the moved-point patch and the notes as one text (where the clipboard is blocked it selects the text for Ctrl+C). Comments are review notes only — they never move a point or change the spec. A point reported `off_surface` is not on the placed CAD — fix the spec, not the marker. Record the user's own words with `workflow.py datum-ok --note "..."`. `concept` refuses to run until this ack exists, and it goes stale whenever contacts, locating groups, clamps, frame or sources change.
4. **Mode details — active branch only:** ribs: [laser construction](references/laser-cut-construction.md) and [spec schema](references/spec-format.md); blocks: [block construction](references/block-construction.md). Checking only: [inspection](references/inspection.md), [practical review](references/practical-review.md), [checking schema](references/checking-build.md), then [laser checking ribs](references/laser-ribs.md) or [printed construction](references/printed-solid.md) + [printed schema](references/printed-body-spec.md). Checking defaults stay 3.0 mm gap, 2.5 mm GO enters / 3.5 mm NO-GO does not. Datum contact, pin fit and handling clearance are separate. Require restraint/hold-down rationale and full gauge/hand access.
5. **Interactive concept:** read [preview](references/preview.md). Run `scripts/workflow.py concept`. It **stops before any preview is shown** when a basic check fails:
   - `cross_support`: lone rib. `cap_joints`: cap without tabs. `material_width`: undersized ligament. `mount_compactness`: oversized clamp plate.
   - `unload`: a rib or fixed pin in the straight unload path.
   - `pin_clearance` (laser ribs): a pin that intersects, sits within 5 mm of, or is not seated on a pad plate — cap tabs, cheeks and braces included; a sliding/removable pin may seat on its bush.
   - `brace_merge` (laser ribs): parallel braces under 50 mm apart in plane and span — commonise them into one brace.
   - `flange_coverage` (checking): a sheet feature — flange, tab, wall, web — with no station, datum, alternative or user-quoted waiver, or a station off the part. An unchecked feature under 5 mm wide is unknown, not a blocker. The datum preview shows unchecked features red.

   Fix the named items and rerun; never show a concept with a blocker. Then show Three.js inline when supported, and invite feedback through the same comment pins and Copy comments as the datum review (window capture still works). Send the single `preview.html` alone (target 250,000 bytes, strictly below 1,000,000) — it is self-contained; keep CAD files, PNGs and records private and send no concept ZIP; send `spec.json`/`project.json` only on a handoff request or at finalization. Revise with `scripts/spec_patch.py spec.json '<small JSON patch>'` rather than rewriting the spec, preserve IDs, and regenerate. **Stop here by default.** Do not run nesting, manufacturing export or final package generation during concept iteration.
6. **Finalize only on explicit user request:** “finalize”, “approve”, or “complete the package” authorizes package generation, **not engineering/fabrication approval**. An initial explicit complete-package request may run end-to-end after survey/concept and validation. Read [finalization](references/finalization.md) only now; record authorization and run the appropriate pipeline. For laser ribs, emit joined open single-stroke etch polylines (never DXF text) and use the configured shop-stock usable zone while preserving a practical rectangular remnant. Fix known defects; retain genuine unknowns.

Astra is recommended for initial concept; Sol for revisions/finalization. This is guidance, not automatic switching. Persist `spec.json` plus `project.json` for a fresh chat/model. Validate source hashes, units, frame and version before reuse; changed source requires a fresh survey and invalidates evidence/approval. A byte-only change (re-export, identical solids by `source_geometry` fingerprint) is rebased automatically before authorization.

## Invariants and boundaries

Keep `cad_verified`, `fabrication_ready`, `fixture_calibrated`, and `inspection_validated` distinct. Unknown/fail/exception never becomes pass. A complete package is not a production release. Preserve construction, fastener and pin evidence; continuous loading/release, clamp motion, weld access, stiffness, calibration and inspection qualification are not proved by sample clearance tests.

Rib automation supports one thickness, horizontal seat and vertical seated polygonal ribs. Blocks use an explicit OCP/CAD workflow, not rib fabrication automation. Curved/oblique checking, complex printed forms and unsupported arrangements need explicit measured CAD work. Three.js meshes are approximate and non-authoritative; exact OCP CAD owns measurements/verification.

Setup: install `scripts/requirements.txt` in a task environment (tested OCP 7.8.1.1; supported 7.8.x). Run `python -m unittest discover -s tests -v` after code changes. Low-level builders remain for regression tests; use the workflow gate for real projects.
