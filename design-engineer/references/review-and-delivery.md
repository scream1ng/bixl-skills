# Review and delivery

Use the working spec as the acceptance checklist. Match verification effort to the requested output and consequences of error.

## Two independent review tracks

| Track | Evidence | What it does not establish |
|---|---|---|
| Geometry | CAD-kernel measurements, solid validity, declared contact/clearance checks, requested feature and process checks | Resemblance, finish, or engineering approval beyond the checks actually performed |
| Appearance | Inspected renders, reference comparisons, neutral inspection views and relevant alternate angles | Unknown dimensions, hidden features, tolerances, structural performance, or manufacturability |

Do not make a failed geometry check disappear behind a polished render. Do not call a model visually reviewed because a preview file was created.

## Mechanical layout review

For assemblies and housings around bought or existing components. Both tracks above check the model against the spec; this checks whether the arrangement itself is sound. Run it on the preliminary CAD before the proposal board, while orientation and body form are still cheap to change, and again at structure.

| Check | Ask |
|---|---|
| Orientation | Does each component face the way its function needs (inlet/outlet, connector exits, display or control side, gravity, drainage)? Would turning or mirroring it shorten a path or free space? |
| Functional paths | Trace air, fluid, cable, heat and load paths end to end. Any sharp turns, blocked inlets, crossings, recirculation or pinch points? |
| Wasted space | Where is dead volume? Could the envelope shrink or the parts regroup? |
| Support and retention | What holds each part, against which loads, vibration or shock? Is anything floating, cantilevered or held only by its cables? |
| Installation and access | Assembly order, hand and tool reach, fastener access, connector mating, service and replacement. |
| Body suitability | Does the chosen body (enclosure, housing, existing part) suit this layout, or is the layout being forced to fit it? |

Use the functional faces recorded in the element table; when one is unknown, say so instead of guessing an orientation. Put a "Layout review" section on the design board: a plan or section view with the paths drawn, one bullet per finding, and the alternative when a finding suggests one. Before the proposal, resolve findings internally and show the chosen arrangement and its alternative on the board. After approval, a finding that changes the envelope, an interface, the body or the approved arrangement is a consequential departure: ask. Never fix it silently.

## Internal stage checks

| Before proceeding to | Inspect | Resolve first |
|---|---|---|
| Small features | Neutral blockout at the reference view and relevant alternate views | Main silhouette, proportions, component placement, camera mismatch |
| Finish and presentation | Main surfaces, section transitions, negative spaces, functional interfaces | Visible discontinuities, missing defining features, affected fit/clearance failures |
| Expensive final render | Cheap draft with intended materials, camera and lighting | Framing, material separation, texture scale, obvious intersections or stretching |
| Delivery | Reopened final files and inspected final image | Export loss, missing assets, incorrect output settings, defects introduced by the last revision |

Apply only the stages relevant to the task. A CAD-only bracket needs no expensive presentation render. Passing a stage check releases the next stage; it is not a user stop. Do not keep polishing a later stage while a consequential earlier-stage defect remains unresolved.

## Proposal board

The one board the user approves in stage 2. Build all of it before showing any of it. Each preview covers the **whole element table**, not just what changed.

| Section | Contents |
|---|---|
| Brief and assumptions | Requirements used, recommendations adopted, open risks |
| Concept | Concept pictures, labelled appearance only |
| Views | Enough views to understand the design; every element visible at least once (`preview.py` sheet and 3D viewer from the preliminary CAD) |
| Mechanism | Moving parts: every operating position and how the parts fit together in it, from posed CAD, with the motion explained |
| Dimensions and interfaces | Element table: value, source, approval |
| Materials and manufacturing | Process, build orientation and supports or tooling, finishing, assembly |
| Feasibility | Checks run on the preliminary CAD and their results; what is not yet checked |
| Trade-offs | Alternatives considered and why this one |

Label every picture by `basis` (below): a concept picture never shows a mechanism position, clearance or fit. For concept work include the traced concept and section sketch.

At delivery, update the same board: final sheet and viewer, proposal vs final comparison (concept vs CAD at the concept camera for visual work), verification results, departures from the proposal, and physical validation still required. Keep the approved proposal in a dated section.

Generate with the CAD environment:

```
python scripts/preview.py model.step elements.json OUT --stage blockout [--html]
```

`model.step` may also be an STL (e.g. exported from Blender — set the export scale so the STL is in millimetres, matching the anchors). `elements.json`:

```json
{"project": "lamp", "revision": "r2", "elements": [
  {"id": "E1", "name": "Base disc", "value": "Ø180 × 12", "source": "provided", "anchor": [0, 0, 6]},
  {"id": "E2", "name": "Rear cable exit", "value": "Ø8, 20 above base", "source": "estimated", "anchor": [0, 90, 20]}]}
```

Add `"front": "+Y"` (one of ±X, ±Y, ±Z; default `-Y`) when the product's visible face points along another axis, so the sheet's Front view shows the face the user sees. `anchor` is a model-space point (mm) on the element's visible surface (for a hole, a point on its rim, not its empty centre). The script writes `OUT/sheet.png` (four views, numbered callouts, legend with value and source) and, with `--html`, `OUT/preview.html` (rotate/pan/zoom, numbered element markers, comment pins, copy comments). It **blocks** (exit 2, no outputs) when an element lacks an anchor or an anchor lies outside the model bounds — fix the table, don't drop the element.

Three separate fields per element; never infer one from another:

