---
name: draft-icl
description: v1.2 · Draft and revise process-specific inspection check lists (ICLs) from STEP files or dimensioned drawings. Supports Laser, Bending and Welding, with HTML review and pinned comments before company-template Excel delivery. Use for inspection check lists, QC/inspection check sheets and ICL rules. Not for weld or checking fixtures (use design-fixture), shop drawings (use draft-drawing) or general CAD modeling (use design-engineer).
---

# Draft ICL

Inspect characteristics created or changed by the selected manufacturing operation, without repeating accepted upstream checks.

## Read only the active process

Identify Laser, Bending or Welding from the request; ask if unclear. For several processes, create separate jobs. Read [presentation](common/presentation.md), [job format](common/job-format.md), and exactly one of [Laser](processes/laser/rules.md), [Bending](processes/bending/rules.md), [Welding](processes/welding/rules.md). Load only its template/layout when exporting.

## Default tolerances

Company defaults for linear dimensions; explicit drawing tolerances take precedence (flag conflicts):

- Laser cut: ±0.2 mm.
- Bending: ±0.5 mm.
- Welding and any other process: ±0.5 mm.
- Holes for clinch fasteners: ±0.2 mm, whichever process the ICL covers.

Angles, geometric (parallelism, flatness) and visual criteria have no default; they need their own specification or stay `TBC`.

Display nominal angles to **one decimal place** in the table and drawing (145.757… → 145.8°, 105 → 105.0°). Retain the measured value in the spec and use it for CAD/contact validation. Preserve explicit tolerance precision.

## Change boundaries

- “Change this sheet” edits the job only. “Change the Laser rule/default/template” edits only `processes/laser/`, likewise for other processes. Do not read or rewrite sibling processes for that change.
- Change common files only for explicitly shared behavior or a demonstrated shared defect. Keep a process-specific presentation preference in that process's rules/job settings.
- If feedback's permanence is unclear, apply it to the current job; ask before promoting it to a permanent rule. Sample dimensions never become defaults.
- Ordinary generation does not modify this skill. Keep original sources, spec, previews, comments, approval and deliverables together in the job directory. No publishing or git actions are implied.

## Workflow

