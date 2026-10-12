# Isometric views

## Source and component identification

Inspect the complete supplied STEP assembly and drawing. Use STEP product names/relationships and exact CAD solids, backed by drawing component callouts, to identify parts. Record selected solid indices plus source identity/hash in the job; indices are specific to that file and never become skill defaults. Extra root solids may be weld beads, not additional BOM items. Keep all appropriate solids in the final assembly. Do not modify CAD for these illustrations.

Render the formed main part without hardware, the separate secondary part, each relevant hardware component, and complete finished assembly. Use a consistent orthographic view that shows important features clearly. Orient simple plates to show holes and thickness; orient studs with the head above the threaded shank. Use a neutral steel shade for uncoated shapes and a source-defined finish for the final view. Keep lighting readable on the white PFC sheet. Preserve transparent backgrounds and crop/pad evenly; do not add decorative environments or imagegen details.

## Renderer

`render_iso.py` uses exact cadquery STEP import and tessellation, orthographic projection, surface shading and silhouette edges. It preserves the supplied geometry rather than constructing an approximation. Its CAD render is illustrative and does not establish a dimension or an inspection tolerance.

```bash
python scripts/render_iso.py JOB/sources/assembly.step JOB/render-config.json --out JOB/renders
```

A render config has `views` mapped to roles. Each view has `solids` (0-based selected solids), camera and up vectors, optional RGB `color`, `size` [width,height] pixels, and mesh tolerance (default 0.06 in CAD model units). Read and verify STEP units first. Set a view orientation deliberately from the component's real frame; no global-axis assumption or sample camera is universal. Adjust camera if a necessary hole/fastener is hidden. Preserve transformed assembly locations and inspect the complete view.

Dependencies: cadquery, numpy and Pillow. Use the installed primary runtime when available. Other environments can use an isolated environment with scripts/render-requirements.txt. If exact rendering dependencies are unavailable, use a supplied current drawing's isometric crop when adequate, label its source and preserve its meaning; otherwise report the render limitation. Never substitute generated geometry.

## Placement and review

Use `images` and `layout.boxes` in the spec, in the source form coordinate system returned by `scripts/form.py`. Preserve the reference frame and legend positions; boxes use the enlarged sizes from `spaced()` in `pfc.py`, so place images in the remaining whitespace; do not resize the form around images. Prefer main part in the middle near Form/Bend, small spacer/secondary component on the right near its manufacturing stage, hardware left near its consuming stage, and finished assembly bottom right near Finish/Pack. Keep process boxes compact, with renders beside or around their relevant stage. Prefer external pictures and do not enlarge boxes to enclose them. Reserve an inside-box image for an explicit user request. External images must not overlap process boxes, arrows, other pictures or the symbol legend. Leave clear connector corridors and arrange photos in the remaining whitespace. Inspect visible connector paths as well as box intersections.

Keep all renders in one complete preview before review. Comment pins can target the image's mapped node. Keep HTML below 1 MB and optimize PNG size without losing hole/thread recognition. Use the exact approved image bytes in Excel; record each SHA-256. Both the source STEP/drawing and image bytes bind approval. Verify Excel picture count, byte hashes, aspect ratios and full printed page. Do not deliver a user workbook during preview iteration.
