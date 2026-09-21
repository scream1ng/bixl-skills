# Construction and operation checks (v8)

Read before detailing supports and again when reviewing final CAD. These checks add fabrication and operation evidence to the existing locating, collision and strength checks; they do not replace them.

## Rib structure and dry assembly

Review every plate, identifying base plates and other inapplicable members explicitly. For every upright, clamp mount and pin carrier:

- Trace load into the base, including sideways bending and twisting. Prefer two spaced backing ribs under broad clamp mounts with offset loading; one sufficiently supported arrangement or a block may be appropriate when justified. Two ribs are not a universal count requirement.
- Select the bracing arrangement from load path, stiffness and available space. Use a crossing member where it fits and provides suitable support. When space or handling clearance is limited, consider a one-sided T-brace into the available space; it is not a universal preference. For that joint, fit side tabs into the locator rib and keep their ends and welds flush at the opposite face. Check the complete rib, not just the brace tip, after moving or widening it.
- Cross-support every upright with perpendicular members (`cross_support` check fails a lone rib). Model actual complementary cross-lap slots or tab-and-slot connections between the members and the supported cap, plus the required base tabs. Adjacent butt faces do not constitute a dry-fit interlock.
- Check actual intersections, engagement, ligaments, insertion order and tool/weld access in DXF and STEP. A joint record alone does not create cut geometry. Fix the responsible spec profile and rebuild.
- Describe how the dry assembly will be held square while tacking. Slot clearance permits rocking; two base tabs are not a substitute for transverse bracing. Check both the temporary fabrication state and the retained finished state.
- Identify permanent retention, weld sequence and finishing after weld distortion. Keep unknown forces or physical trial results open rather than asserting strength from plate thickness.

Cross-support is structural; it must not introduce unintended workpiece datum contacts or block weld access/removal. A low, broad upright can use a justified alternative support arrangement, with measured dimensions and load reasoning. Do not exempt it silently.

## Handling clearance

- Identify intentional support/datum contact patches explicitly. Check the rest of the rib, tabs, weld allowance and adjacent hardware as non-locating structure. A plate carrying one datum is not exempt from clearance checks elsewhere.
- Establish a job-specific allowance from part variation, weld distortion, burrs/spatter and manual approach. Record the chosen nominal clearance, lateral offsets, rocking angles/pivots and applicable loading stages. Values from the WAG example are not universal limits or standards.
- Check each loose preassembly and the welded assembly in the real sequence: release clamps and withdraw obstructing pins in an order that keeps the parts supported and avoids binding, clear fixed pins and datum lands, then allow free handling. Do not simulate arbitrary sideways motion while a locating pin is still engaged and call that normal unloading.
- Screen lateral movement and slight rocking around the expected path where applicable. Measure the minimum clearance as well as penetration. Retain exact body/face coverage, transforms and acceptance criteria; justify constrained stages or inapplicable motions.
- A collision-free straight lift of nominal CAD is insufficient handling evidence. Local brace checks cannot pass the whole loading/unloading check when clamps, other parts, tolerance effects or portions of the path remain unverified. Samples are screening, not a continuous-path proof.
- Fix a known shortfall by relocating, shortening or making the brace one-sided while preserving datum contacts, structural ligaments, joints and access. Do not merely label a known obstruction unknown or move the datum to hide it.

## Clamp and fastener access

For every mounting hole, check screw head/washer seating, actual screw length and protruding end, driver/socket/hand access, drilling/tapping breakthrough and maintenance removal. Check ribs, tabs, welds and adjacent parts on both sides of the mounting plate. A hole inside the plate outline is not proof that it can be drilled, tapped or used.

Model actual fasteners or conservative clearance envelopes in the project analysis. Record dimensions, tool approach, assembly stage and minimum clearances. Tools need not remain in the delivered assembly, but the checked geometry and evidence must be retained. Tapping before assembly can be legitimate; it does not waive final screw clearance or tightening access. Review bush retainers and other fixture fasteners as well as clamp screws; the automatic inventory currently covers clamp mounting holes only.

