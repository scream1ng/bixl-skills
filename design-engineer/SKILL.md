---
name: design-engineer
description: v1.1 · Develop product ideas, photographs, sketches, drawings, or existing STEP parts into detailed visual models or dimensioned CAD. Use for reference-based modeling, product form development, parts and assemblies, and iterative CAD previews. Supports build123d for solid CAD and Blender for visual modeling and rendering. Not for weld or checking fixtures (use design-fixture) or shop drawings of existing sheet-metal parts (use draft-drawing).
---

# Design Engineer

Turn the user's references and requirements into an editable model, then inspect and refine the actual output. Match the requested deliverable: a convincing image, a dimensioned part, or both. Visual resemblance and dimensional correctness are separate acceptance criteria.

## Questions: grill the design tree until it is settled

Build shared understanding before modeling with the grilling interview in [question-rounds.md](references/question-rounds.md) — part of this skill, not a separate one. Walk the design tree (use, outputs, scale/envelope, interfaces, every element, form, surface character, material/finish, hidden regions, tolerances). Each round asks **every frontier question at once** — every decision whose prerequisites are settled — with no cap, but never a question whose answer depends on another question in the same round. Each question carries your recommendation. Look facts up yourself (files, measurements, CAD); ask the user only for decisions. Never re-ask what the request, supplied files or earlier answers already settle.

Questions stay in chat in the ❓/➡️ format; any picture a question needs goes on the design board first. A detailed brief shortens the interview but does not skip it: unstated items still go into the spec playback (step 3) as proposed values for the user to confirm.

## Design board: the one page the user reviews

Every picture, render, comparison and the element table go on one full-quality HTML **design board** (`board.html`), the job's scope of work. Bullets only, no paragraphs. Keep `board.json` in the job folder and rebuild with `python scripts/board.py board.json` at every stop (format in [review-and-delivery.md](references/review-and-delivery.md#design-board)); it embeds images at full resolution and blocks on a missing one. Chat replies are two or three sentences, the board link, and the round's questions. Do not paste long specs or picture walkthroughs into chat.

## Host capabilities: same workflow on any assistant

This skill runs on ChatGPT and Claude. At the start, check which of these the host actually has and note it in `design-spec.md`. Use what exists; otherwise use the fallback. The question rounds, design board, spec playback, stage previews and their stops are identical on every host. Ask questions as chat text on every host so runs compare like for like.

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
- Give a brief plan: what will be built, what is estimated, what will be verified, and where artifacts will be saved. Ask before changing the requested envelope, interfaces, or scope; ordinary reversible modeling iterations are already part of the task.

## 2. Choose the modeling route

Choose the reconstruction workflow from the evidence as well as the requested output. Read [reference-workflows.md](references/reference-workflows.md): single-image matching, multiple-view reconstruction, CAD-first styling, or scan-assisted reconstruction. State the selected workflow and its main uncertainty in the brief plan. Use the evidence already available; do not require scans or extra photographs for a sufficient single-view visual request.

| User's result | Route | Guidance |
|---|---|---|
| Dimensioned part, mechanical assembly, editable solids, STEP | Parametric solid CAD, normally build123d | [cad-modeling.md](references/cad-modeling.md) |
| Reference-matched appearance, sculpted form, scene, rendered image | Visual modeling, normally Blender | [visual-modeling.md](references/visual-modeling.md) |
| Accurate interfaces plus a styled enclosure or presentation render | CAD for functional geometry; CAD surfaces or Blender for styling as appropriate | Read both; establish which body is authoritative |

Do not replace a user's chosen application without explaining a concrete limitation. If a necessary tool is unavailable, try an appropriate supported alternative; identify any requested output that remains blocked.

Images **may guide geometry**. They do not establish unseen dimensions, tolerances, material properties, or engineering validity. Freeform features are not automatically deferred: try suitable curves, section profiles, lofts, sweeps, or mesh modeling. Explain actual limitations when a requested surface cannot be constructed or verified.

For concept-led restyling, establish the user's intended changes and protected features before choosing a style. When clarification is pending, do not treat a request to continue as an answer to unanswered design choices. For picture-first development, with or without existing CAD, follow [Concept pictures to CAD](references/reference-workflows.md#concept-pictures-to-cad): select a concept, capture its defining shapes and proportions, resolve useful alternate views, and compare a CAD blockout at the concept's camera angle before adding internals or detail. Reuse choices already made; do not re-ask a direction the user has chosen. The stage previews in step 5 still apply. Three extra stops for picture-first work:

