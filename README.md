# BIXL Skills

Backwell IXL assistant skills. Install a skill by copying its whole folder into the assistant's skills directory.

| Skill | Purpose |
|---|---|
| [design-fixture](#design-fixture) | Weld and checking fixtures from a STEP file or dimensioned drawing |
| [draft-drawing](#draft-drawing) | Draft A3 shop drawing of a sheet-metal part or weldment from a STEP file |

## design-fixture

[SKILL.md](design-fixture/SKILL.md) · local scripts need [`scripts/requirements.txt`](design-fixture/scripts/requirements.txt) (OCP 7.8.x)

![Stage gates](flow.svg)

The checks: cap tabs, rib width, cross ribs, clamp plate size, straight unload, pin clearance, brace merge, flange coverage (checking fixtures). A failed check stops the concept with no preview.

Default construction is 5 mm laser-cut tab-and-slot ribs. Blocks (weld) and printed solid (check) are explicit alternatives. Finalizing generates the package; it is not engineering approval.

### Versions

| Release | Change |
|---|---|
| [`v1.2.6`](../../releases/tag/v1.2.6) | Printed checking gauge defaults and reference build; one-command `revise`; datum review kept on rib/clamp-body edits; near-flat spline faces checked; about 10 KB less reading per concept. |
| [`v1.2.5`](../../releases/tag/v1.2.5) | Brace merge and flange coverage checks; datum preview shows sheet features checked or not; re-exported STEP keeps the datum review; clearer tab errors. |
| [`v1.2.4`](../../releases/tag/v1.2.4) | Concept stops on basic check failures, including new unload and pin clearance checks; preview about 60% smaller; `spec_patch.py` for small spec edits. |
| [`v1.2.3`](../../releases/tag/v1.2.3) | Standard clamp mount plate, cross-support check, single compressed `preview.html`, restored nester. |
| [`v1.2.2`](../../releases/tag/v1.2.2) | Comment pins in datum and concept previews. |
| [`v1.2.1`](../../releases/tag/v1.2.1) | Removes a duplicate nested skill folder. |
| [`v1.2`](../../releases/tag/v1.2) | Generated cap tab-and-slot joints. |
| [`v1.1`](../../releases/tag/v1.1) | First combined design-fixture skill. |

## draft-drawing

[SKILL.md](draft-drawing/SKILL.md) · local scripts need [`scripts/requirements.txt`](draft-drawing/scripts/requirements.txt) (OCP 7.8.x, matplotlib)

STEP file in, measured numbers out: overall size, flanges, bends, hole and slot positions, and total steel weight. Every number comes from exact OCP geometry, never a picture.

`workflow.py preview` writes a single self-contained `preview.html` (3D plus one tab per sheet) with comment pins. Comments are applied by editing `drawing.json` and re-running the preview. The A3 PDF is only generated on an explicit request, and `finalize` refuses if the STEP or settings changed since the last preview. What is not measured — flat pattern, tolerances, GD&T, welds, threads — is listed as NOT DIMENSIONED, never passed off as checked.

Release tags for this skill are prefixed `draft-drawing-`.

---

Release a skill only when `python -m unittest discover -s tests` passes in its folder.
