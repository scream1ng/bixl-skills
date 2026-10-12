# Job format and commands

`spec.json` is the editable job authority. Keep paths relative to its folder. The import command creates a fresh job and will not overwrite an existing one.

- `schema_version`, `revision`, `number`, `name`, `plant`, `issued_by`, `original_date`, `revision_date`: header and revision data. Dates are ISO YYYY-MM-DD or null; do not copy sample dates. Plant and issuer default to TBC until supported by the job input or user; do not copy them from the sample form.
- `source`: relative BOM path, SHA-256 and sheet name.
- `nodes`: stable key, item code, label, kind, source_rows; operations add family/op/bom_key and the owning component quantity/unit when ea/each consumption and lot establish them; items add quantity/unit/parent. Pack nodes keep their complete `packaging` items.
- `edges`: `from` and `to` stable node keys. Verify physical joining stage.
- `operation_numbering`: record the proposed-route basis, increment, independent-route restart and source (null until supplied). Supplied route IDs replace the proposal with explicit source/evidence.
- `main`: ordered operation keys for the main route. Routes/branches are drawn from the graph, not sorted by item codes.
- `issues`: stable key, full text and optional concise summary for unresolved facts or provisional interpretations. Show concise decisions in the review card and retain full notes in the spec. Resolve only from actual evidence/user input.
- `source_rows`: all extracted BOM records, preserving source row and sheet.
- `layout.boxes`: optional mapping from node key to [x,y,width,height] in measured reference-form pixels. Used to revise placement; graph quantities/meaning do not change.
- `nodes[].display_lines`: optional concise multiline display preserving the same source facts; `nodes[].symbols` can retain stage-specific source selections such as Pack having Operation and Storage only.
- `history`: revision, requested change and evidence. Increment revision for content changes.
- `preview`: current revision HTML name/hash and fingerprint. Managed by preview command.
- `approval`: exact wording, UTC time, spec/source/template/script fingerprint and HTML hash. Managed by approve command.

- `additional_sources`: relative CAD/drawing paths and SHA-256 values, verified before approval/export.
- `images`: mapping of stable image role keys to `path`, `sha256`, `node_key`, `[x,y,width,height]` in `box`, optional `within_node`, `caption`, render settings and evidence. Use PNG files with transparency. Image boxes preserve aspect ratio in SVG and Excel. Images inside their parent node must fit entirely; external images must avoid every process box. Keep copied feedback bound to the mapped node and normalized image position.

PNG bytes are embedded directly in the self-contained HTML and in native Excel picture objects. Changing image/source bytes invalidates approval; update evidence hashes and regenerate before recording a new approval. The spec retains the exact solid selections and camera/finish choices for rerendering. Single-sheet export uses the five measured process slots in the supplied form plus side routes. More stages or complicated branches require an inspected extra-page mapping, not a silently stretched form. The entire source A1:X52 grid is retained. Overlapping boxes/cycles/missing references fail rather than generating silently broken charts. Connector intersections require visual review.

```bash
python scripts/pfc.py import "PART-NO - BOM.xlsx" --job JOB
python scripts/pfc.py preview JOB/spec.json
# User reviews preview.html, pastes comments, and explicitly approves its current revision.
python scripts/pfc.py approve JOB/spec.json --note "approve"
python scripts/pfc.py export JOB/spec.json
```

Changes to content, source, bundled exporter or HTML invalidate the binding. Do not reuse an approval after edits. Keep test jobs separate and remove their approval before ever promoting them to a user job.
