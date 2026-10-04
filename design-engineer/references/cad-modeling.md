# Parametric CAD workflow

Use solid CAD when dimensions, assembly interfaces, or STEP delivery matter. build123d is a suitable Python engine; use the user's required CAD system when available. Check the installed version and relevant API before relying on an unfamiliar operation.

## Preserve evidence and interfaces

For supplied geometry, import and measure the actual STEP. Establish units, axes, bounds, solid count and the datums needed for the requested edit. A bounding-box face is not necessarily a physical mating face. Measure the relevant face, axis, plane, or hole directly.

Keep the source unchanged on disk. Reference its geometry rather than rebuilding an approximate copy. Do not rotate or scale the imported base to simplify code unless the task authorizes that transformation; use local construction planes or a documented reversible working transform.

For image-only input, use known dimensions to anchor scale where available. Record estimated depths and unseen features explicitly. Do not infer dimensions from perspective pixel ratios as though they were orthographic measurements. A mesh that looks correct is not evidence of exact dimensions.

## Construction strategy

- Define units and a stable coordinate frame first. Put important dimensions and repeated feature parameters together in editable source.
- Decompose the object into functional bodies and operations. Sketch/extrude prismatic sections; revolve axisymmetric shapes; sweep sections along paths; loft between meaningful profiles for changing cross-sections.
- Build primary volumes before cuts, mounts, ribs and cosmetic edge treatment. Add fillets after supporting geometry is stable unless a curved section defines the primary form.
- Use symmetry and repeated features to keep paired interfaces consistent.
- Construct holes from their intended axes and datums. Keep mating clearances distinct from hole or shaft nominal sizes.
- Use robust geometric selectors or named construction references where possible; avoid unexplained face/edge indices that may change after a boolean.
- Keep separate assembly parts identifiable. Fuse only when the intended part is one body.

A more complex form may require several profiles or surface patches. Choose their number from the actual curvature and silhouette, not an arbitrary one-loft limit. Inspect sections and surface transitions; a valid solid can still have visibly poor curvature.

For dense ribs or other repeated features on an imported curved skin, first join one representative feature across a difficult surface transition and inspect both the solid and its render. Establish a reliable construction before generating the full pattern. When lofting many spline sections, use consistent point parameterization and inspect knot/pole counts if operations become unexpectedly slow; compatibility between differently parameterized sections can greatly inflate the surface. A valid individual rib does not prove that its union with the source is correct.

### Reconstructing continuous styling surfaces

Choose the construction from the reference's surface character before choosing CAD operations. Individual ribs on a base and continuously blended crests and valleys need different constructions; fusing strips into one solid does not make them visually continuous.

For flowing relief, first construct a representative patch containing neighboring crests, valleys and an opening or edge transition. Candidate methods include spline surfaces fitted to a controlled point grid and Gordon surfaces through intersecting profiles and guides. Retain protected source geometry and the agreed relief envelope. Test the patch's intended join to the exact source body, then inspect its sections and neutral render before extending the pattern. Inspect fitted surfaces between the input samples for overshoot; a valid face and a requested fitting tolerance do not alone prove the relief envelope. If automatic fitting becomes unstable, test explicit shared surface parameterization before scaling up again. If the defining transition remains wrong, change the construction rather than multiplying the same features.

Where Blender helps resolve form, share editable curves, sections and relief parameters with the CAD construction when practical. Do not independently reinterpret the image at every transfer. Compare reconstructed CAD against both the visual geometry and the reference; matching a flawed visual model is not matching the reference. Blender is optional; the CAD environment can construct and render the trial on its own.

For an ordered point-grid construction, the bundled [surface_from_grid.py](../scripts/surface_from_grid.py) provides fixed-parameter cubic interpolation. Load `surface_from_grid(points)` in the task CAD environment; it needs build123d, NumPy and SciPy. Supply geometric XYZ samples, not raw pixel brightness. The helper returns a face, not a verified solid, and does not prevent overshoot automatically. It was exercised with OCCT 8; its OCCT 7 import fallback still needs environment-specific validation.

Implementation references: [build123d surface APIs](https://build123d.readthedocs.io/en/latest/direct_api_reference.html#build123d.Face.make_surface_from_array_of_points) and [FreeCAD Gordon surface construction](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Curves_GordonSurface.md). Verify methods against the installed version. [Input Labs' migration](https://github.com/inputlabs/cad) is a practical example of rebuilding Blender parts in build123d, with STEP exported only for the reconstructed CAD parts.

## CAD plus visual styling

State which representation controls each requirement. CAD should control verified interfaces and the dimensions promised in the CAD deliverable. A Blender shell can explore appearance, but do not silently substitute it for requested editable solid geometry.

If the final styling is developed in Blender and STEP is required, construct suitable CAD surfaces/solids from the agreed form and verify them. If that reconstruction is incomplete, report the STEP limitation instead of exporting a faceted mesh and claiming equivalent parametric CAD. STEP itself does not preserve the generating Python parameters; include the editable source when requested.

Generate inspection/render meshes from the final CAD when evaluating its appearance. Set tessellation fine enough that display faceting does not masquerade as a geometry defect; measurements still come from the CAD kernel.

## Checks

After major operations, check whether each intended solid exists and is valid. Before final export, verify the actual dimensions and relationships named in the working spec, including relevant feature diameters, axes, positions, and depths. Overall bounds alone cannot verify these.

Use tolerances suited to the feature and agreed specification; do not apply a universal 0.5 mm threshold. Distinguish computational tolerance, intended clearance, and manufacturing tolerance. Record pass, fail, or not checked with the measurement and criterion.

Evaluate overlaps and gaps per intended relationship: separate, touching, joined, or intentionally penetrating. A positive overlap can be correct for material being fused and wrong between moving parts. Explain an unresolved result rather than converting it to a pass.

For process-specific work, check the requirements actually agreed: for example minimum wall thickness, tool access, bend allowances, draft, or moving clearances. Identify methods and unchecked areas. Do not imply a generic solid validator covers these.

If a boolean or fillet fails, inspect the operands, feature size, and offending region, then simplify or change the construction. Never fix a failed check by silently loosening the agreed requirement.
