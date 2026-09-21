# Backwell IXL fixture skills

[Design Fixture](design-fixture/SKILL.md) designs weld and checking fixtures from a STEP file or dimensioned drawing.

```mermaid
flowchart LR
    A[STEP / drawing] --> B[Datum preview] -->|user OK| C[Concept] -->|5 checks pass| D[Preview] -->|user: finalize| E[Package]
```

Each gate loops back until it passes. The 5 checks: cap tabs, rib width, cross ribs, clamp plate size, straight unload. A failed check stops the concept with no preview.

Default construction is 5 mm laser-cut tab-and-slot ribs. Blocks (weld) and printed solid (check) are explicit alternatives. Finalizing generates the package; it is not engineering approval.

## Install

Copy the whole [`design-fixture`](design-fixture/) folder into the assistant's skills directory. For local scripts, install [`scripts/requirements.txt`](design-fixture/scripts/requirements.txt) (OCP 7.8.x).

## Versions

| Tag | Change |
|---|---|
| `v1.2.4` | Current, not tagged yet. Concept stops on basic check failures, including the new unload check; preview about 60% smaller; `spec_patch.py` for small spec edits. |
| [`v1.2.3`](../../tree/v1.2.3) | Standard clamp mount plate, cross-support check, single compressed `preview.html`. |
| [`v1.2.2`](../../tree/v1.2.2) | Comment pins in datum and concept previews. |
| [`v1.2`](../../tree/v1.2) | Generated cap tab-and-slot joints. |

Tag only when `python -m unittest discover -s tests` passes in `design-fixture/`.
