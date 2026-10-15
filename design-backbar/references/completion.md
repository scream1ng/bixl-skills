# Exported CAD completion

## Inventory and evidence

Before implementation, list **every agreed CAD change** from the active job. Preserve its ID, description, expected geometry and acceptance criteria through revisions. Set `reviewed: true` only after comparing this list with the conversation. An empty list is valid only when no physical corrections were requested; generated trims and programming tabs are added automatically.

For example, a request for common bends uses:

```json
{"reviewed":true,"changes":[
  {"id":"C1","kind":"common_bend","bends":[1,4],"description":"B1 and B4 common in CAD"},
  {"id":"C2","kind":"common_bend","bends":[2,3],"description":"Correct B3 to the B2 bend axis"}
]}
```

Run `backbar.py corrected.step OUT --sequence 1+4,2+3,5 --requirements requirements.json`; add `--package` only when requested. CLI grouping never performs the correction. The inventory describes required results, not an assertion that they are done.

For a custom extension, reshape, hole relocation or other physical edit, implement a measurement routine against the **reopened exported STEP**, then attach numerical evidence to the inventory item:

```json
{"id":"C3","kind":"extension","description":"Extend the agreed local edge by 0.3 mm",
 "step_sha256":"SHA256_OF_THE_EXACT_EXPORTED_STEP",
 "before":{"extension_mm":0},
 "checks":[{"name":"local extension","unit":"mm","min":0.299,"max":0.301,"measured":0.300}]}
```

Choose criteria from the agreed design before seeing results. Include all material consequences and protected features, such as hole position/diameter, radius and thickness; do not reduce a reshape to a volume-only check. Record coordinate frame and feature references alongside measurements. A plain `verified: true` is not accepted. Do not enter intended dimensions as measured values or reuse evidence from another export. The generic checker evaluates supplied evidence; it cannot invent the correct feature measurement for an arbitrary CAD edit.

The CLI independently checks generated trim-region removal and tab-volume retention after STEP readback. For a custom pipeline, supply equivalent or stronger feature-specific checks and preserve original/physical/programming geometry separately.

## Common-bend readback

`completion.verify_common_step(step_path, groups, bend_map=None, expected_centers=None, line_tolerance=.001)` reopens one formed solid and unfolds it afresh. It checks 0.001 mm line alignment, known rotations, analytic formed cylinder axes (0.001 mm / 0.001°), inner radii (0.001 mm) and fold sense. It returns measured evidence tied to the STEP SHA-256. It never moves geometry or widens limits. A tighter `line_tolerance` is retained through packaging.

Prefer `expected_centers` from the ordered input bends' `formed_center` values to match identities uniquely after export. The CLI supplies these automatically for formed-only input. Supplied-flat numbering has no automatic formed reference: explicitly establish the corresponding formed bend identities in a custom workflow rather than assuming matching order. In standalone calls, `bend_map` lists detected exported IDs in user-number order; omit it only after confirming that order matches. Do not infer mapping from operation position.

The conservative analytic check does not support every spline bend or pair whose axes move apart in the final formed state due to later bends. Such a result is unresolved, not automatically a bad design. Implement an independent staged-geometry verifier with the same fixed criteria, feature mapping and exported-byte binding before claiming completion; do not skip checks, alter the tolerance, or hand-edit the completion status. Shop collision and reach checks remain separate.

For an actual correction, preserve before measurements and verify that the final CAD satisfies the target, including any consequential hole-centre movement. If geometry was already common, label it already common rather than claiming an edit.

## Seal and package

After regenerating and inspecting all affected outputs, call:

```python
from completion import seal_delivery
from package_delivery import package_run
seal_delivery(outdir, report, requirements, expected_centers=ordered_centers)
# Save the updated report as OUT/report.json before packaging.
package_run(outdir, zip_path)
```

`report` must include `step`, `deliverables`, `operations` and STEP `verification`; custom workflows may supply `export_bend_map`. The completion record contains the entire agreed-change inventory, measured common-bend results, unresolved items and hashes of the exact STEP/report-preview/DXF files. Hashes detect changed files; they do not establish that old previews were regenerated. Generate and visually inspect them from the corrected geometry before sealing.

`package_run` refuses absent/incomplete evidence, missing common requests, numerical failures and modified files. It remeasures common geometry when packaging. If any item fails, fix it and regenerate affected outputs. Do not omit it from the inventory, drop a requested operation, change criteria or reseal stale drawings to force a pass.

Only when the user explicitly requests an interim review, call `package_run(outdir, '...INCOMPLETE....zip', interim=True)`. Its README states unresolved work. Never describe that archive as completed or manufacturing-verified.
