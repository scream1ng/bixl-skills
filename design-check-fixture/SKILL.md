---
name: design-check-fixture
description: Generate a checking-fixture review package from an uploaded STEP model or drawing using the Design Weld Fixture v8 CAD pipeline with checking geometry on top. Support 5 mm laser-cut ribs or a solid 3D-printed plastic body, a 3 mm nominal flange gap and 2.5/3.5 mm GO/NO-GO gauges; deliver verified exports, review images and JSON records.
---

# Design Check Fixture

Use the bundled Design Weld Fixture v8 fabrication, hardware, export and verification pipeline, extended with STEP surveying, checking surfaces, gauge checks and printed-body construction. Work from measured geometry; do not replace the pipeline with newly invented per-job exporters or treat a rendered fixture as verified.

## Fresh-chat default: uploaded STEP to delivery

When the user drops a STEP file and invokes this skill, perform the complete workflow without asking for a spec JSON or repeating preferences already defined here. **Create the measured design specification yourself.** Do not stop at a proposal, a survey or script instructions when a fixture is requested. Missing physical calibration or shop process evidence can remain open in a complete review package.

1. Read [STEP-first workflow](references/step-first.md), [measured workflow](references/workflow.md) and [inspection logic](references/inspection.md).
2. Run `python scripts/survey_step.py INPUT.step WORK/survey`. Inspect exact geometry and survey output, choose the work frame, and resurvey the original with `--transform` if needed. Preserve the source hash, occurrence identities and placements. Do not assume a planar face is a flange or a cylinder is a hole.
3. Select drawing datums or explicitly proposed functional datums. Inventory every flange, choose checking stations and define loading/release. Before fixing rib profiles, apply the mandatory [restraint, access and profile review](references/practical-review.md): map primary supports to hold-downs, route full gauges and hands with the part restrained, and justify profile reliefs. Build the job's spec using [inherited spec format](references/spec-format.md) plus [checking build schema](references/checking-build.md). Respect actual geometry; never scale the example fixture to the new bounding box.
4. Use `laser_rib` by default and read [laser ribs](references/laser-ribs.md) and [v8 laser construction](references/laser-cut-construction.md). When the user requests a solid printed fixture, use `printed_solid` and read [printed construction](references/printed-solid.md) and [printed-body schema](references/printed-body-spec.md).
5. Run `python scripts/build_check.py WORK/spec.json WORK/build`. Inspect actual reports and CAD images; revise the responsible geometry/spec and rebuild until foreseeable defects are fixed. Run `python scripts/validate_delivery.py WORK/build/DELIVERY` before delivery. Exit 0 means a complete concept package, not physical production approval.
6. Deliver the assembly STEP, mode-appropriate fabrication/print files, two CAD review images and four JSON records. Keep supporting scripts and analysis in work storage. Follow [verification and delivery](references/verification-delivery.md).

Install `scripts/requirements.txt` in a task environment if needed. The inherited kernel target is OCP 7.8.x; record the actual runtime. For drawings without solid CAD, construct geometry from provided dimensions and keep missing dimensions explicit; do not invent a manufacturable part from a picture.

## Fixed shop defaults

- **3.0 mm nominal checking gap; 2.5 mm GO must enter; 3.5 mm NO-GO must not enter**, using light hand pressure without flange deflection. Apply this on STEP-only work and label `shop_standard`; no drawing is needed to establish these already-specified gauge sizes.
- Flag conflicting customer/drawing tolerances. Preserve the shop check while distinguishing it from drawing conformity; add an appropriate separate measurement when necessary. Do not silently substitute gauge sizes.
- Datum pads touch the part. Pin fits and general handling clearances are separate from the 3 mm gap. Checking surfaces must not locate or force the inspected flange into shape.
- Default to 5 mm flat laser-cut tab-and-slot construction. Keep two separated base tabs, actual mating slots, appropriate transverse bracing, compact supported clamp mounts and accessible fasteners. Crossing ribs and one-sided T-braces are options selected by space and loads, not universal preferences.
- Prefer suitable existing holes/slots for secondary and tertiary location after drawing datums. Prefer standard round dowels with ground relieved/diamond ends where suitable. Use simple hand-removable dowels in real bushes where release is needed; verify relief orientation, grip and withdrawal.
- Reuse actual GH-201-B hardware, with gentle datum seating and no distortion of measured flanges. Its supplied STEP is **not a verified closed pose**. A mounting-height pass does not prove closure, force or motion.
- Preserve the full 3-2-1 locating and seating discipline from v8. A six-DOF rank pass does not prove the part stays seated during gauging. Provide required toggle hold-downs over or near supported primary seating regions; justify any gravity-only region explicitly. Do not impose one clamp per support universally.
- Require usable access for both gauge ends, stems, handles and the operator's hand at every station in the inspection restraint state. A 3 mm gap or short working-tip fit alone is insufficient. Fix known blocked routes before delivery; retain genuinely unresolved access as unknown, never pass.
- Keep rib transitions simple. Retain a notch or relief only for an identified joint, manufacturing, clearance or access function; do not add a narrow transition slit automatically. Review the final STEP and cut profiles, including generated offsets and Boolean cuts.

