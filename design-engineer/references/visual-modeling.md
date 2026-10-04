# Image-guided modeling and rendering

Use this route for detailed appearance, freeform exploration, reference matching, and presentation images. Blender may run through a connected tool, its Python API, or its executable; a special connection is not mandatory. Check the actual available version and tool interface.

## Read the image before modeling

Identify the visible major masses, component boundaries, symmetry, negative spaces, distinctive features, and surface transitions. Separate geometric detail from texture, reflection, shadow and motion blur. Note which surfaces are hidden or ambiguous.

For a reference-matched view, identify framing, horizon, perspective versus orthographic projection, camera height, apparent focal length, object size in frame, and visible top/side surfaces. Use these as adjustable hypotheses rather than recovered camera facts.

Use legitimate existing assets when they suit the task and their license is known; otherwise model the geometry. Do not spend time searching for assets when procedural modeling is more practical for the visible subject.

## Model and inspect in passes

1. **Silhouette:** block the overall form and largest components with simple geometry. Establish scale and camera. Inspect a neutral render against the reference before adding tiny features.
2. **Surface structure:** add real cross-sections, cavities, bevels, panel transitions and separate parts where they determine appearance. Choose curves, loft-like mesh sections, subdivision or sculpting according to the form.
3. **Identity details:** model important openings, grille structure, seams, fasteners, trim, and other recognizable features. Use instances or procedural repetition. Detail the views the user needs; do not invent hidden internals unless they are in scope.
4. **Materials and light:** tune surface finish, roughness, metallic response, glass and textures. Ensure textures use a sensible physical or object scale. Inspect geometry in neutral lighting as well as the final lighting.
5. **Final composition:** match framing, environment, depth, atmosphere, and requested motion effects. Keep details intended to be sharp readable.

Preserve an editable source and manageable object organization. Keep reusable geometry and source scripts where they materially help revision. A dense mesh is not inherently a detailed or accurate model.

## Reference comparison

Render a cheap draft early. Compare silhouette and a few stable landmarks at the reference camera: overall extents, opening centers, major edges, and spacing between features. An overlay is useful when supported; otherwise inspect side by side.

Correct the largest discrepancy first. If all features shift together, inspect camera and framing before changing the object. If only a local region differs, inspect its geometry. Do not distort verified CAD interfaces to improve a single projected view.

Then review surface quality, material separation, shadows and small details. Use neutral views and additional angles to expose defects hidden by glare, darkness or blur. Aim for the specified visual fidelity; do not promise reconstruction of hidden geometry from one image.

For tracking motion, moving the camera and subject together can keep the subject sharp while the static environment blurs. Verify the actual render rather than relying on animation settings alone. Use compositor effects when appropriate and disclose material departures from the reference.

## Final render

Honor the requested renderer, resolution, aspect ratio, format, alpha, and denoising. Use draft settings until framing and geometry are stable; finish with adequate sampling and inspect at delivery size. Check for clipping, floating parts, exposed internal geometry, unintended stretching, noisy edges and texture-scale errors.

After corrections, rerender the final image. Save the scene with settings that reproduce the delivered image. Pack required assets or include them using resolvable paths. Preserve the reference when useful and permitted, without making it part of the rendered scene accidentally.
