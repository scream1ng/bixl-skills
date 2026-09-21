# BIXL Skills

Backwell IXL assistant skills. Install a skill by copying its whole folder into the assistant's skills directory.

| Skill | Purpose |
|---|---|
| [design-fixture](#design-fixture) | Weld and checking fixtures from a STEP file or dimensioned drawing |

## design-fixture

[SKILL.md](design-fixture/SKILL.md) · local scripts need [`scripts/requirements.txt`](design-fixture/scripts/requirements.txt) (OCP 7.8.x)

![Stage gates](flow.svg)

The 6 checks: cap tabs, rib width, cross ribs, clamp plate size, straight unload, pin clearance. A failed check stops the concept with no preview.

Default construction is 5 mm laser-cut tab-and-slot ribs. Blocks (weld) and printed solid (check) are explicit alternatives. Finalizing generates the package; it is not engineering approval.

### Versions

| Tag | Change |
|---|---|
| `v1.2.4` | Current, not tagged yet. Concept stops on basic check failures, including the new unload and pin clearance checks; preview about 60% smaller; `spec_patch.py` for small spec edits. |
| [`v1.2.3`](../../tree/v1.2.3) | Standard clamp mount plate, cross-support check, single compressed `preview.html`. |
| [`v1.2.2`](../../tree/v1.2.2) | Comment pins in datum and concept previews. |
| [`v1.2`](../../tree/v1.2) | Generated cap tab-and-slot joints. |

Tag only when `python -m unittest discover -s tests` passes in `design-fixture/`.
