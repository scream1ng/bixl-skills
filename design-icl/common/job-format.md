# Job data (version 1)

Keep `spec.json`, unmodified source CAD/drawings and `geometry.svg` together. Paths in the spec are relative to its directory. Runtime outputs belong here, never inside the installed skill. On a change, increment `revision`; keep check `key` values stable even if displayed IDs change.

Use `examples/bending/spec.json` as a structural example only. Replace its sources/measurements/geometry with the actual job. Required fields:

- `version: 1`, `process: laser|bending|welding`, positive integer `revision`.
- `part`: `number`, `name`, ISO `date`, `drawing_number`, `frequency` (explicit `TBC` when unknown).
- `sources`: objects with relative `path` and full `sha256`. The hash locks the evidence; it does not prove that the measurements are correct.
- `checks`: stable `key`, displayed `id`, `description` without the appended nominal, `gauge`, evidence `source`, practical `method`; optional numeric `nominal`, numeric nonnegative `tolerance`, `unit: mm|deg`, or textual `limits`. Missing limits become `TBC`. Never encode a nominal as a formatted number string.
- Each Laser check has `group: setup|hourly`. Bending defaults to `group: main`. Keep groups in their mapped order. The standard template permits 3 setup + 7 hourly checks or 8 bending checks. Extend an inspected mapping/form when more checks are necessary; do not drop checks to fit.
- `drawing`: integer `width`, `height`, relative geometry path and `dimensions`. Geometry root viewBox must be `0 0 WIDTH HEIGHT`. Use only vector shapes/groups with explicit attributes; no text, scripts, styles, links or raster images.
- Dimension: stable check key in `check`, `kind: horizontal|vertical`, physical feature projection points `a` and `b`, dimension-line `offset`, optional numeric label `value_xy`, and separate `badge_xy`. Coordinates use SVG screen axes. Endpoints must come from the selected CAD view and measurement references, not guessed pixels. Rendering does not measure CAD.
- Angular dimension: `kind: angle`, `centre`, `radius`, `start_deg`, `end_deg`, `value_xy`, `badge_xy`; the referenced check must have unit `deg`. Angles use SVG screen coordinates; confirm sweep and actual nominal against CAD.
- Optional `layout` points to a job-local layout JSON, which points to its own relative template. Its process must match. Follow the bundled mapping format after inspecting the actual workbook; exporter supports the existing check columns B/C/E/G and a logo plus drawing panel.
- Optional `history` records prior `{date, revision, change, author}` entries. Append the previous revision when editing a job; the current `change`/`author` become the newest row. Do not import an unrelated template part's history.

Each review writes `preview-rN.html` and `drawing-rN.svg`. Approval records bind the current spec, geometry, sources, template, layout and saved preview. Do not edit HTML directly: edit the spec/geometry, bump revision and regenerate. Notes do not mutate nominal values or create an approval.

No measurement acceptance is implied by `TBC`, a matching hash, successful script execution or preview approval. Check the resulting Excel in the target application, including print layout.
