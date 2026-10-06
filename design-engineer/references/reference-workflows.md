# Choose a workflow from the evidence

Select the least complex workflow that supports the requested result. Combine routes when different regions have different evidence. Supplied CAD and verified dimensions remain authoritative for the interfaces they describe.

## Single image: match the intended view

Use for a render or visual concept from one photograph or illustration.

- Establish the camera, silhouette and several visible landmarks together; keep geometric proportions and camera parameters separately editable.
- Build visible major forms, render a neutral draft, compare the reference, and correct the largest discrepancy before adding details.
- Record inferred depth and hidden surfaces as estimates. Inspect another angle for gross geometry defects, while recognizing that it cannot validate unseen shape against the source.
- If exact fit or a faithful all-around reconstruction is requested, ask for the missing dimensions or views; continue independent visible-form work when useful.

## Multiple views: reconstruct a consistent object

Use when front/side/rear photographs, drawings, or a suitable view set are available.

- Check whether images show the same object and configuration. Distinguish orthographic drawings from perspective photographs; account for separate camera viewpoints and image crops.
- Establish a common coordinate frame and reliable scale where known. Identify shared landmarks, then construct principal outlines and section profiles.
- Build and inspect the surfaces between sections. Check every supplied view after major changes so a local improvement does not break the opposite side or profile.
- Resolve conflicting evidence explicitly. Do not average away a known dimension or treat AI-generated alternate views as independent measurements.

## CAD-first styling: protect functional geometry

Use for an existing part, assembly, or product with defined interfaces.

- Establish the authoritative base, mounting locations, internal keep-out regions and clearances before shaping the exterior.
- Develop the outer form around those constraints. Use parametric surfaces where practical; use a separate visual shell when exploring freeform styling.
- Render meshes derived from the CAD to assess the actual CAD appearance. After styling changes, recheck affected interfaces, clearances and envelope.
- If the promised STEP must include a mesh-developed shell, reconstruct and verify suitable CAD geometry before claiming that deliverable complete. Keep an unresolved mesh shell clearly identified.

## Concept pictures to CAD

Use when the user wants to explore styling in pictures before developing geometry, with or without an existing CAD base.

- Settle intended changes, style and protected interfaces first. Save available source geometry, dimensional evidence and user decisions in the project folder so subsequent sessions can resume from evidence. Record explicit exceptions, such as an opening the user wants removed.
- Generate concepts using views rendered from supplied CAD when available; otherwise start from the supplied photographs, drawings or brief. Without an image generator, offer 2–3 rendered blockout variants (same camera, differing only in the open design choices) or ask the user for concept images; the rest of this workflow is unchanged. Once a direction is selected, retain that image and user corrections as the common styling reference for subsequent views; do not independently redesign each angle.
- Choose a view set that shows every element in the element table at least once. A front view clarifies layout and texture paths; side or section views clarify depth and transitions; an oblique view shows form; a detail view clarifies rib profiles and edge termination. Add rear views when the rear design is changing or unseen regions need the user's decision. Show these views to the user, not only to yourself.
- Generated alternate views are design proposals, not additional measured evidence or automatically consistent projections. Check silhouette, aperture locations, feature count, rib paths and edge transitions together against the source CAD and selected concept. Fix or explicitly resolve contradictions before using them to define geometry; never average away a protected CAD dimension.
- For hidden mounts, wall thickness, light channels and other functional sections, prefer views from a constrained CAD blockout. An image may illustrate a proposed arrangement, but label unselected hardware and inferred clearances; do not present an invented rear view as recovered source geometry.
- Capture the selected concept's defining geometry in `design-spec.md`: outlines, height/width/depth proportions, component arrangement, opening centres and distinctive transitions. Distinguish geometry from reflection, texture and lighting. Translate these into editable dimensions, curves, sections, relief height, pitch, edge blends and surface boundaries. Record which are measured and which are design choices; establish scale from reliable dimensions or explicitly record a chosen scale.
- **Concept translation (stop):** put on the design board the concept with its defining lines traced over it and aligned to the CAD front view, the counts and pitch (e.g. crests across), and a cross-section sketch giving depth, profile and edge endings. Ask the surface-character questions (continuous vs discrete, pitch, depth, profile). Do not build until the user confirms these numbers; a picture the agent invented (such as a path study) is a proposal until confirmed.
- **Patch trial (stop):** for textured or sculpted surfaces, build a small representative patch with the intended construction and render it beside a crop of the concept at a similar angle and light. If it cannot reach the look, show the alternatives and their cost on the board and let the user choose. Never quietly fall back to a simpler construction.
- Before adding internals or small details, build a simple CAD blockout and render it at the selected concept's camera angle and framing. Compare silhouette, proportions and feature positions with the board's compare slider (concept vs CAD, same camera, framing and lighting). Resolve camera mismatch before changing geometry, and correct the largest shape differences while the model is still simple.
- Carry the defining shapes into detailed CAD. Do not silently replace distinctive forms with generic primitives to simplify construction. Try suitable curves, lofts or sweeps; show and explain necessary departures from the selected design, including their visual effect and any unresolved tool limitation.
- Render the actual CAD from the agreed views and the concept's camera and lighting, and compare it with the selected concept on the board's compare slider at structure and detail. Resolve camera mismatch first, then refine geometry. Check both preserved interfaces and appearance; approval of a concept does not verify fit or manufacturing suitability.

## Scan-assisted: capture an existing object

Use when an actual scan or adequate overlapping photographs of the physical object are available, or when the user chooses to capture them. Do not make this a prerequisite for an ordinary image-modeling request.

- Check reconstruction-tool availability and inspect capture coverage, scale evidence and gaps before processing.
- Reconstruct or import the mesh, establish scale from reliable measurements, and inspect holes, noise and distorted regions. Reflective, transparent or poorly observed regions may need additional evidence.
- Keep the captured mesh as a reference. Rebuild needed functional features or surfaces in CAD and compare them to both the scan and known measurements.
- Do not describe a scan as exact ground truth or automatic mesh-to-STEP conversion as recovered design intent. State the actual dimensional evidence and limitations.
