# Laser

- Inspect cutting results: hole/slot sizes, flat hole positions, cut profile/blank size and specified burr/dross/material conditions.
- Default tolerance: ±0.2 mm (see SKILL.md defaults). Do not apply it to stock thickness or visual criteria.
- Use an approved flat pattern/cutting drawing. A formed STEP alone does not establish blank dimensions, bend allowance or flat hole positions. Do not unfold with guessed tooling parameters.
- Do not add formed flange heights or assembly distances. Keep IDs, dimensions, datum and gauge contacts consistent.
- Preserve start-of-run and hourly groups. Do not merge inspection frequencies or invent technology/tip/material settings.
- Keep unavailable flat pattern/program approvals in the review note; include an operator flat-position/profile check only with an approved drawing and a practical specified method.
- Use Vernier for accessible stock thickness and cut dimensions. A pin gauge or other tool needs confirmed operator availability. The included company profile appends one final hourly check: `Ensure no harmful burrs, sharp edges, laser daggs etc | SOP008 | Visual`. Keep the SOP reference; its detailed criteria come from the company's controlled SOP, not CAD. A matching existing quality row keeps its stable key and is not duplicated.

Use `template.xlsx` and `layout.json`. Geometry-specific sample hole sizes are not defaults.
