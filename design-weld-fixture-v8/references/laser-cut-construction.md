# Default 5 mm laser-cut construction

Use this mode unless the user explicitly requests block construction or another process.

## Shop defaults

- All custom fixture plates are flat and laser-cut from nominal 5 mm sheet.
- Use the bundled actual purchased-clamp STEP and standard fasteners; do not create custom machined blocks or bent fixture parts unless requested.
- Prefer broad, predominantly rectangular ribs with direct load paths and few unnecessary outline turns.
- Maintain at least 10 mm nominal in-plane material at structural necks, shoulders, contact fingers, webs, tab necks, and material beside or behind slots. Account for kerf and process capability before claiming a finished minimum.
- Choose crossing ribs or one-sided T-braces to suit structural support and available space. A one-sided T-brace is an option when space or handling clearance limits a crossing member, not the default arrangement. If selected, put tabs into matching slots in the locator rib and keep tab ends/welds flush on the workpiece side. Preserve structural ligaments and datum contacts, and check handling clearance.
- Cross-support tall locating and clamp-support uprights with modeled interlocking perpendicular members. Two base tabs alone do not establish dry-fit squareness or resistance to sideways bending. Apply [construction and operation checks](construction-operation.md), including every upright and clamp mount.
- Consolidate compatible coplanar parts and reuse genuinely identical profiles.
- Give every upright seated on the base two separated integral tabs and matching through-slots. This includes locator ribs, braces, and clamp-support cheeks.
- Use etched part IDs and station marks for assembly guidance. Etching does not replace physical location or retention.

## Profile development

1. Start each rib from a broad rectangle.
2. Add only required contact shoulders, mating joints, weld/tool clearances, loading clearances, and tabs.
3. Identify the purpose of every non-rectangular feature. Remove decorative tapers, thin slivers, acute V cuts, and unexplained notches.
4. Measure the final profile after all cuts and unions. A bounding box, corner spacing, or zero CAD interference does not establish minimum material width.
5. If a required feature leaves less than 10 mm material, widen or reposition the support, change the joint, or revise the locating approach. Do not silently waive the requirement.

## Tabs, slots, and assembly

- Use two separated tabs per base-seated upright to control dry-fit rotation.
- Make tab engagement suit the measured base thickness and underside clearance.
- Size slots using measured stock, kerf, fit allowance, and a physical coupon. Do not assume zero clearance.
- Preserve at least 10 mm at tab necks and between cutouts after process allowance.
- Widen short feet with simple rectangular material before reducing tab count.
- Derive complementary cross-slots from actual crossing angles and stock thickness.
- Record which member installs first and check intermediate insertion poses. Final-position fit alone does not establish assemblability.
- Give supported clamp and pin-carrier caps matching tab-and-slot joints with at least two separated locating tabs per cap. Add these joints explicitly: base-tab automation does not create cap joints. Verify tab engagement, slot ligaments and that tab ends/welds do not stand proud of a clamp mounting face. Reposition the joints before enlarging the cap.
- Tabs locate parts for assembly but do not by themselves establish vertical retention, fixture strength, or weld adequacy.

## Clamp mounting holes

For the standard GH-201-B clamp, place the four mounting positions from its hardware record. Cut nominal diameter 4.2 mm pilot holes in the fixture plate and identify them as `M5 x 0.8 TAP AFTER LASER`. Do not use the clamp body's clearance-hole diameter as the tap-drill size.

Treat 4.2 mm as the shop nominal. Confirm laser kerf, heat-affected edge, tapping practice, and actual clamp fit before production.

## DXF

- Use millimetres.
- Keep fabrication contours on `CUT` and identifiers/instructions on `ETCH`.
- Include all custom plates in the cutting file and nest on the minimum practical number of sheets. One sheet is preferred when feasible, not a fixed requirement.
- Generate part IDs and quantities from the final verified geometry.
- Reopen the DXF and compare every closed `CUT` loop with the final plate profiles. Keep stock references and text off `CUT`.

Design clamp platforms from hardware and joint requirements, not broad default rectangles. Apply the compactness workflow in [clamping.md](clamping.md). Keep auxiliary supports distinct from fixed datum lands; a solid fixed-height laser-cut land cannot be called floating or adjustable without the corresponding mechanism.
