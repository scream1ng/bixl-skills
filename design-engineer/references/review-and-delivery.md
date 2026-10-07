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

Use the functional faces recorded in the element table; when one is unknown, say so instead of guessing an orientation. Put the layout review inside the relevant assembly/interface element: a plan or section view with the paths drawn, one bullet per finding, and the alternative when a finding suggests one. Before the proposal, resolve findings internally and show the chosen arrangement and its alternative on the board. After approval, a finding that changes the envelope, an interface, the body or the approved arrangement is a consequential departure: ask. Never fix it silently.

**When the product's purpose is an effect** (light out of a reveal, air through a vent), on any part, not only assemblies: check that the effect works on the preliminary CAD before the proposal. Trace rays or flow from the source and report the share that reaches where it is meant to go; a hidden source says nothing about whether the effect works. Show the traced paths and the share in a section in the relevant element, and offer an alternative when the effect is weak.

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

Use the three-section layout and visual requirements in [board-format.md](board-format.md). Review holds the requested concept options, recommendation and enough overall views. Elements hold dimensions, functional interfaces, materials/process, layout findings, posed mechanisms, feasibility evidence and trade-offs, each with a visible snapshot. Revision History records brief actual changes. Do not add extra top-level cards for these subjects.

Label concept images as appearance-only; use actual posed CAD for mechanism positions and actual geometry for fit/clearance evidence. Complete and inspect every render and snapshot before presenting the board. For a simple visual concept, do not force final CAD before approval: a rough blockout is enough, and it supplies the snapshots and viewer. Skip preliminary CAD only when the user asked for concept imagery alone; then each element's picture is a labelled crop of a concept image (`image_basis: concept`). At delivery use the current actual model for snapshots and the viewer. Preserve the approved proposal in job files and put relevant matched-view comparisons in Review or the affected element.

Generate with the CAD environment:

```
python scripts/preview.py model.step elements.json OUT --stage blockout [--html] [--snapshots] [--fill-images]
```

`model.step` may also be an STL (e.g. exported from Blender — set the export scale so the STL is in millimetres, matching the anchors). `elements.json`:

```json
{"project": "lamp", "revision": "r2", "elements": [
  {"id": "E1", "name": "Base disc", "value": "Ø180 × 12", "source": "provided", "anchor": [0, 0, 6]},
  {"id": "E2", "name": "Rear cable exit", "value": "Ø8, 20 above base", "source": "estimated", "anchor": [0, 90, 20]}]}
```

Add `"front": "+Y"` (one of ±X, ±Y, ±Z; default `-Y`) when the product's visible face points along another axis, so the sheet's Front view shows the face the user sees. `anchor` is a model-space point (mm) on the element's visible surface (for a hole, a point on its rim, not its empty centre). The script writes `OUT/sheet.png` (four views, numbered callouts, legend with value and source) and, with `--html`, `OUT/preview.html` (rotate/pan/zoom, numbered element markers, comment pins, copy comments). It **blocks** (exit 2, no outputs) when an element lacks an anchor, or an anchor is not on the model surface (more than 0.5 mm or 0.5 % of the part away, whichever is larger; the message gives the nearest surface point) — fix the table, don't drop the element. Comment positions copied from the viewer are in the model's own coordinates, whatever `front` is.

`--snapshots` also writes draft pictures for the board: `OUT/views/{iso,front,rear,right,top}.jpg` and `OUT/elements/<id>.jpg`, smooth-shaded with outlined edges, a few seconds each. Each element is shown from the nearest direction in which its anchor is on the visible surface, including the rear and underside, so an element hidden on the four-view sheet no longer needs a hand-made image when a snapshot shows it; `snapshot_missing` lists the ones no outside view can show (give those a section). `--fill-images` writes `image`, `image_basis` (`final` at `--stage detail`, otherwise `cad`) and `image_caption` into `elements.json` for every element that does not carry its own picture. These are the default board pictures; see the draft rule in [board-format.md](board-format.md).

Three separate fields per element; never infer one from another:

| Field | Values | Meaning |
|---|---|---|
| `source` | `provided`, `measured`, `derived`, `estimated` | Where the value came from |
| `approval` | `open` (default), `agreed`, `assumed` | The user's decision: confirmed the presented design choice (board approval does not verify physical performance or accept undisclosed assumptions), or accepted your recommendation by telling you to proceed. A routine element added during CAD delivery within the approved proposal is `assumed` and listed on the final board. A measured or provided value is still `open` until the user confirms keeping it |
| `status` | `pending`, `modeled` (default), `verified` | Model state: not built yet, built, or checked against its value with a CAD measurement |

An element not yet modeled stays in the table with `"status": "pending"` and shows as pending in the legend. At `--stage detail` the script refuses pending elements and any element whose approval is still `open`.

Each callout is filled where the anchor is visible and a ring where it is hidden. An element no sheet view shows (underside, internals) **blocks** the preview unless `--snapshots` finds a rear or underside view that shows it (that snapshot is its evidence): move the anchor onto a visible face, or render a section/detail view of it, set the element's `"image"` to that file (relative to `elements.json`; it must exist and be an image) and say what it shows in `"hidden"` (shown in the legend). The board's element card shows the image. Do not ask the user to approve elements they cannot see.

Open the sheet yourself before sending it, then add it (and `preview.html` as the board's viewer) to the design board. Comments are review notes; apply them to the spec and model, then regenerate.

## Design board

Follow [board-format.md](board-format.md) for schema v2, the three-section layout, mandatory per-element snapshots, evidence labels, revision history and migration. Use the generator after assembling all assets; it does not create the renders itself. Retain source/approval/model status separately, and keep questions in chat until answered or explicitly deferred. There is no separate specification, remaining-checks or question-form section.

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
- For a feature added to existing geometry, inspect a section through the joint: a gap or a one-sided join passes validity and volume checks. To make one, cut the part in half with a box in build123d, export that STEP, and run `preview.py --snapshots` on it with an anchor on the cut face; that element's snapshot is the section.
- Open the final image and check its actual dimensions and visible result. Keep the saved scene and final render consistent.
- Verify the preview was actually displayed if claiming it works interactively. Otherwise provide and inspect a static fallback and state the limitation.
- Place requested artifacts in the agreed folder. Keep drafts and supporting scripts out of the main deliverable list, while retaining useful revision sources.

In the final message, distinguish a model built exactly to chosen parameters from a model measured to match a real object. Do not label unperformed checks as passed.
