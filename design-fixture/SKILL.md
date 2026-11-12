---
name: design-fixture
description: v1.9 · Design and revise welding or checking fixtures from STEP geometry or dimensioned drawings, with an interactive concept preview before an explicitly requested verified delivery package. Supports laser-cut ribs, weld blocks, and solid printed checking fixtures.
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

Every file read stays in context for the rest of the job. This table is the only reading list: read the active mode's files in `references/`, once, and nothing else.

| When | Read |
|---|---|
| All | project-record; step-first for STEP input; clamping when GH-201-B is used |
| Weld, laser ribs | weld-workflow, construction-operation, laser-cut-construction, spec-format |
| Weld, blocks | weld-workflow, construction-operation, block-construction |
| Check, laser ribs | checking-workflow, inspection, practical-review, checking-build, laser-ribs |
| Check, printed | checking-workflow, inspection, practical-review, checking-build, printed-solid, printed-body-spec; then build the body by **Shop standards → Printed body** below. `examples/checking-printed/gauge-reference/` is superseded (posts/pads layout, heat-set inserts, slow mesh offset): do not use it |
| Feature in job | assembly-locating (more than one part), hole-slot-locating (locating from holes/slots), locating-hardware (pins, bushes, checking seating) |
| Phase | preview at concept (step 5), finalization only at step 6 |

Open `hardware/gh-201-b.json` only for a value you need (the scripts read it). Do not open script source unless a command fails and its message does not name the fix.


1. **Survey and concept:** Create the specification yourself from measured geometry, not scaled example dimensions or bounding boxes. Survey datums, units, tolerances, loads, parts and joints; choose an accessible right-handed frame and retain its transform. Identify functional faces/holes/slots from exact trimmed geometry — a cylinder is not automatically a hole, nor a plane a flange. Keep missing engineering inputs open. Checking needs every flange inventoried; welding needs a weld access/distortion strategy. Initialize with `workflow.py init spec.json project.json --kind weld|checking [--construction block|printed_solid]`.
2. **Locate/support:** Preserve 3-2-1 logic with every primary (A) point of a part on one surface, spread along it — never split across a bend or two straights; no lone ribs (every upright crossed by a perpendicular member), suitable round/diamond pins, real bushes/manual withdrawal, practical bracing and supported clamp forces. Design so the whole workpiece lifts straight out away from the big part's primary datum with clamps open and removable pins withdrawn. For GH-201-B, start from the standard mount plate with cap tabs into its cheeks. Carry every dowel on the standard pin pad (hardware/pin-pad.json) named in `pin_locators[].pad`, on two cheeks with cap tabs, never on a rib edge. Use the actual 14-component CAD. Its supplied tilted-spindle pose is **not verified closed**. Never fake closure or equate mounting height with operating clearance.
3. **Datum scheme review (required before any concept):** run `scripts/workflow.py datum` and show the returned `datum-preview.html` — the 3-2-1 points and clamp on the bare part, no ribs, blocks or clamp bodies. Markers drag in their own face plane and hand back an exact mm patch; never read dimensions off the picture. **Comment mode** pins a numbered note to a clicked point on the part; **Copy all** combines moves and notes. If clipboard access is blocked, the complete text is selected in an inline box: press ⌘C/Ctrl+C, then paste into chat. Comments are review notes only — they never move a point or change the spec. A point reported `off_surface` is not on the placed CAD — fix the spec, not the marker. A primary point ringed red sits off the part's primary face: `datum-ok` refuses until the A points share one face or a user-quoted `primary_surface_waivers` entry exists. Record the user's own words with `workflow.py datum-ok --note "..."`. `concept` refuses to run until this ack exists, and it goes stale whenever contacts, locating groups, clamp contact/force, frame or sources change (rib or clamp-body edits do not stale it).
4. **Checking mode:** Checking defaults stay 3.0 mm gap, 2.5 mm GO enters / 3.5 mm NO-GO does not. Datum contact, pin fit and handling clearance are separate. Require restraint/hold-down rationale and full gauge/hand access.
5. **Interactive concept:** Run `scripts/workflow.py concept`. It **stops before any preview is shown** when a basic check fails:
   - `primary_surface`: a part's primary (A) points on separate surfaces (across a bend or straights).
   - `cross_support`: lone rib. `cap_joints`: cap without tabs, or a cheek run through the cap to its far face. `material_width`: undersized ligament. `mount_compactness`: oversized clamp plate.
   - `unload`: a rib or fixed pin in the straight unload path.
   - `pin_clearance` (laser ribs): a pin that intersects, sits within 5 mm of, or is not carried by a pad plate — pressed through it or standing on a face square to the pin, never a rib edge — cap tabs, cheeks and braces included; an elevated pad standing on fewer than two plates fails; a sliding/removable pin may seat on its bush.
   - `brace_merge` (laser ribs): parallel braces under 50 mm apart in plane and span — commonise them into one brace.
   - `interference` (laser ribs): plates overlapping each other or the part.
   - `flange_coverage` (checking): a sheet feature — flange, tab, wall, web — with no station, datum, alternative or user-quoted waiver, or a station off the part. An unchecked feature under 5 mm wide is unknown, not a blocker. The datum preview shows unchecked features red.

   After the checks pass:
   - [ ] Fixed every named blocker and reran; never show a concept with a blocker. Tell the user each blocker in plain words with its fix (e.g. "rib R3 stands alone — adding a cross brace"), never the check ID alone.
   - [ ] Presented the datum/support/clamp decisions and open items in plain words.
   - [ ] Showed Three.js inline when supported and invited feedback through the same comment pins and Copy comments as the datum review (window capture still works).
   - [ ] Sent the single `preview.html` alone (target 250,000 bytes, strictly below 1,000,000) — it is self-contained. Keep CAD files, PNGs and records private; send no concept ZIP; send `spec.json`/`project.json` only on a handoff request or at finalization.
   - [ ] Revised with `scripts/spec_patch.py spec.json '<small JSON patch>'` (include the new `revision`), not a spec rewrite; preserved IDs and tracked changes by them.
   - [ ] Regenerated with one `workflow.py revise spec.json project.json OUT [--build "<job build cmd>"] [--verify "<job verify cmd>"]` (build, checkpoint, concept, verify; one summary line, full output in `OUT/revise.log` and `OUT/result.json`).
   - [ ] **Stopped here.** No nesting, manufacturing export or final package during concept iteration.