Position backing ribs outside these envelopes. Reposition brace spacing and joints before growing the platform. Do not add unnecessary machining clearance to the base when a simple laser-cut layout change solves the access problem.

## Choose the simplest suitable pin operation

Distinguish `fixed`, `sliding` (captive) and `removable` pins. Prefer common removal directions and preserve explicit user choices.

For suitable manual release, start with one braced carrier rib, a machined weldable-steel bush and a hand-removable dowel. Provide perpendicular support appropriate to the loading; two backing gussets are a useful starting arrangement, not a universal count. Align and weld the bush, cool it, then finish its bore to suit the actual dowel. Distinguish the carrier opening, bush mounting fit, pin sliding fit and workpiece locating fit. Use a replaceable bush when wear, material or servicing warrants it.

All moving pins need measured bush ID/OD/length, supported mounting, projection, lead-in, locating engagement, withdrawal, grip access, release sequence and retention/orientation assessment. Choose dimensions from this job. A bare carrier hole does not substitute for a bush.

- **Hand-removable:** an exposed dowel tail can provide the grip. Measure accessible grip length and hand clearance through the operating interval. Define insertion/withdrawal references (for example witness marks), the method that keeps the pin seated during welding, and handling of the withdrawn pin. For directional relief, define repeatable alignment and check its adequacy; scribed marks can suit a manually aligned application. Require a key or other mechanical control when the operating requirement demands assured orientation. Do not add a handle, tether, guide cap, locknut or captive carriage without a practical reason.
- **Captive sliding:** model its real handle, retention, positive travel stops and anti-rotation feature when directional relief requires one. Record why this arrangement is needed, such as inaccessible grip, repeated stroke control, loss prevention or assured orientation.
- **Fixed:** qualify mounting fit, projection, retention and any relieved-tip orientation. A guide bush is not automatically required.

Check withdrawal with the workpiece present and guidance until the locating tip disengages. For a detachable pin, separately check free extraction after disengagement; final free removal need not retain bush engagement. Then check the complete part-removal sequence with clamps in their verified open state. Include grip/hand access and intermediate poses, with honest limits on sampled motion.

Model named solids for the actual design. An integral grip or stop may share the pin solid only when that physical feature and its access are identified and measured. Manual witness marks are manufacturing annotations, not imaginary hardware. Record real purchased/custom components, material and post-weld finishing in hardware.json. Missing fit, force or operating trials remain open; simplicity does not waive verification.

## Evidence contract and automation boundary

`scripts/records.py` requires `rib_construction`, `fastener_access` and `pin_mechanisms`. Missing checks become unknown and prevent fabrication readiness. Known deficient construction is fail, not merely unknown. A concept review may be delivered with explicit open items, but complete foreseeable detailing within the authorized design task before delivery.

Use the standard engineering-check envelope: current `geometry_fingerprint`, `status`, `scope`, `limit`, `units`, `next_action`, hash-checked evidence files and `measured`. For these three checks, `measured` contains:

```json
{"basis":"reopened_step", "items":[]}
```

An empty inventory also needs `not_applicable_reason` describing the actual inspected design. Each item has `id` and `component_names` (an array of exact exported solid names). Reference current CAD faces/features and measured values in the evidence report. Passing evidence is a measured report, not a repeated requirement.

Each applicable item has `findings`, mapping the section names below to objects with:

```json
{"status":"pass", "method":"Describe the actual CAD inspection/calculation and stage",
 "measurements":{"description":"Actual measurements or geometric observations"},
 "acceptance":{"description":"Job-specific acceptance criteria"}}
```

Use numeric values for dimensional checks, explicit contact/joint/feature identities for geometric observations, and state units. Failed or unresolved findings cannot be summarized as pass. A valid evidence structure does not prove the measurements were performed.

