---
name: design-weld-fixture-v8
description: Design and verify a welding fixture from STEP geometry or drawings, preferring suitable hole/slot locators and using practical bracing, manual pin release and 5 mm laser-cut tab-and-slot construction by default or blocks when requested, then deliver fabrication DXF, assembly STEP, review images, and compact JSON design records.
---

# Design Weld Fixture v8

Create a mechanically reasoned, reviewable welding-fixture concept from measured source geometry. Do not treat an attractive render as evidence that contacts, clearances, motion, or fabrication details are correct.

Read [the measured workflow](references/workflow.md) before designing or revising a fixture. Read [the output contract](references/output-contract.md) before starting the export stage.

## Inputs and source control

- Use an uploaded STEP file or accessible source path when available. Obtain dimensions from CAD or drawings, not screenshots.
- Record source identity, units, loose parts, welds, drawing datums, tolerances, loads, and assumptions.
- For a different or changed STEP file, perform a fresh survey. Reuse an earlier delivery's JSON only when its source hash and geometry revision match.
- Keep missing engineering information marked `unknown` or as an open item. Never invent dimensions, clamp force, tolerances, or test results.

## Construction mode

Use 5 mm flat laser-cut tab-and-slot construction by default. Read [laser-cut construction](references/laser-cut-construction.md) before building it.

If the user explicitly asks for blocks, machined blocks, or block construction, use [block construction](references/block-construction.md) instead. A project instruction can override any shop default.

## Practical defaults

- Select bracing for the load path, stiffness, fabrication and available space; neither crossing ribs nor one-sided T-braces are universally preferred. When a crossing rib restricts workpiece or handling clearance, consider relocating or shortening it, or use a one-sided T-brace extending into the available space. Preserve structural support and keep tabs/welds clear of the workpiece.
- Separate intended datum contact from non-locating structure. Set job-specific handling margins and check lateral movement and slight rocking as well as the intended loading path. Nominal non-interference alone is insufficient.
- For suitable manual release, start with a hand-removable dowel in a machined weldable-steel bush on a braced rib. Finish the bush bore after welding. Add captive mechanisms, handles or keys only when access, retention, orientation or repeatability needs them; see [construction and operation checks](references/construction-operation.md).

## Design sequence

1. **Survey:** identify bodies, loose pieces, thicknesses, holes, planar faces, bends, joints, welds, and relevant tolerances.
2. **Orient:** choose a stable, accessible loading and welding orientation; save a right-handed work frame and rigid transform.
3. **Locate:** choose the master part, shared assembly datums and loading stages using [assembly locating](references/assembly-locating.md). Prefer suitable existing holes and slots for secondary/tertiary location before adding edge stops; read [hole and slot locating](references/hole-slot-locating.md). Account for fixture and part-to-part constraints together; do not duplicate a complete fixed 3-2-1 arrangement for every loose sheet.
4. **Support and clamp:** put clamp forces into local supports, preserve access, and use actual purchased hardware geometry with explicit pose and clearance evidence.
5. **Build:** create manufacturable base, locators, supports, clamp mounts, joints, and retention suitable for the selected construction mode.
6. **Verify:** measure intended contact, unintended penetration, constraint independence, clamp opening, weld access, and workpiece loading/unloading.
7. **Export:** produce the exact files in the output contract, reopen DXF/STEP, verify the exported revision, and run the delivery validator.

Never advance on a failed or unknown result as if it passed. A documented exception can support a concept review but not fabrication approval.

## Construction and operation gates

Before detailing supports, read [construction and operation checks](references/construction-operation.md). Complete the rib structure, fastener access, and pin mechanisms in CAD before final review. Repair foreseeable design omissions within the task; do not use an `unknown` label as a substitute for designing the bush, brace, joint or usable grip.

