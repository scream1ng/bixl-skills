---
name: design-engineer
description: v1.4 · Develop product ideas, photographs, sketches, drawings, or existing STEP parts into detailed visual models or dimensioned CAD. Use for reference-based modeling, product form development, parts and assemblies, and iterative CAD previews. Supports build123d for solid CAD and Blender for visual modeling and rendering. Not for weld or checking fixtures (use design-fixture) or shop drawings of existing sheet-metal parts (use draft-drawing).
---

# Design Engineer

Turn the user's references and requirements into an editable model, then inspect and refine the actual output. Match the requested deliverable: a convincing image, a dimensioned part, or both. Visual resemblance and dimensional correctness are separate acceptance criteria.

## Workflow: three user-facing stages

The user sees exactly three stages. Route choice, spec, preliminary CAD, stage checks, layout/motion/process reviews and refinement are internal work between them.

1. **Requirements.** Use what the request and supplied files already settle. Ask every essential decision in one round, each with your recommendation ([question-rounds.md](references/question-rounds.md)). Ask a follow-up only when a missing answer would materially change the proposal. Once the proposal can be built, go straight to stage 2 without asking.
2. **Proposal board, approved once.** Build the complete design board in one pass, then show it ([Proposal board](references/review-and-delivery.md#proposal-board)). Ask one question: approve the proposal for CAD, or what to change. Revise and re-show the whole board until approved. Never show a partial board or add pictures across approval rounds.
3. **CAD delivery, autonomous.** After approval, build, check and deliver without further approvals. Pause only for a genuine blocker or a consequential departure from the approved proposal ([Changes and approvals](references/question-rounds.md#changes-and-approvals)).

When the user says to proceed on your judgment ("you have enough information — keep going", "use your recommendations"), accept your recommendation for every open question, mark those rows `"approval": "assumed"`, list them on the board, say so in one line, and continue. Silence or an elapsed timeout is never an answer.

Questions stay in chat in the ❓/➡️ format. Look facts up yourself (files, measurements, CAD); ask the user only for decisions. Never re-ask what the request, supplied files or earlier answers already settle.

## Design board: the one page the user reviews

Every picture, render, comparison and the element table go on one full-quality HTML **design board** (`board.html`), the job's scope of work. Bullets only, no paragraphs. Keep `board.json` in the job folder and build with `python scripts/board.py board.json` when the proposal is complete, after each requested revision, and at delivery (format in [review-and-delivery.md](references/review-and-delivery.md#design-board)); it embeds images at full resolution and blocks on a missing one. Chat replies are two or three sentences, the board link, and the stage's one question. Do not paste long specs or picture walkthroughs into chat.

## Host capabilities: same workflow on any assistant

This skill runs on ChatGPT and Claude. At the start, check which of these the host actually has and note it in `design-spec.md`. Use what exists; otherwise use the fallback. The three stages and the design board are identical on every host. Ask questions as chat text on every host so runs compare like for like.

| Capability | If available | Fallback |
|---|---|---|
| Image generation | Generate concept pictures for picture-first work | Render 2–3 quick CAD/Blender blockout variants as concepts, or simple vector sketches; or ask the user for concept images (from any tool) |
| Inline HTML rendering (ChatGPT visualization surface, Claude artifact) | Also show the board inline when it fits the host's size limit | Send `board.html` as a file; it opens in any browser at full quality |
| Code execution with the CAD environment | build123d, `scripts/preview.py` | Say which outputs are blocked; do not fake renders or previews |

Never claim a capability you did not use, and never present a generated picture as measured geometry.

## 1. Inspect and define success

- Open the supplied images and geometry before describing or modeling them. Inventory usable local assets and their licenses when relevant.
- CAD environment: reuse `~/.cache/design-engineer/venv` when it exists; otherwise create it from [requirements.txt](scripts/requirements.txt). Confirm it with `python -m unittest discover -s tests` from this skill's folder.
- Check available tools and versions: CAD engine, Blender connection or executable, and export/preview support. A running desktop app is optional when its CLI or Python engine can do the job. Prefer an existing environment; isolate new dependencies.
- Establish intended use, required output files, scale/units, important views, and the features that determine success. Derive these from the request before asking.
- For a supplied STEP, measure its units, bounds, solids, relevant faces and datums with the CAD kernel. Keep the original file and coordinate frame intact; apply only requested edits to a working copy.
- For an image, identify silhouette, part boundaries, symmetry, proportions, major surface transitions, and visible interfaces. A single view leaves depth and hidden geometry uncertain. Camera perspective can mimic a shape error.
- Record the plan (what will be built, estimated and verified, and where artifacts will be saved) in `design-spec.md` and on the board; do not stop for it. Ask before changing the requested envelope, interfaces, or scope; ordinary reversible modeling iterations are already part of the task.

## 2. Choose the modeling route

Choose the reconstruction workflow from the evidence as well as the requested output. Read [reference-workflows.md](references/reference-workflows.md): single-image matching, multiple-view reconstruction, CAD-first styling, or scan-assisted reconstruction. Record the selected workflow and its main uncertainty in the plan. Use the evidence already available; do not require scans or extra photographs for a sufficient single-view visual request.

| User's result | Route | Guidance |
|---|---|---|
| Dimensioned part, mechanical assembly, editable solids, STEP | Parametric solid CAD, normally build123d | [cad-modeling.md](references/cad-modeling.md) |
| Reference-matched appearance, sculpted form, scene, rendered image | Visual modeling, normally Blender | [visual-modeling.md](references/visual-modeling.md) |
| Accurate interfaces plus a styled enclosure or presentation render | CAD for functional geometry; CAD surfaces or Blender for styling as appropriate | Read both; establish which body is authoritative |

Do not replace a user's chosen application without explaining a concrete limitation. If a necessary tool is unavailable, try an appropriate supported alternative; identify any requested output that remains blocked.

Images **may guide geometry**. They do not establish unseen dimensions, tolerances, material properties, or engineering validity. Freeform features are not automatically deferred: try suitable curves, section profiles, lofts, sweeps, or mesh modeling. Explain actual limitations when a requested surface cannot be constructed or verified.

For concept-led restyling, establish the user's intended changes and protected features before choosing a style. When clarification is pending, an instruction to continue accepts only recommendations you actually showed; a design choice never put to the user with a recommendation stays open. For picture-first development, with or without existing CAD, follow [Concept pictures to CAD](references/reference-workflows.md#concept-pictures-to-cad): select a concept, capture its defining shapes and proportions, resolve useful alternate views, and compare a CAD blockout at the concept's camera angle before adding internals or detail. Reuse choices already made; do not re-ask a direction the user has chosen. Concept translation and the patch trial are internal: finish them before the proposal board and show their results on it. If the patch cannot reach the concept's look, show the options and their cost on the board as a trade-off; never downgrade the look silently. The camera-matched concept vs CAD comparison runs during CAD delivery and goes on the final board.

## 3. Record the working specification

Keep a concise `design-spec.md` in the job folder for nontrivial work. Record:

- Intended use, outputs, units, coordinate frame, main envelope and interfaces.
- Feature/part list; which existing geometry must be preserved.
- Important dimensions or proportions, their sources, and unresolved assumptions.
- Visual targets and measurable acceptance criteria appropriate to the request.
- An **element table**: one row per feature, part, interface or visual element the user would recognise (id, name, value or description, source, approval, status). Source, user approval and model status are separate fields: measuring the old housing does not mean the user approved keeping it.
- For assemblies, each bought or existing component's **functional faces** (inlet, outlet, connector exit, mounting face, service side) and their source (datasheet, vendor STEP, measurement). The layout review in step 5 depends on them. Every element must later appear in the previews. Keep the table in `elements.json` (the single source; `scripts/preview.py` reads it) and render the board's element table from it (format in [review-and-delivery.md](references/review-and-delivery.md#proposal-board)).

For each important value, distinguish **provided**, **measured from supplied CAD**, **derived from stated constraints**, and **estimated from a reference or design choice**. Record the source or derivation. User acceptance makes an estimate agreed, not measured; a measurement is not agreement either. Separate an ideal CAD value from a manufacturing tolerance.

**Spec on the board:** the element table (each element, its value, its source) and the list of estimates and assumptions are part of the proposal board. Board approval confirms them: set `approval` to `agreed`. Minor fillets and control points need no individual row unless they define the look; group them (e.g. "edge blends R2–R5, estimated").

## 4. Build from large forms to detail

1. **Blockout:** establish overall envelope, silhouette, datums, component placement, and viewing setup. Inspect before investing in detail.
2. **Structure:** create main bodies, cavities, section transitions, attachment regions, and clearances. Preserve functional constraints as styling evolves.
3. **Detail:** add justified ribs, vents, fasteners, fillets, seams, textures, or trim. Use parameters, symmetry, patterns, and instances for repetition. Include hidden functional geometry when the requested use requires it.
4. **Presentation:** generate neutral inspection views first; add materials, lighting, camera matching, and scene effects where requested.

Keep dimensions and repeated patterns editable. Avoid baking all parts into one mesh or treating a tessellated STEP export as reconstructed analytic CAD. Spend effort on important interfaces and recognizable surfaces, not uniform detail everywhere.

Use the internal stage checks in [review-and-delivery.md](references/review-and-delivery.md) before increasing detail or render cost. Pass each internal check for blockout, structure and detail before moving on; these are not user stops.

## 5. Inspect, compare, refine

Read [review-and-delivery.md](references/review-and-delivery.md). Run both applicable review tracks:

- **Geometry:** valid solids, dimensions, feature locations, holes, contacts, clearances, interference, and any specifically requested process checks.
- **Appearance:** silhouette, proportions, feature placement, surface continuity, perspective, and requested lighting/materials.
- **Mechanical layout** (assemblies, and housings around bought components): component orientations, functional paths, wasted space, support and retention, installation and service access, and whether the body suits the layout. Run it on the preliminary CAD before the proposal board, and again at structure; see [Mechanical layout review](references/review-and-delivery.md#mechanical-layout-review). Matching the agreed spec does not pass this check: a correctly placed part can still face the wrong way.
- **Motion** (anything that moves, folds, slides or adjusts): pose the CAD in each operating position and through its travel. In every position check clearance or intended contact, stops and retention, and stability or load path. Show every position from posed CAD, never from a generated image.
- **Process:** check the rules of the proposed manufacturing process that shape geometry (e.g. build orientation and supports, overhangs, minimum walls, tool access, draft, bend allowances, assembly clearances) on the preliminary CAD before the proposal, and again on the final CAD. If no process is stated, propose one in stage 1 rather than leaving it unchecked.

Inspect a rendered image or actual preview; a successful build or export is not a visual check. Identify the highest-impact discrepancy, change the smallest relevant parameter set, then inspect again. Recheck geometry affected by each revision. Handle camera mismatch before distorting correct CAD to fit a photograph.

**Previews:** generate the numbered sheet and the interactive 3D preview with comment pins using `scripts/preview.py` (it blocks when any element is missing a callout): from the preliminary CAD (`--stage blockout`) for the proposal board, and from the final CAD (`--stage detail`) at delivery. Intermediate stage previews are internal inspection; do not send them.

Continue until the requested criteria are met or a concrete limitation requires user input. When the same failure repeats without new evidence, change the construction strategy or ask a focused question instead of retrying indefinitely. Do not use the loop to expand scope.

## 6. Deliver the authorized result

Save the editable source, requested exports, and inspected preview/render to the agreed job folder. Reopen and verify the final files after the last revision. Board approval authorizes the package: finish, verify and deliver without a further approval gate. Update the same board to the delivered geometry: final sheet and viewer, proposal vs final comparison, check results, and any departures from the proposal.

Report file links, relevant checks and their results, and material differences or unresolved estimates. State exactly which checks were performed. Report three levels separately: concept imagery (appearance only), CAD verification (what was measured or checked in the model), and physical validation still required (fit, strength, print or function that only a built part can confirm). A detailed render or valid solid alone does not establish manufacturability. Keep requested preview-only work at the proposal board.

## Improving or evaluating this skill

When asked to test or improve modeling reliability, use [benchmarking.md](references/benchmarking.md). Evaluate real artifacts and retained examples before changing instructions. Do not run an unrelated benchmark suite during ordinary modeling work or claim modeling quality from a skill-format validator.
