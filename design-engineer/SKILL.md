---
name: design-engineer
description: v1.0.0 · Develop product ideas, photographs, sketches, drawings, or existing STEP parts into detailed visual models or dimensioned CAD. Use for reference-based modeling, product form development, parts and assemblies, and iterative CAD previews. Supports build123d for solid CAD and Blender for visual modeling and rendering. Not for weld or checking fixtures (use design-fixture) or shop drawings of existing sheet-metal parts (use draft-drawing).
---

# Design Engineer

Turn the user's references and requirements into an editable model, then inspect and refine the actual output. Match the requested deliverable: a convincing image, a dimensioned part, or both. Visual resemblance and dimensional correctness are separate acceptance criteria.

## Questions: independent rounds of 2–3

When clarification is needed, ask a round of **2–3 independently answerable questions together**. Wait for that round's answers before asking questions that depend on them. Offer a recommendation where useful. Never ask already-answered questions or pad a round with unnecessary ones; if only one genuine blocker remains, ask that one.

Use the available structured question tool when appropriate; otherwise send a compact numbered round. Read [question-rounds.md](references/question-rounds.md) when preparing a round. If the request is already sufficient, state material assumptions and start work without an interview.

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

For concept-led restyling, establish the user's intended changes and protected features before choosing a style. When clarification is pending, do not treat a request to continue as an answer to unanswered design choices. For picture-first development, with or without existing CAD, follow [Concept pictures to CAD](references/reference-workflows.md#concept-pictures-to-cad): select a concept, capture its defining shapes and proportions, resolve useful alternate views, and compare a CAD blockout at the concept's camera angle before adding internals or detail. Reuse choices already made; do not add another selection gate after the user has chosen a direction.

## 3. Record the working specification

Keep a concise `design-spec.md` in the job folder for nontrivial work. Record:

- Intended use, outputs, units, coordinate frame, main envelope and interfaces.
- Feature/part list; which existing geometry must be preserved.
- Important dimensions or proportions, their sources, and unresolved assumptions.
- Visual targets and measurable acceptance criteria appropriate to the request.

For each important value, distinguish **provided**, **measured from supplied CAD**, **derived from stated constraints**, and **estimated from a reference or design choice**. Record the source or derivation. User acceptance makes an estimate agreed, not measured. Separate an ideal CAD value from a manufacturing tolerance.

Do not require the user to approve every styling control point, fillet, or decorative dimension. Resolve routine details within the brief. Ask about missing fit-critical dimensions before claiming a dimensionally verified fit. Work on independent geometry while those answers are pending.

## 4. Build from large forms to detail

1. **Blockout:** establish overall envelope, silhouette, datums, component placement, and viewing setup. Inspect before investing in detail.
2. **Structure:** create main bodies, cavities, section transitions, attachment regions, and clearances. Preserve functional constraints as styling evolves.
3. **Detail:** add justified ribs, vents, fasteners, fillets, seams, textures, or trim. Use parameters, symmetry, patterns, and instances for repetition. Include hidden functional geometry when the requested use requires it.
4. **Presentation:** generate neutral inspection views first; add materials, lighting, camera matching, and scene effects where requested.

Keep dimensions and repeated patterns editable. Avoid baking all parts into one mesh or treating a tessellated STEP export as reconstructed analytic CAD. Spend effort on important interfaces and recognizable surfaces, not uniform detail everywhere.

Use the internal stage checks in [review-and-delivery.md](references/review-and-delivery.md) before increasing detail or render cost. These are inspection checkpoints, not additional user-approval gates.

## 5. Inspect, compare, refine

Read [review-and-delivery.md](references/review-and-delivery.md). Run both applicable review tracks:

- **Geometry:** valid solids, dimensions, feature locations, holes, contacts, clearances, interference, and any specifically requested process checks.
- **Appearance:** silhouette, proportions, feature placement, surface continuity, perspective, and requested lighting/materials.

Inspect a rendered image or actual preview; a successful build or export is not a visual check. Identify the highest-impact discrepancy, change the smallest relevant parameter set, then inspect again. Recheck geometry affected by each revision. Handle camera mismatch before distorting correct CAD to fit a photograph.

Continue until the requested criteria are met or a concrete limitation requires user input. When the same failure repeats without new evidence, change the construction strategy or ask a focused question instead of retrying indefinitely. Do not use the loop to expand scope.

## 6. Deliver the authorized result

Save the editable source, requested exports, and inspected preview/render to the agreed job folder. Reopen and verify the final files after the last revision. If the user requested deliverables, that already authorizes creating the package; do not add another approval gate.

Report file links, relevant checks and their results, and material differences or unresolved estimates. State exactly which checks were performed. A detailed render or valid solid alone does not establish manufacturability. Keep requested preview-only work at the preview stage.

## Improving or evaluating this skill

When asked to test or improve modeling reliability, use [benchmarking.md](references/benchmarking.md). Evaluate real artifacts and retained examples before changing instructions. Do not run an unrelated benchmark suite during ordinary modeling work or claim modeling quality from a skill-format validator.