- **Concept translation:** before any CAD, put on the board the concept with traced lines, counts and pitch, and a cross-section sketch with depth and profile, aligned to the CAD front view. The user confirms the numbers; the picture alone is not the spec.
- **Patch trial:** for a textured or sculpted surface, build a small patch first and show it beside a concept crop. If the chosen construction cannot reach the look, stop and show the options (e.g. continuous lofted surface vs discrete ribs). Never downgrade the look silently.
- **Camera-matched comparison:** at structure and detail, render the CAD at the concept's camera and lighting and show it with the board's compare slider.

## 3. Record the working specification

Keep a concise `design-spec.md` in the job folder for nontrivial work. Record:

- Intended use, outputs, units, coordinate frame, main envelope and interfaces.
- Feature/part list; which existing geometry must be preserved.
- Important dimensions or proportions, their sources, and unresolved assumptions.
- Visual targets and measurable acceptance criteria appropriate to the request.
- An **element table**: one row per feature, part, interface or visual element the user would recognise (id, name, value or description, source, status). Every element must later appear in the previews. Keep the table in `elements.json` (the single source; `scripts/preview.py` reads it) and render the spec table and playback from it (format in [review-and-delivery.md](references/review-and-delivery.md#stage-previews)).

For each important value, distinguish **provided**, **measured from supplied CAD**, **derived from stated constraints**, and **estimated from a reference or design choice**. Record the source or derivation. User acceptance makes an estimate agreed, not measured. Separate an ideal CAD value from a manufacturing tolerance.

**Spec playback gate:** before the blockout, show the user, on the design board, the element table (each element, its value, its source) and the list of estimates and assumptions. Stop and wait for confirmation or corrections. Do not start modeling on an unconfirmed spec. Minor fillets and control points need no individual row unless they define the look; group them (e.g. "edge blends R2–R5, estimated").

## 4. Build from large forms to detail

1. **Blockout:** establish overall envelope, silhouette, datums, component placement, and viewing setup. Inspect before investing in detail.
2. **Structure:** create main bodies, cavities, section transitions, attachment regions, and clearances. Preserve functional constraints as styling evolves.
3. **Detail:** add justified ribs, vents, fasteners, fillets, seams, textures, or trim. Use parameters, symmetry, patterns, and instances for repetition. Include hidden functional geometry when the requested use requires it.
4. **Presentation:** generate neutral inspection views first; add materials, lighting, camera matching, and scene effects where requested.

Keep dimensions and repeated patterns editable. Avoid baking all parts into one mesh or treating a tessellated STEP export as reconstructed analytic CAD. Spend effort on important interfaces and recognizable surfaces, not uniform detail everywhere.

Use the internal stage checks in [review-and-delivery.md](references/review-and-delivery.md) before increasing detail or render cost. After passing each internal check for blockout, structure and detail, show the user the stage preview (step 5) and stop for their approval.

## 5. Inspect, compare, refine

Read [review-and-delivery.md](references/review-and-delivery.md). Run both applicable review tracks:

- **Geometry:** valid solids, dimensions, feature locations, holes, contacts, clearances, interference, and any specifically requested process checks.
- **Appearance:** silhouette, proportions, feature placement, surface continuity, perspective, and requested lighting/materials.

Inspect a rendered image or actual preview; a successful build or export is not a visual check. Identify the highest-impact discrepancy, change the smallest relevant parameter set, then inspect again. Recheck geometry affected by each revision. Handle camera mismatch before distorting correct CAD to fit a photograph.

**Stage previews (hard stops):** at the end of blockout, structure and detail, show the user a labeled preview in which every element-table row is visible and numbered — a multi-view image sheet at every stage, plus the interactive 3D preview with comment pins at the structure stage (and on request at others). Generate them with `scripts/preview.py` (it blocks when any element is missing a callout) and put them on the design board. Ask the frontier questions the preview raises, then stop until the user approves or comments. Apply comments, regenerate, and re-show before moving to the next stage. Silence or "continue" without answering open questions is not approval.

Continue until the requested criteria are met or a concrete limitation requires user input. When the same failure repeats without new evidence, change the construction strategy or ask a focused question instead of retrying indefinitely. Do not use the loop to expand scope.

## 6. Deliver the authorized result

Save the editable source, requested exports, and inspected preview/render to the agreed job folder. Reopen and verify the final files after the last revision. Once the user approves the detail-stage preview, create the requested package without a further approval gate.

Report file links, relevant checks and their results, and material differences or unresolved estimates. State exactly which checks were performed. A detailed render or valid solid alone does not establish manufacturability. Keep requested preview-only work at the preview stage.

## Improving or evaluating this skill

When asked to test or improve modeling reliability, use [benchmarking.md](references/benchmarking.md). Evaluate real artifacts and retained examples before changing instructions. Do not run an unrelated benchmark suite during ordinary modeling work or claim modeling quality from a skill-format validator.
