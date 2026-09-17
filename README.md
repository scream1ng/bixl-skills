# Backwell IXL fixture skills

Reusable CAD workflows for designing and reviewing manufacturing fixtures.

| Skill | Folder | Purpose |
|---|---|---|
| Design Check Fixture | [design-check-fixture](design-check-fixture/SKILL.md) | Checking fixtures with 3 mm nominal flange gaps, 2.5/3.5 mm GO/NO-GO gauges, laser-cut ribs or printed bodies, and explicit restraint, full-tool access and profile reviews. |
| Design Weld Fixture v8 | [design-weld-fixture-v8](design-weld-fixture-v8/SKILL.md) | Welding fixtures with 3-2-1 locating, suitable hole/slot locators, manual pin release and practical 5 mm tab-and-slot construction. |

## Using the skills

Copy or install the complete skill folder into your assistant's skills directory, then invoke the skill with the part or assembly STEP file and any drawings or requirements. Start with that folder's `SKILL.md`. Keep its `scripts`, `references`, `assets`, `examples`, `tests` and `agents` folders together.

Each skill is self-contained and includes its own GH-201-B hardware STEP model. The shared foundation is currently copied into both skills; changes do not automatically propagate between them.

For local script use, install the dependencies in the selected skill's `scripts/requirements.txt` in a suitable Python environment. Follow the skill's workflow and verification instructions. Example models are software test coupons, not approved production fixtures. CAD verification, fabrication readiness, physical calibration and inspection validation are separate decisions.