6. **Finalize only on explicit user request:** “finalize”, “approve”, or “complete the package” authorizes package generation, **not engineering/fabrication approval**; “design a fixture”, invocation, upload or a screenshot revision alone does not. An initial explicit complete-package request may run end-to-end after survey/concept and validation. Record authorization and run the appropriate pipeline. For laser ribs, emit joined open single-stroke etch polylines (never DXF text) and use the configured shop-stock usable zone while preserving a practical rectangular remnant. Fix known defects; retain genuine unknowns.

   **Finalize delivers one zip, never loose files.** The design was approved in the HTML preview, so a passing `workflow.py finalize` packages it itself (`scripts/package_delivery.py`): the whole `DELIVERY` folder (DXF, assembly STEP, both PNGs, `JSON/`) plus `source/` with `spec.json`, `project.json` and the original source files, and a `BUILD-ORDER.txt` listing each etched fit-up number with its plate, part number, role and seat (from `measurements.cutting_audit.build_order`), as `OUT/<project_id>-<revision>.zip` with one top folder of the same name. Send only that zip (one file card); do not send the files individually or zip by hand. A run that needs review is not packaged; fix and rerun. Do not change any file after the build: the JSON records hash the exports, so a hand-edited STEP or DXF breaks validation — fix the spec or script and rebuild instead.

Persist `spec.json` plus `project.json` for a fresh chat/model; resume with `workflow.py resume spec.json project.json`, mapping relocated source paths. Validate source hashes, units, frame and version before reuse; changed source requires a fresh survey and invalidates evidence/approval. A byte-only change (re-export, identical solids by `source_geometry` fingerprint) is rebased automatically before authorization, as is a change confined to the `REF_` fixture solids in a surveyed STEP (a pin lengthened to press through its pad): where a pin locates the part is its `contacts` rows, so the datum ack survives it. Never relabel measurements. A handoff carries both records, the original sources and evidence, not only HTML.

## Shop standards (override any conflicting reference or example)

**Fasteners in printed bodies.** No brass/heat-set inserts anywhere. Every M5 into plastic (GH-201-B clamp base and body-to-base bolts) is a Ø4.2 × 12 deep hole, tapped M5 × 0.8 in the print. Clamp holes go at the measured CAD slot centres (`hardware/gh-201-b.json` → `mounting.hole_centres_canonical_mm`) through the clamp's `mount_transform`; pedestal = standard 50 × 60 footprint, top level with the clamped face. Ignore `printed-solid.md` / `make_gauge.py` insert text (Ø6.4).