The three required engineering checks are `rib_construction`, `fastener_access`, and `pin_mechanisms`. They need per-component evidence from reopened final CAD, including non-locating rib clearance and mode-specific pin operation. `construction_checks.py` enforces coverage, measured evidence structure and exported component identity; it does not calculate stiffness, infer interlocking joints or simulate tool/pin motion. Missing evidence remains unknown; a known obstruction or omitted required component is a failure. Neither can confer fabrication readiness.

## GH-201-B toggle clamp

GH-201-B is the preferred available manual hold-down clamp when its reach, capacity, adjustment, and clearance suit the job. Before using it, read [clamping and placement](references/clamping.md) and [the GH-201-B record](references/hardware/gh-201-b.json).

Default the GH-201-B mounting face to the same level as its workpiece clamping surface, measured along the clamp normal. Derive cap and cheek heights from that surface and the plate thickness. Verify both faces on the exported CAD with `mounting_height`; matching levels does not verify closed-and-locked operation. Different heights require the measured exception in [clamping and placement](references/clamping.md).

Place the clamp by aligning its closed spindle axis to a supported workpiece contact. Transform its stored mounting-hole centres onto the clamp-support plate. The fixture plate receives four nominal 4.2 mm laser-cut tap-drill holes for M5 x 0.8 tapping. Keep the clamp's 90 kg rating identified as holding capacity, not applied clamping force.

Bundle and use `assets/hardware/GH-201-B.step` in delivered assemblies and review images. The exporter inserts all 14 components with one rigid mounting transform; do not replace them with blocks or rebuild the handle/arm/pad separately. A user-requested schematic is a separate explicitly labelled exception workflow, not the default builder output.

The supplied CAD is saved with a tilted spindle, not a verified closed operating pose. Its mounting slots also differ from the old drawing values; use the measured CAD centres in the hardware record and keep physical variant confirmation open. A nominal reach does not establish the imported pad contact. The automatic import preserves the supplied pose; verify a closed pose through an explicit CAD workflow before claiming seating or operating clearance. Never fake closure by rotating the whole mounted clamp or moving only its pad.

Size the mounting platform from the actual base, pilot holes, structural ligaments and tool access. Reconsider cap tabs, cheek spacing and bracing before enlarging it; record the reason and compact alternative for a large platform. See [clamping and placement](references/clamping.md).

## Tool boundaries

Use a CAD kernel or other available geometry tools for measurement, analytic solids, DXF, STEP, and intersection checks. Blender is optional for scene assembly or pictures; it is not required and a `.blend` file is not a deliverable.

Use scripts for transforms, hole placement, distances, intersections, export comparisons, and deterministic checks. Inspect tool and application results rather than relying only on process exit status.

## Laser-cut build scripts

For laser-cut construction, write the design as one spec ([spec format](references/spec-format.md)) and run the bundled pipeline instead of hand-writing geometry code. Start from the [worked example](examples/flat-plate/make_example.py).

Setup once: create a virtual environment and install `scripts/requirements.txt`. The tested kernel is OCP 7.8.1.1; the supported range is 7.8.x.

Run: `.venv/bin/python scripts/build.py spec.json OUT`. Diagnostic flags `--no-step`, `--no-insertion`, and `--no-render` leave the corresponding evidence or files unresolved; they never waive requirements.

| Step | Script | Result |
|---|---|---|
| Tabs and slots | `tabs_slots.py` | Two tabs per seated plate, searched per part number; slots in the seat plate; feet widened only below foot height |
| Clamp mounts | `clamp_mount.py` | Hardware hole pattern placed from contact, normal and arm direction; hole fit, ligament, base support, spindle extension |
| Mount height | `mount_height.py` | Actual mounting and workpiece face heights, signed difference, scoped operating-height exceptions |
| Mount compactness | `mount_compactness.py` | Hardware-derived minimum envelope, platform ratio and explained joint/access extensions |
| Assembly locating | `assembly_locating.py` | Same-side secondary stops, coupled staged rank, redundant fixed constraints and mating-face checks |
| Purchased hardware | `hardware_geometry.py` | Hash-checked 14-component STEP, measured mounting frame and explicit saved-pose limitation |
| Material width | `audit_width.py` | Contact fingers, tab necks, joint ligaments and edge-pair screening against `min_width_mm` |
| Nest and DXF | `nest_dxf.py` | First successful configured sheet in area order, `CUT`/`ETCH`/`STOCK_REFERENCE`, reopened and compared |
| STEP | `export_step.py` | Named plates, `Part_*`/`REF_*` workpiece references and automatically placed `HW_*` clamp components |
| CAD checks | `verify.py` | Contact gaps, interference, constraint rank, straight-line insertion in assembly order |
| Construction evidence | `construction_checks.py` | Required rib/access/pin evidence, per-component coverage, pin travel and exported component identities; explicit CAD inspection still required |

