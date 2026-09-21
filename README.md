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

Versions and notes: [Releases](../../releases). Release only when `python -m unittest discover -s tests` passes in `design-fixture/`.
