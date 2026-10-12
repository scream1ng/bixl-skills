# Bending

- Covers press-brake bending of sheet-metal parts generally (legs, returns, offsets, channels, boxes), not only simple flanges. Inspect what forming creates/changes. Use the largest suitable main planar **outside face** as reference; establish actual CAD faces and practical seating.
- A formed height (leg, return, offset or flange) is the perpendicular distance from that outside face to the physical edge/contact corner, including material thickness. Apply the same concept at non-90° bends; do not substitute sloping leg length, inside height or a theoretical sharp bend intersection. Bend-to-bend and bend-to-edge distances use physical outside faces too.
- Omit numeric 90° callouts. State other nominal angles from CAD/drawing; require a separate angular tolerance. Never apply millimetre tolerances to angles.
- Choose real vernier contacts and verify reach, seating, clearance from bend radii and access. Outside width uses outside face to outside face. Specify another gauge when access is unsuitable.
- Default tolerance: ±0.5 mm, clinch-fastener holes ±0.2 mm (see SKILL.md defaults). Angular, parallelism and visual criteria need their own specification.
- Do not repeat upstream hole diameters, blank/perimeter or unchanged length. Include a length only if forming changes it and there is a relevant measurement method.
- Post-form feature positions need functional relevance and a real method. A hole centre is not a direct vernier contact.
- Include parallelism, twist or bend-condition checks when the drawing, part function or controlled inspection specification requires them. Keep unrelated/pending checks in review notes rather than automatically adding generic operator rows.
- Prefer Vernier for formed distances, with direct outside contacts verified for reach. Use Protractor for surface-to-surface angles; short straight lands still need compatible protractor contacts clear of radii. Nominal angles display to one decimal. Height gauges are not in the included operator equipment profile; require confirmed availability before specifying one.

Use `template.xlsx` and `layout.json`. The sample 35/100 mm dimensions and its number of flanges are not defaults.
