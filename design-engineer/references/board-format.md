# Visual review board contract

Build one complete board before presenting it. Use `python scripts/board.py board.json`; link its returned `delivery_board` (revision-specific filename), retaining `board.html` as the working copy. Increment `board_revision` whenever the presented board changes, even when the CAD revision stays the same. The generator embeds images unscaled and the viewer in `srcdoc`; missing assets or unlabelled evidence block generation. It does not render images or validate the CAD for you.

## Exactly three top-level sections

1. **Design Review / 3D Review**: project, design/CAD revision and board revision in one small line inside this section. During proposal, show the requested number of distinct rendered concepts and identify the recommendation; add a preliminary viewer when useful. During CAD delivery, show the actual interactive model plus inspected CAD render(s) as static fallback. Keep comparisons here or in the relevant element.
2. **Elements**: three columns on desktop, two on tablet, one on mobile. Every card has a clean, clearly framed feature snapshot visible while collapsed; then name, dimensions, evidence basis, source, approval and modelling status. Expand for full-size images, corner/section/rear views, motion poses, checks, assumptions and approved deferrals. Do not substitute a repeated whole-part thumbnail for an unreadable small feature. Use a deliberate camera/crop, no clipped feature or legend overlay. Keep IDs stable across revisions and align them with viewer markers. Element image paths are relative to `elements.json`.
3. **Revision History**: brief dated entries describing what changed and why. Keep CAD/design revisions separate from presentation revisions. Include only real history; an initial proposal has one initial entry. Keep prior sources/boards in the job files; do not accumulate superseded full-size galleries on the current board.

No separate page banner, logo, navigation strip, scope/specification card, questions form or generic engineering-check section. Use black, red, grey and white UI defaults with no company identity. Product materials and user-requested product markings remain task-specific, not template branding. Avoid forcing actual product renders into the UI palette.

## Visual obligations

- Concept stage: generate/render all requested options and sufficient views to explain their form and function. Use image generation for illustrative styling when available; use the host fallback from SKILL.md if unavailable. Do not stop at a text-only board or wait for the user to request renders.
- CAD stage: derive snapshots and inspection views from the current delivered geometry. Generated concept images cannot stand in for CAD evidence. Keep relevant concept comparisons labelled.
- Moving/hidden features: show posed CAD, sections, underside/rear or exploded views as needed, inside the relevant element. An illustrative image cannot prove clearance, motion or fit.
- Inspect actual output before sharing: framing, readability at card size, completeness, intended front axis, correct state/revision and correspondence to delivered CAD. Enlarge must show the full image. Test viewer controls, comment copying and element links when browser execution is available; otherwise state the interactive check was unavailable and inspect the static images.
- Resolve questions affecting the next stage in chat before depending on them. Only an explicitly approved deferral can be labelled approved; keep the unresolved requirement/assumption and approval evidence under its element. Board approval accepts shown design choices, not unperformed physical validation. Routine estimated values within the agreed scope do not need another approval round.

## Schema v2

`board.json` paths are relative to that file. `elements.json` is the shared source used by the viewer and the board. Optional fields are omitted below where unnecessary.

```json
{
  "schema_version": 2,
  "project": "Desk lamp",
  "revision": "CAD R2",
  "board_revision": "R3",
  "stage": "delivery",
  "elements": "elements.json",
  "viewer": "preview/preview.html",
  "review": {
    "recommendation": "Selected concept B: rounded base and enclosed cable route.",
    "images": [{"src": "renders/assembly.png", "basis": "final", "caption": "Delivered assembly"}],
    "notes": ["Base and shade geometry checked against the approved dimensions."],
    "compare": [{"a": "concepts/B.png", "a_basis": "concept", "a_label": "Approved concept", "b": "renders/assembly.png", "b_basis": "final", "b_label": "Delivered CAD", "caption": "Matched view"}]
  },
  "history": [
    {"revision": "CAD R1", "date": "2026-10-06", "summary": "Built the approved base and shade."},
    {"revision": "CAD R2", "date": "2026-10-07", "summary": "Moved the cable exit rearward for assembly access."}
  ],
  "board_history": [{"revision": "R3", "date": "2026-10-07", "summary": "Added a cable-route section snapshot."}]
}
```

`stage` is `proposal`, `blockout`, `structure`, `detail`, `delivery` or `final`. A proposal may omit `viewer`; renders are still required. A CAD delivery should supply the viewer when supported. `detail`, `delivery` and `final` require at least one final review render and a final snapshot on every element. A visual-model delivery can use snapshots rendered from its delivered model; `final` describes provenance, not an engineering certification.

```json
{
  "project": "Desk lamp", "revision": "CAD R2", "front": "-Y",
  "elements": [{
    "id": "E1", "name": "Base", "value": "Ø180 × 12 mm",
    "source": "provided", "approval": "agreed", "status": "verified",
    "anchor": [0, -90, 6],
    "image": "renders/base.png", "image_basis": "final", "image_caption": "Base from delivered CAD",
    "notes": ["Diameter measured after reimporting the STEP."],
    "images": [{"src": "renders/base-section.png", "basis": "final", "caption": "Cable passage section"}],
    "assumptions": ["Nominal dimensions; manufacturing tolerances not specified."],
    "questions": [],
    "deferrals": []
  }]
}
```

Evidence bases: `concept` (appearance only), `cad` (preliminary model), `final` (delivered model), `photo` (supplied reference). Require `image_basis` on each element; never infer evidence from approval or stage. Extra `images` and comparisons each need explicit bases too. `notes`, `assumptions` and `questions` are short string lists. A deferral is an object with `question`, `assumption`, and `approval_record` quoting/paraphrasing the user's actual authorization with a date when known. Do not invent owners, dates or approval.

Source, approval and status remain independent. `approval`: `open`, `agreed`, `assumed`; `status`: `pending`, `modeled`, `verified`. Keep proposed packaging geometry and hardware qualification distinct in the wording. At final geometry delivery unresolved physical checks can remain recorded; they do not magically become verified when the user accepts the concept.

## Migrate an older job

Do not silently drop legacy content. The generator rejects schema v1 and legacy top-level `sections`, `brief`, `next`, `decisions`, `open`.

- Move concept renders, recommendation and overall comparisons into `review`.
- Move brief requirements, layout/process checks, corner details and questions into the affected elements' notes/images/assumptions/questions/deferrals. If a check spans the assembly, use the appropriate assembly element.
- Supply an inspected `image` and `image_basis` for every element, including previously unillustrated ones.
- Convert actual decisions/revisions to concise `history` entries; do not relabel an open question as a decision.
- Put board-only changes in `board_history`. Preserve old board/source files in the job folder and validate the replacement before delivery.
