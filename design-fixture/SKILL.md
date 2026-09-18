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
2. **Locate/support:** read [assembly locating](references/assembly-locating.md), [hole/slot locating](references/hole-slot-locating.md), and [construction/operation](references/construction-operation.md) as these features are designed. Preserve 3-2-1 logic, suitable round/diamond pins, real bushes/manual withdrawal, practical bracing and supported clamp forces. For GH-201-B read [clamping](references/clamping.md) and its [hardware record](references/hardware/gh-201-b.json); use actual 14-component CAD. Its supplied tilted-spindle pose is **not verified closed**. Never fake closure or equate mounting height with operating clearance.
3. **Mode details — active branch only:** ribs: [laser construction](references/laser-cut-construction.md) and [spec schema](references/spec-format.md); blocks: [block construction](references/block-construction.md). Checking only: [inspection](references/inspection.md), [practical review](references/practical-review.md), [checking schema](references/checking-build.md), then [laser checking ribs](references/laser-ribs.md) or [printed construction](references/printed-solid.md) + [printed schema](references/printed-body-spec.md). Checking defaults stay 3.0 mm gap, 2.5 mm GO enters / 3.5 mm NO-GO does not. Datum contact, pin fit and handling clearance are separate. Require restraint/hold-down rationale and full gauge/hand access.
4. **Interactive concept:** read [preview](references/preview.md). Run `scripts/workflow.py concept` and show its single `preview.html` inline. Target 850,000 bytes and keep it strictly below 1,000,000 bytes. The default viewer contains only rotate/pan/zoom and Workpiece, Fixture and Hardware visibility toggles; keep CAD files, PNGs and engineering records private during review. Revise the responsible spec, preserve IDs, and regenerate. **Stop here by default.** Do not provide a concept ZIP or run nesting, manufacturing export or final package generation during concept iteration.
5. **Finalize only on explicit user request:** “finalize”, “approve”, or “complete the package” authorizes package generation, **not engineering/fabrication approval**. An initial explicit complete-package request may run end-to-end after survey/concept and validation. Read [finalization](references/finalization.md) only now; record authorization and run the appropriate pipeline. For laser ribs, emit joined open single-stroke etch polylines (never DXF text) and use the configured shop-stock usable zone while preserving a practical rectangular remnant. Fix known defects; retain genuine unknowns.

Astra is recommended for initial concept; Sol for revisions/finalization. This is guidance, not automatic switching. Persist `spec.json` plus `project.json` for a fresh chat/model. Validate source hashes, units, frame and version before reuse; changed source requires a fresh survey and invalidates evidence/approval.

## Invariants and boundaries

Keep `cad_verified`, `fabrication_ready`, `fixture_calibrated`, and `inspection_validated` distinct. Unknown/fail/exception never becomes pass. A complete package is not a production release. Preserve construction, fastener and pin evidence; continuous loading/release, clamp motion, weld access, stiffness, calibration and inspection qualification are not proved by sample clearance tests.

Rib automation supports one thickness, horizontal seat and vertical seated polygonal ribs. Blocks use an explicit OCP/CAD workflow, not rib fabrication automation. Curved/oblique checking, complex printed forms and unsupported arrangements need explicit measured CAD work. Three.js meshes are approximate and non-authoritative; exact OCP CAD owns measurements/verification.

Setup: install `scripts/requirements.txt` in a task environment (tested OCP 7.8.1.1; supported 7.8.x). Run `python -m unittest discover -s tests -v` after code changes. Low-level builders remain for regression tests; use the workflow gate for real projects.