`build.py` writes the DXF, STEP, two CAD-derived PNGs and four JSON records to `OUT/DELIVERY/`, with working reports under `OUT/work/`. Read `geometry_status`, `overall_status`, `delivery_status`, and `fabrication_ready` in `verification.json`. Exit 0 means a complete review package; it may still have unknown engineering checks. Exit 1 means a failed check/build; exit 2 means an incomplete delivery. Missing checks and sampled motion cannot silently become passed verification.

The saved records retain the input spec, final profiles/frames, source hashes, supports, retention proposals, and detailed measurements. Validate hashes and map source paths before resuming. Provide original `source_files` and the rigid `source_to_fixture` transform; the placed STEP alone does not document the survey.

Prefer standard round dowels with ground relieved ends for pin locating. Keep workpiece locating clearance separate from the dowel mounting fit, and check the full assembly release path. Use the explicit pin-analysis and manufacturing-stage workflow in [hole and slot locating](references/hole-slot-locating.md); the planar-contact builder does not automatically generate or audit pin locators.

You still decide datums, contacts, rib outlines and lands, cross-joint slots, cap tab-and-slot joints, clamp position/support, and retention. Engineering checks remain explicitly unknown until measured evidence is supplied through `engineering_checks` in the spec. Read the evidence rules in [spec format](references/spec-format.md). Change the responsible spec feature and rebuild; do not relabel old measurements or edit generated geometry.

### Supported automation and fallback

The bundled builder supports flat polygonal plates of one thickness, one horizontal XY seat, and vertical seated ribs. Planar intended workpiece faces use geometric descriptors; curved faces need separate CAD verification. STEP reading traverses nested assemblies with occurrence placements, but preparation must still assign unique `Part_*` and `REF_*` leaf names and verify imported placements. Non-unique names are rejected rather than merged.

Nesting searches configured single-sheet sizes using a rectangle-packing heuristic. It does not prove global optimality. For angled/multiple seats, mixed thicknesses, curved contact verification, or multi-sheet layouts, use an explicit CAD/CAM workflow preserving the same evidence and delivery contract; mark unsupported automated checks unknown or a documented exception. Do not force geometry into the example's assumptions.

Fixture insertion samples concern fixture construction only. They are screening evidence and cannot establish a continuous path. Workpiece loading/unloading, clamp motion, and weld access require their own checks. Actual clamp solids remain in their recorded pose; their presence is not proof of closed seating, linkage motion or hardware clearance. Missing assembly plans remain unknown; opposing secondary stops and unexplained large mounts fail the appropriate screen.

Run `python -m unittest discover -s tests -v` after changing scripts. The worked example uses a compact 60 x 64 mm welded cap, two base-tabbed support cheeks, actual bundled clamp geometry, an explicit single-part locating plan, and both review views. Cap placement, retention and other engineering checks intentionally remain unknown; choose dimensions from the job rather than copying this example.

## Completion

Deliver one DXF, one assembly STEP, two review PNGs, and the four JSON records required by [the output contract](references/output-contract.md). Do not add HTML, spreadsheets, CSV schedules, `.blend` files, or many separate audit files unless the user requests them.

Report what is complete, summarize measured checks, and list material open decisions. Do not claim production readiness while datums, tolerances, clamp suitability, fastening, weld access, distortion, or trial validation remain unresolved.
