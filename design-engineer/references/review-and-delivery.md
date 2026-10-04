# Review and delivery

Use the working spec as the acceptance checklist. Match verification effort to the requested output and consequences of error.

## Two independent review tracks

| Track | Evidence | What it does not establish |
|---|---|---|
| Geometry | CAD-kernel measurements, solid validity, declared contact/clearance checks, requested feature and process checks | Resemblance, finish, or engineering approval beyond the checks actually performed |
| Appearance | Inspected renders, reference comparisons, neutral inspection views and relevant alternate angles | Unknown dimensions, hidden features, tolerances, structural performance, or manufacturability |

Do not make a failed geometry check disappear behind a polished render. Do not call a model visually reviewed because a preview file was created.

## Internal stage checks

| Before proceeding to | Inspect | Resolve first |
|---|---|---|
| Small features | Neutral blockout at the reference view and relevant alternate views | Main silhouette, proportions, component placement, camera mismatch |
| Finish and presentation | Main surfaces, section transitions, negative spaces, functional interfaces | Visible discontinuities, missing defining features, affected fit/clearance failures |
| Expensive final render | Cheap draft with intended materials, camera and lighting | Framing, material separation, texture scale, obvious intersections or stretching |
| Delivery | Reopened final files and inspected final image | Export loss, missing assets, incorrect output settings, defects introduced by the last revision |

Apply only the stages relevant to the task. A CAD-only bracket needs no expensive presentation render. These checks do not ask the user to approve routine progress. Do not keep polishing a later stage while a consequential earlier-stage defect remains unresolved.

## Evidence-based comparison

For nontrivial reference matching, record a short comparison table in the job folder: criterion, target/source, observed result, status, and next correction. Use `pass`, `needs revision`, or `not verifiable` separately for silhouette, proportions, feature placement, surface quality, and dimensional accuracy. Omit irrelevant criteria or mark them not applicable with a reason.

Choose a few stable landmarks before detailed modeling. Compare projected landmark positions only with matched camera/framing; compare physical dimensions with CAD measurements. Define useful tolerances from the brief before grading. If no numerical target is justified, give a specific visual observation rather than inventing a similarity percentage. Preserve uncertainty: a good silhouette cannot compensate for an unverified mating dimension.

For image-led surface styling, explicitly compare crest/valley continuity, feature endings, spacing and transitions into openings and borders. Separate measured source-geometry conflicts from limitations of the attempted construction; do not blame protected interfaces without evidence. A failed construction does not establish that the shape is impossible.

For progression trials, retain the baseline and compare actual CAD at matching camera, material and lighting settings. Report specific improvements and regressions alongside protected-interface and envelope checks. Geometry validity and visual fidelity remain separate outcomes; label a visually incomplete result as a draft even when its STEP is valid. Do not invent similarity percentages.

## Refinement loop

1. Render or export a draft and inspect the actual artifact.
2. Identify the most consequential mismatch against the agreed criteria.
3. Determine whether its cause is geometry, camera, material, lighting, or the specification itself.
4. Change the smallest relevant parameter set. Stay within existing authorization; ask about a changed functional constraint or scope before depending on it.
5. Repeat affected geometry checks and visual inspection. Correct new defects introduced by the revision.

A clear request for a final result includes ordinary refinement. Avoid asking the user to approve every draft. If alternatives represent a genuine design preference, show the options together and ask a compact independent question round.

Stop iterating when applicable acceptance criteria are met and no material issue remains, or explain the concrete unresolved limitation. Repeated unchanged failures call for a different construction or missing information, not indefinite retries or silently reduced requirements.

## Verify the saved deliverables

- Reopen the saved native/CAD files after the final revision. Confirm expected objects/solids, units, transforms, required assets and editable source where promised.
- Reimport exported STEP when feasible; verify important dimensions and component counts survived export. Check actual feature positions/axes, not just overall bounds.
- Open the final image and check its actual dimensions and visible result. Keep the saved scene and final render consistent.
- Verify the preview was actually displayed if claiming it works interactively. Otherwise provide and inspect a static fallback and state the limitation.
- Place requested artifacts in the agreed folder. Keep drafts and supporting scripts out of the main deliverable list, while retaining useful revision sources.

Delivery follows the request. A preview-only request does not require a full production package. A request for STEP, native files or a final render does not need a second “handoff approval.”

The final message should link the outputs, name the meaningful checks and results, and identify significant deviations or estimates. Distinguish a model built exactly to chosen parameters from a model measured to match a real object. Do not label unperformed checks as passed.