| Field | Values | Meaning |
|---|---|---|
| `source` | `provided`, `measured`, `derived`, `estimated` | Where the value came from |
| `approval` | `open` (default), `agreed`, `assumed` | The user's decision: confirmed it (board approval sets every proposal element to `agreed`), or accepted your recommendation by telling you to proceed. A routine element added during CAD delivery within the approved proposal is `assumed` and listed on the final board. A measured or provided value is still `open` until the user confirms keeping it |
| `status` | `pending`, `modeled` (default), `verified` | Model state: not built yet, built, or checked against its value with a CAD measurement |

An element not yet modeled stays in the table with `"status": "pending"` and shows as pending in the legend. At `--stage detail` the script refuses pending elements and any element whose approval is still `open`.

Each callout is filled where the anchor is visible and a ring where it is hidden. An element no view shows (underside, internals) **blocks** the preview: move the anchor onto a visible face, or render a section/detail view of it, set the element's `"image"` to that file (relative to `elements.json`; it must exist and be an image) and say what it shows in `"hidden"` (shown in the legend). The board's element card shows the image. Do not ask the user to approve elements they cannot see.

Open the sheet yourself before sending it, then add it (and `preview.html` as the board's viewer) to the design board. Comments are review notes; apply them to the spec and model, then regenerate.

## Design board

One page per job, rebuilt when the proposal is complete, after each requested revision, and at delivery: the brief, all pictures and renders at full quality, comparisons, element cards, the 3D viewer, and decisions. It is the scope of work the user approves. Bullets only.

```
python scripts/board.py board.json [--out board.html]
```

```json
{"project": "Fascia 636873", "revision": "r3", "stage": "proposal",
 "next": ["Approve for CAD, or list changes"],
 "brief": ["Keep 4 openings + mounts", "Flowing wave relief, +3 mm max"],
 "sections": [
   {"title": "Concept translation", "bullets": ["~28 crests across"],
    "images": [{"src": "concepts/trace.png", "basis": "concept", "caption": "Traced paths"}]},
   {"title": "Concept vs CAD", "compare": [{"a": "concepts/hero.png", "b": "renders/cad_hero.png",
     "a_label": "Concept", "b_label": "CAD", "caption": "same camera"}]}],
 "elements": "elements.json", "viewer": "out/preview.html",
 "decisions": [{"date": "2026-10-06", "text": "Continuous wave, not ribs"}], "open": ["LED strip type"]}
```

Paths are relative to `board.json`. Images are embedded unscaled; a missing or non-image file **blocks** (exit 2). Every section image needs a `basis`, shown as a badge: `concept` (generated or sketched; appearance only), `cad` (preliminary CAD; checked as stated), `final` (delivered CAD) or `photo` (supplied reference). A missing or unknown basis **blocks**. An element in `elements.json` may carry an `"image"` (a crop or close-up) for its card. Keep superseded pictures in a dated section rather than deleting them, so the board doubles as the job record. Open the board yourself before linking it.

## Evidence-based comparison

For nontrivial reference matching, record a short comparison table in the job folder: criterion, target/source, observed result, status, and next correction. Use `pass`, `needs revision`, or `not verifiable` separately for silhouette, proportions, feature placement, surface quality, and dimensional accuracy. Omit irrelevant criteria or mark them not applicable with a reason.

Choose a few stable landmarks before detailed modeling. Compare projected landmark positions only with matched camera/framing; compare physical dimensions with CAD measurements. Define useful tolerances from the brief before grading. If no numerical target is justified, give a specific visual observation rather than inventing a similarity percentage. Preserve uncertainty: a good silhouette cannot compensate for an unverified mating dimension.

For image-led surface styling, explicitly compare crest/valley continuity, feature endings, spacing and transitions into openings and borders. Separate measured source-geometry conflicts from limitations of the attempted construction; do not blame protected interfaces without evidence. A failed construction does not establish that the shape is impossible.

For progression trials, retain the baseline and compare actual CAD at matching camera, material and lighting settings. Report specific improvements and regressions alongside protected-interface and envelope checks. Label a visually incomplete result as a draft even when its STEP is valid.

## Refinement loop

1. Render or export a draft and inspect the actual artifact.
2. Identify the most consequential mismatch against the agreed criteria.
3. Determine whether its cause is geometry, camera, material, lighting, or the specification itself.
4. Change the smallest relevant parameter set. Stay within existing authorization; ask about a changed functional constraint or scope before depending on it.
5. Repeat affected geometry checks and visual inspection. Correct new defects introduced by the revision.

Before approval, put genuine preference alternatives on the proposal board as trade-offs. After approval, ask only if the choice departs consequentially from the proposal.

Stop iterating when applicable acceptance criteria are met and no material issue remains, or explain the concrete unresolved limitation. Repeated unchanged failures call for a different construction or missing information, not indefinite retries or silently reduced requirements.

## Verify the saved deliverables

- Reopen the saved native/CAD files after the final revision. Confirm expected objects/solids, units, transforms, required assets and editable source where promised.
- Reimport exported STEP when feasible; verify important dimensions and component counts survived export. Check actual feature positions/axes, not just overall bounds.
- Open the final image and check its actual dimensions and visible result. Keep the saved scene and final render consistent.
- Verify the preview was actually displayed if claiming it works interactively. Otherwise provide and inspect a static fallback and state the limitation.
- Place requested artifacts in the agreed folder. Keep drafts and supporting scripts out of the main deliverable list, while retaining useful revision sources.

In the final message, distinguish a model built exactly to chosen parameters from a model measured to match a real object. Do not label unperformed checks as passed.