**"Exclude studs/nuts/bolts" (or "ignore hardware").** Drop those bodies entirely: no `REF_` copies in the placed STEP, no clearance cuts, not checked. Assume the part is checked before hardware is fitted and say so once. Locating pins are sized to the **sheet hole** (e.g. Ø8 hole → Ø7.95 ground dowel, full sheet-thickness engagement, 0.5 mm lead chamfer), never to a nut/insert bore.

**Datums (checking).** Propose the largest flat face as A when the part's mass sits over it. Put the clamp force line on the centroid of the A pads (horseshoe pad around a hole if the centroid falls in one). Anti-rotation = one fixed edge stop at the point the user marks plus a 0.2 mm guard post at the far end; never two zero-clearance stops on one edge with a pin.

**Printed body (support-free continuous offset).** Build in exact OCP, not mesh Minkowski:
1. Flat base 10 mm; nest block under the datum face; Ø8 pads to Z0 at A points.
2. For every part face whose normals all point down (n_z < −0.02, flats **and bends**): planar → rebuild from its outer wire only (holes filled); offset 3 mm along its normal (`BRepOffsetAPI_MakeOffsetShape.PerformBySimple`); prism −Z to the base; fuse all with one fuzzy fuse.
3. Cut a 3 mm vertical relief band at each sheet-thickness side face (planar, |n_z| < 0.5, area < 250 mm²): xy convex hull of the face + its 3 mm offset, prism full height. Do not apply to the web or other large faces.
4. Add stop/guard posts (roles `Tertiary` and `Guard`), clamp pedestal with tapped holes, pin press bore (ream after print).
5. Keep the largest solid; heal (`ShapeFix_Wireframe` small edges + `ShapeFix_FixSmallFace` at 0.05 mm, `ShapeFix_Shape`); write STEP, reread, write again (settles tolerances so `step_roundtrip` < 0.001 mm³ and the STL closes).
6. Verify before concept: one valid solid; 9-ray gap = 3.000 mm at every station; nothing but datums within 3.0 mm of the part; no face with n_z < −0.05 above the base bottom (support-free).

**Pipeline gotchas.**
- After the rigid placement transform, re-sew the workpiece (`BRepBuilderAPI_Sewing` 1e-4 → solid → `ShapeFix_Shape`): placement can leave a BSpline bend face "unorientable" after STEP write (`solid_integrity` fail). Volume must not change.
- `pin_bearings` is a **top-level** list (`{"pin","point","axis"}`), not inside `pin_locators`.
- Station `direction`, `patch.u/v` and `point_mm` at full precision from the exact face (no rounding): the checker needs orthogonality ≤ 1e-7 and points ≤ 1e-4 mm on the face.
- A guard is not a contact: keep it out of `contacts`/`locating_groups` (store under `guards`), or `contacts` fails on its 0.2 mm gap.
- Put notes in `decisions`, never as extra fields on `clamps`/`contacts`: those fields are part of the datum digest and stale the datum review.

## Invariants and boundaries

Keep `cad_verified`, `fabrication_ready`, `fixture_calibrated`, and `inspection_validated` distinct. Unknown/fail/exception never becomes pass. A complete package is not a production release. Preserve construction, fastener and pin evidence; continuous loading/release, clamp motion, weld access, stiffness, calibration and inspection qualification are not proved by sample clearance tests.

Rib automation supports one thickness, horizontal seat and vertical seated polygonal ribs. Blocks use an explicit OCP/CAD workflow, not rib fabrication automation. Curved/oblique checking, complex printed forms and unsupported arrangements need explicit measured CAD work. Three.js meshes are approximate and non-authoritative; exact OCP CAD owns measurements/verification.

Setup: tell the user the CAD engine takes about a minute to install, then install `scripts/requirements.txt` in a task environment; if it cannot install (no network), say so plainly and stop — this skill needs exact CAD. Report any script error or failed check as one plain sentence plus the next action, never raw output. Tested OCP 7.8.1.1; supported 7.8.x. Run `python -m unittest discover -s tests -v` after code changes (without a prepared env: `uv run --no-project --python 3.12 --with-requirements scripts/requirements.txt python -m unittest discover -s tests`). Low-level builders remain for regression tests; use the workflow gate for real projects.
