---
name: design-icl
description: v1.0 · Design and revise process-specific inspection check lists (ICLs) from STEP files or dimensioned drawings. Supports Laser, Bending and Welding, with HTML review and pinned comments before company-template Excel delivery. Use for inspection check lists, QC/inspection check sheets and ICL rules. Not for weld or checking fixtures (use design-fixture), shop drawings (use draft-drawing) or general CAD modeling (use design-engineer).
---

# Design ICL

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

## Change boundaries

- “Change this sheet” edits the job only. “Change the Laser rule/default/template” edits only `processes/laser/`, likewise for other processes. Do not read or rewrite sibling processes for that change.
- Change common files only for explicitly shared behavior or a demonstrated shared defect. Keep a process-specific presentation preference in that process's rules/job settings.
- If feedback's permanence is unclear, apply it to the current job; ask before promoting it to a permanent rule. Sample dimensions never become defaults.
- Ordinary generation does not modify this skill. Keep original sources, spec, previews, comments, approval and deliverables together in the job directory. No publishing or git actions are implied.

## Workflow

1. Inspect the supplied form and exact CAD/drawing. Establish units, faces, bends, physical contact points and gauge access. Bounding boxes, pictures and meshes alone do not establish functional dimensions. Use an available exact CAD kernel; if unavailable, request a dimensioned drawing or retain an explicitly unmeasured draft. Never invent nominals/tolerances.
2. Select a small useful set of process checks. Save `spec.json`: stable check keys, displayed IDs, nominal/tolerance, gauge, source and measurement method. Keep keys stable through renumbering. Unknown acceptance criteria stay `TBC`; never claim production readiness from document approval.
3. Generate CAD-derived `geometry.svg` containing wireframe geometry only. Specify dimension endpoints, offsets and badge positions in the spec. Dimension numbers come directly from checks. Moving badges changes presentation only; changing endpoints/nominals requires checking geometry again.
4. Run `python scripts/icl.py preview JOB/spec.json`. Inspect the complete `preview-rN.html` before sharing. It is self-contained and strictly below 1,000,000 bytes. Simplify redundant geometry if oversized; do not omit required views/checks or hide dependencies behind network links.
5. Users pin comments to rows/drawing locations and copy/export them to chat. Comments are feedback, never executable patches or approval. Match process/revision/stable key, apply the requested job edits, increment revision and regenerate. Do not generate final Excel during preview iteration.
6. On explicit approval of the current preview or a request to finalize, record actual user wording: `python scripts/icl.py approve JOB/spec.json --note 'user wording'`, then `python scripts/icl.py export JOB/spec.json`. Changed spec, geometry, source, template or preview invalidates approval. An edit request, screenshot or silence is not approval. Approval authorizes document generation, not physical validation.
7. Reopen Excel and inspect values, IDs, image, company form/logo and print layout against the approved preview. HTML approximates the form's screen layout; final pagination still requires inspection. Correct export defects within approved content without re-asking. Link the workbook and requested preview.

## Execution and portability

Preview uses Python standard library. Excel export uses CairoSVG and lxml (`scripts/requirements.txt`) plus the system Cairo library (`brew install cairo` on macOS, `libcairo2` on Debian/Ubuntu). Run export and tests through
`uv run --no-project --python 3.12 --with-requirements scripts/requirements.txt python …`; without `uv`, `pip install -r scripts/requirements.txt` into an isolated environment. On macOS with Homebrew, prefix the command with `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` if CairoSVG reports `no library called "cairo-2"`. Never modify another skill's environment. If export dependencies are unavailable, report that limitation; do not claim export completion.

The exporter patches the selected OOXML template, embeds a PNG rendered from the approved SVG and strips leftovers of the template's source part (unused text, images, thumbnail, author properties). It supports the included Laser/Bending mappings. Other templates require an inspected mapping; never silently use another process's form or truncate rows. Welding can preview now but needs a supplied form/mapping before export.

Carry the entire skill folder and job sources/spec/geometry to another assistant or cloud session. Paths are relative. The HTML alone is not the editable CAD evidence. No other skill or online viewer is required.

The bundled example is one measured U-channel, not a general bending rule, and contains no user approval. Run `python -m unittest discover -s tests -v` in this folder through the same `uv run` command. Test approvals and temporary outputs never authorize delivery of a user job.
