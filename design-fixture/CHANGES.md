# design-fixture v1.8.2 (includes v1.7, v1.8, v1.8.1)

v1.7
- scripts/export_step.py: assembly STEP is one named root assembly (opens in Rhino and SolidWorks).
- SKILL.md: finalize delivers one zip; never hand-edit exports after the build.

v1.8 – build-order etching (default)
- scripts/nest_dxf.py: `nest.etch_style: "build_order"` (default)
  - every plate etched with its fit-up number in its middle (braces first, then uprights, then caps; follows assembly_layers)
  - base repeats the number beside each of that plate's tab slots, along the slot
  - numbers containing 6 or 9 are underlined; plate names are no longer etched
  - order stored per plate (`build_order`) and in verification `measurements.cutting_audit.build_order`
  - `etch_style: "part_numbers"` brings back the old names + part numbers
  - etch_marks may contain plain lines: `{"path": [[x, y], ...]}`
- references/laser-cut-construction.md: etching rule updated.
- SKILL.md: zip also carries BUILD-ORDER.txt.
- tests/test_nest_dxf.py: 3 old tests pinned to "part_numbers" style (same checks); 3 new tests for build order,
  underlines and explicit-mark override. Full suite 220/220 OK.

v1.8.1 – continuous etch digits
- scripts/nest_dxf.py: vertical stroke segments b, c, e, f now meet at mid-height (0.50 instead of 0.48/0.52),
  so connected strokes join into one polyline. Digits 1, 2, 5, 6, 7, 9 etch as a single continuous line
  (0 and 8 stay split so no etch forms a closed contour; 6/9 underline stays a separate stroke).

v1.8.2 – cap numbers on cheeks
- scripts/nest_dxf.py: in build_order etching, each cheek carrying a clamp cap or pin pad (a cap-tab joint) also gets
  the cap's number at the seat height (4 mm, 3.5 mm fallback) just below its cap tab, clear of the cheek's own number.
  No room is an error, never a silent skip.
- references/laser-cut-construction.md: documents the cheek marks.