Read [locating and hardware](references/locating-hardware.md), [hole/slot locating](references/hole-slot-locating.md), [assembly locating](references/assembly-locating.md), [construction/operation checks](references/construction-operation.md) and [clamp placement](references/clamping.md) as those features are designed. The [hardware record](references/hardware/gh-201-b.json) and full original `assets/hardware/GH-201-B.step` are bundled.

## Scripts: inherited foundation plus checking layer

| Layer | Reusable scripts |
|---|---|
| Source survey | `survey_step.py`: nested occurrences, unit normalization, named placed STEP and measured face/edge evidence |
| V8 construction | `tabs_slots.py`, `clamp_mount.py`, `mount_height.py`, `mount_compactness.py`, `audit_width.py` |
| V8 location and verification | `assembly_locating.py`, `construction_checks.py`, `verify.py`, `hardware_geometry.py` |
| V8 exports | `nest_dxf.py`, `export_step.py`, `render_review.py`, `records.py`, `validate_base_delivery.py` |
| Checking construction | `checking_offsets.py`: clips rib stock at exact normal offset planes; `printed_body.py`: explicit solid features/offset pockets and reopened STL verification |
| Checking audit | `check_gap_plan.py`, `checking_geometry.py`: plan coverage, measured finite planar gap samples, nominal GO/NO-GO working-end fit, optional sampled tool approaches |
| Practical review evidence | `checking_evidence.py`: current attached evidence, complete primary-support/clamp mapping, full gauge/hand route records and final profile review; record completeness is not independent proof of the engineering analysis |
| Delivery orchestration | `build_check.py` wraps the v8 `build.py` or `build_printed.py`, adds checking records and CAD section insets through `checking_review.py`, and validates with `validate_delivery.py` |

Use `build_check.py` for user checking-fixture deliveries. `build.py` is the retained lower-level steel fabrication pipeline and alone does not create a complete checking-fixture delivery. JSON-plan validation is not CAD verification.

The model still decides datums, flange identity, contacts, rib stock/joints, station placement and real operating details from the source. This is the same measured design responsibility as v8. The scripts supply reusable geometry/export/checking operations, not a universal automatic fixture designer.

## Boundaries and completion

The steel backend retains v8's one-thickness, horizontal-base/vertical-seated-rib limitations. Explicit offset-plane rib generation requires the checking normal in the rib plane; oblique/curved lands need an explicit kernel extension and measured evidence. Printed-body primitives cover boxes, cylinders and oriented planar offset pockets; more complex shapes can be supplied as finished analytic STEP bodies. Do not force unsupported geometry into an example's assumptions.

Checking audit passes cover finite planar samples and nominal working-gauge envelopes only. Whole-flange coverage, full tool/hand access, continuous release, seating distortion and error budgets remain engineering checks. The printed backend reports unsupported inherited checks as unknown rather than pretending metal-specific automation applies. Resolve appropriate checks with explicit CAD/engineering evidence.

Retain `cad_verified`, `fabrication_ready`, `fixture_calibrated` and `inspection_validated` separately. A complete review package can have unresolved readiness. No Blender file is required. Validate changed scripts with the bundled tests and run both `examples/checking-rib/spec.json` and `examples/checking-printed/spec.json` through `build_check.py`; examples are software test coupons, not approved fixtures or dimensions to copy.

Consult [research basis](references/research-basis.md) for background; customer-specific standards are not automatically this shop's requirements.
