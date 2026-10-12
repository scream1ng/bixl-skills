# Validation and delivery

## Before presenting HTML

- Reconcile the graph with BOM/route evidence: item codes, owning levels, input consumption, operation order, branch joins, hardware and packaging.
- Preserve unknowns and provisional interpretations as concise review decisions; never silently convert them into facts.
- Verify the original form frame, box spacing, symbol selections/styles and boxed legend. Keep every connector segment horizontal or vertical, with one shared main-route axis.
- Inspect the whole page for text/image/arrow overlaps, clipped labels, disconnected ends and readable size. Keep complete required isometrics outside boxes by default.
- Confirm self-contained HTML below 1,000,000 bytes, current logo, complete pins/copy interaction, hidden empty state and no download-comment button.

## Before delivering Excel

Confirm recorded user authorization of the current content. `preview`, `approve` and `export` bind the spec, original BOM, optional source CAD/drawing, image bytes, reference form, exporter and logo by hashes. Keep temporary test approvals separate. Correct already-authorized output defects without another permission round; changes to process content need current authorization.

Reopen the exported ZIP/workbook and verify:

- Exact item codes and all displayed text, operation sequence, branch topology and carton details.
- Full A1:X52 original grid, border cells, original row/column dimensions, paragraph spacing and symbol styles, plus editable native shapes/connectors.
- Current logo, expected CAD picture count, exact approved picture bytes and aspect ratios; no stale reference part pictures or sample author metadata.
- Macro-free XLSX, active main PFC, A4 portrait, print area A1:X52, source margins/centering, 1 × 1 fit and single-sheet page number 1.

Render with an available spreadsheet application and inspect the entire printed page for pagination, symbols, borders, all labels and image placement. The exporter writes a hash-bound `.print-settings.json`. XML settings, text extraction and a LibreOffice/PDF render do not establish Windows Excel printer-dialog confirmation; leave that flag false unless evidence confirms this exact workbook.

If a required dependency or renderer is unavailable, report the concrete missing capability and the useful output completed. Do not claim a workbook was generated or visually checked when it was not. No manufacturing/engineering qualification follows from a document approval.

## Supported boundaries

The bundled single-sheet exporter supports five measured main-route slots and simple independent side routes. It rejects overlapping boxes, out-of-page placements, cycles, broken node references, changed evidence and unapproved export. It does not automate arbitrary multi-page layouts or prove the correctness of ambiguous route/consumption links. Implement and inspect an additional-sheet mapping for larger jobs; never omit source items or shrink the form silently. Visual review still owns connector/image clearance and print legibility.

Run bundled parser/source-binding/native-drawing regressions with `python -m unittest discover -s tests -v`, and comment-controller checks with `node tests/test_comments.cjs`. Use isolated job directories. Test authorization wording stays in those directories and never authorizes delivery of a user job.