1. Inspect the supplied form and exact CAD/drawing. Establish units, faces, bends, physical contact points and gauge access. Bounding boxes, pictures and meshes alone do not establish functional dimensions. Use an available exact CAD kernel; if unavailable, request a dimensioned drawing or retain an explicitly unmeasured draft. Never invent nominals/tolerances.
2. Include one `Check part to Reference sample | Reference Sample | Visual` row for each part and operation. Require a designated physical sample and keep its identity/revision TBC until established; CAD review does not validate the sample. Select a small useful set of process checks. Use operator equipment: Vernier for reachable linear contacts, Protractor for angles and Visual for the configured edge check. The included company profiles allow these three gauges. Add equipment to job `available_gauges` only after availability is established; verify access before changing a gauge. Keep missing flat/program information in review notes. Add parallelism/twist/condition checks only for a defined drawing, function or inspection requirement. Save stable keys, numeric nominal/tolerance, gauge, evidence and full measurement method. Displayed IDs are derived sequentially from check order on every preview/export. Unknown acceptance criteria stay `TBC`; never silently accept a nominal as a limit.
3. Generate CAD-derived wireframe `geometry.svg`. Specify physical dimension contacts, offsets and badges in the spec. Use concise numeric captions through `feature`, `size_checks` and `diameter` (see job format). Use grouped `drawing.views` to arrange the complete reference and details inside the drawing panel; transform geometry and annotations together. Use red annotations, separate ID badges and concise measured values. Use filled arrowheads for linear dimensions and angle arcs. Route square horizontal/vertical leaders from a clear side, including below the part when that is simpler. Resolve the renderer’s label/line clearance failures after view packing. See presentation for sizing at Excel print scale. Changing endpoints/nominals requires checking geometry again.
4. Run `python scripts/icl.py preview JOB/spec.json`. Inspect the complete `preview-rN.html` before sharing. It is self-contained and strictly below 1,000,000 bytes. Simplify redundant geometry if oversized; do not omit required views/checks or hide dependencies behind network links.
5. Use the same comment interaction as design-fixture/design-engineer: **Comment mode**, click to place a **C1/C2** pin, type in its anchored box, click the pin to collapse/reopen, and delete with automatic renumbering. Use a compact right-hand card with title, process/revision, Comment mode and Copy comments. Show two or three short `to_confirm` items; hide empty comments/status. Omit the download button and repeated guidance. Keep anchored pin editors on the review target, as in design-fixture. Support both check rows and drawing locations. **Copy comments** produces readable text to paste into chat; keep process, revision, digest, stable check keys and normalized drawing positions in the locally persisted structured comments. If clipboard access is blocked, select the complete text inline for Ctrl+C/⌘C. Users copy comments to chat. Comments are feedback, never executable patches or approval. Match process/revision/stable key, apply the requested job edits, increment revision and regenerate. Do not generate final Excel during preview iteration.
6. On explicit approval of the current preview or a request to finalize, record actual user wording: `python scripts/icl.py approve JOB/spec.json --note 'user wording'`, then `python scripts/icl.py export JOB/spec.json`. Changed spec, geometry, source, template or preview invalidates approval. An edit request, screenshot or silence is not approval. Approval authorizes document generation, not physical validation.
7. Reopen the exported workbook and inspect values, sequential IDs, uniform 10 pt / 24 pt checkpoint rows, full SOP wording, image, logo and footer against the preview. The exporter compacts unused check rows and saves A4 landscape, main print area fitted 1 × 1 and the main sheet active; history uses landscape. Verify actual rendered pagination. The generated `.print-settings.json` records file-level settings with Windows Excel verification false. A landscape XML flag or LibreOffice/PDF result does not establish the Windows Excel printer dialog. Record Windows confirmation only for the exact current workbook when supported by user/application evidence. Treat application re-save as an optional compatibility attempt until Windows confirms it. Correct authorized export defects without repeating approval. Link the workbook and requested preview.

## Execution and portability

Preview uses Python standard library. Excel export uses CairoSVG and lxml (`scripts/requirements.txt`) plus the system Cairo library (`brew install cairo` on macOS, `libcairo2` on Debian/Ubuntu). Run export and tests through
`uv run --no-project --python 3.12 --with-requirements scripts/requirements.txt python …`; without `uv`, `pip install -r scripts/requirements.txt` into an isolated environment. On macOS with Homebrew, prefix the command with `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` if CairoSVG reports `no library called "cairo-2"`. Never modify another skill's environment. If export dependencies are unavailable, report that limitation; do not claim export completion.

The exporter patches the selected OOXML template, embeds a PNG rendered from the approved SVG and strips leftovers of the template's source part (unused text, images, thumbnail, author properties). It supports the included Laser/Bending mappings. Other templates require an inspected mapping; never silently use another process's form or truncate rows. Welding can preview now but needs a supplied form/mapping before export.

Run `python scripts/verify_print.py JOB/PROCESS-icl-rN.xlsx` for saved settings. With an available spreadsheet application, use `--render` (optional `--office PATH`) to check A4 landscape pages, all checkpoint text and the signing footer on the first page. It retains `.print-preview.pdf` for visual inspection; text extraction does not prove absence of overlaps/clipping. Verification reports remain bound to the exact workbook SHA-256 and never claim Windows Excel confirmation from another application's result.

Carry the entire skill folder and job sources/spec/geometry to another assistant or cloud session. Paths are relative. The HTML alone is not the editable CAD evidence. No other skill or online viewer is required.

The bundled example is one measured U-channel, not a general bending rule, and contains no user approval. Run `python -m unittest discover -s tests -v` in this folder through the same `uv run` command. Test approvals and temporary outputs never authorize delivery of a user job.
