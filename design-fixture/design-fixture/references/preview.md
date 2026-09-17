# Lightweight Three.js preview

`workflow.py concept` writes `preview.html`, `scene.json`, `evaluated-spec.json`, private `concept.step` and two fallback PNGs. No DXF/nesting/final package is produced. Geometry comes from the final pipelines' OCP plate, tab/slot, clamp, checking-offset, body and hardware functions. Block concepts use `block_bodies` with box stock/add/subtract or exact finished STEP, not machining approval.

HTML embeds compact indexed meshes, pinned Three.js 0.180.0 modules from jsDelivr, rotate/pan/zoom, isometric/front/right/top cameras, per-component/group visibility, selected ID, project/revision and a permanent non-authoritative warning. Coarse tessellation and vertex clustering compact workpiece meshes; original/preview triangle counts are recorded. No random triangle omission or mesh measurement is authoritative.

For inline ChatGPT visualization, use an available raw-HTML visualization surface with the **exact generated HTML**, not a local-file iframe. Discover the supported surface; no second skill is required. If HTML/ES modules/WebGL/CDN is unavailable or payload reaches 1,000,000 bytes, show PNGs and offer standalone `preview.html`. Keep inline HTML strictly under 1 MB. HTML displays a load/WebGL failure message and PNG links. Interactive HTML needs CDN access; OCP/PNGs work offline once Python dependencies are installed. Do not claim inline rendering succeeded without inspecting it. Window capture is enough feedback.

Diagnostic CLI: `python scripts/preview.py spec.json OUT --kind weld --construction laser_rib`. Routine projects use `workflow.py concept` to enforce identity. Keep evaluated-spec hash with the scene; never mix revisions. Preview STEP remains private work material, never a substitute for final reopened exports/validation.