| Gate | Inventory and per-item data | Required findings |
|---|---|---|
| `rib_construction` | One item per `plates[].name`; `applicable:true` for seated/nonhorizontal plates and clamp mounts. Other plates may have `applicable:false` with a reason. Include the reviewed plate, braces and connected components in `component_names`. | `load_path`, `bracing`, `joints`, `dry_fit`, `fabrication_sequence`, `handling_clearance` |
| `fastener_access` | One item per clamp `tag`, including its mount plate in `component_names`. Supply `holes`, one entry per mounting hole, each with `id`, `stage` and findings. GH-201-B uses IDs H1–H4 in hardware-record order; other hardware declares `mounting_hole_ids` on the clamp. Include hole centres in measurements. | Per hole: `screw_end`, `installation`, `tightening`, `drilling`, `tapping`, `maintenance` |
| `pin_mechanisms` | One item per `pin_locators[].id`; include mechanism-role mapping described below. | All pins: `fits`, `retention`, `relief_orientation`, `release`. Moving pins also: `guidance`, `stroke`, `operator_access` |

Declare every locator pin in the top-level input spec inventory:

```json
{"pin_locators":[{"id":"P1", "shape_name":"REF_PIN_P1",
 "mode":"sliding", "orientation_sensitive":true}]}
```

`mode` is `fixed`, `sliding` or `removable`. The inventory does not generate geometry or locating rank. Use `REF_PIN_` only for actual locating-pin solids, and different prefixes such as `REF_BUSH_` for guide bushes. Old ad-hoc pin records must be mapped to this inventory before a v8 pass.

Each pin evidence item contains `mechanism`, mapping each actual role to a nonempty array of exported CAD names, also included in `component_names`:

| Mode | Required CAD roles |
|---|---|
| `fixed` | `pin`, `carrier`, `retention` (may be the measured press-fit feature) |
| `removable` | `pin`, `carrier`, `bush`, `grip` (may be the measured exposed dowel tail) |
| `sliding` | `pin`, `carrier`, `bush`, `handle`, `retention`, `travel_stop`; `anti_rotation` when orientation-sensitive |

Additional roles are optional but, when supplied, their solids must exist. All modes still need `fits`, `retention`, `relief_orientation` and `release` findings. Moving modes additionally need `guidance`, `stroke` and `operator_access` findings. A manual method may satisfy a removable pin's retention/orientation finding only with application-specific evidence; the mode alone grants no pass.

Moving-pin `motion_mm` contains numeric `withdrawal`, `required_withdrawal`, `minimum_guide_engagement`, `required_guide_engagement`. Define the interval before the locating tip disengages for a detachable pin; do not compare its final fully removed position to required bush engagement. Actual values must meet positive job-specific requirements. For `removable`, also supply measured `grip_length` and positive `required_grip_length`, and a `manual_operation` object with nonempty `travel_reference`, `retention`, and (when orientation-sensitive) `relief_orientation` descriptions. These descriptions accompany the measured findings; they do not prove them.

For example, a real exposed pin tail can use `"grip": ["REF_PIN_P1"]`; identify its length, accessible faces and checked hand envelope in `operator_access`. Do not map that same solid to a fictional bush or handle.

V8 adds `handling_clearance` to every applicable rib's findings. Record intentional contact exclusions, measured non-locating clearance, the chosen allowance and scoped handling motion. Existing v7 passes must be reassessed against these findings and mode-specific evidence; schema version remains 1.2.

`construction_checks.py` verifies required coverage, evidence fields, fingerprint, pin travel/engagement comparisons and actual exported component names. The build downgrades incomplete pass evidence to unknown; the delivery validator rejects invalid pass claims. Both still require the existing hash-checked engineering evidence. The script does **not** infer stiffness, create joints/bushes, measure tool envelopes, confirm a named part is physically the claimed feature, or simulate a continuous release path. Supply that evidence through explicit CAD/engineering work. Never equate a schema pass with manufacturing verification.
