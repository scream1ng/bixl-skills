---
name: draft-sop
description: v1.0 · Draft Backwell IXL standard operating procedures (SOPs) from shop-floor photos. Dresses each photo (crop, straighten, light), adds red arrows, circles and numbered callouts, keeps text to one short line per step, and shows an HTML review with pinned comments before filling the company IXL Word template. Use for SOPs, work instructions and step-by-step photo procedures. Not for inspection check lists (use draft-icl) or process flow charts (use draft-pfc).
---

# Draft SOP

Make the picture do the work. Each step is one dressed photo, red annotations that point at the action, and one line of text.

## Rules

- **One step = one action = one photo.** If a photo shows two actions, ask for another photo or split it with two crops.
- **Text:** a real Word bullet list (`-`, sub-bullets `o`) in Century Gothic 14 pt. Max 4 bullets of ≤10 words each, verb first. Use sub-bullets (max 8) for lists, with part numbers written as `P/N – name`, e.g. `621507 – Switch`. No paragraphs, no "the", no "carefully".
- **Callouts:** numbered boxes with a leader, max 4 per photo, for spots that have no short name (e.g. the label and the scale reading). Referencing them in the text as ①② is optional. The user's own edits have dropped those references.
- **Labels first:** name a part on the photo with a `text` label (1–3 words, `P/N name` for components) placed over plain background at the photo edge, with `to` set to the point on the part. That draws the leader. Other marks: `oval` to circle a feature, `rect` for a region, `arrow` for movement (`target` names what it hits). Marks must never cover the feature they point at.
- **Aim:** each arrowhead lands well inside its part, never on an edge, the background or a neighbouring part. `preview` writes `check-rN.jpg`, a zoomed crop around every arrowhead with a crosshair and the target's name. Open it and fix every miss before sharing the preview. Most errors come from guessing coordinates off the full photo.
- **Dress:** crop tight to the work area (show hands or tooling only if they explain the action), level with `rotate`, and leave `light` on. Never alter what the part looks like: no cloning, no removing defects, no AI-generated pixels.
- **Never invent** torques, part numbers, tool names or quantities. Ask, or put them in `to_confirm`.

## When to ask

Ask in one short batch, only for what you can't see in the photos:

- `part.number`, `part.name` and `doc_no` (SOP document number, e.g. A0866), if they weren't given.
- What the action is, if the photo doesn't show it clearly.
- Specs the text needs (torque, count, gap) that you can't read from the photo.
- Format, only if the user cares. The default is A3 landscape, with steps per page picked automatically (1/2/4/8).

Otherwise draft, and list open items under `to_confirm` (max 3 shown) in the preview.

## Workflow

1. **Job folder.** Copy the user's photos into `JOB/photos/` unchanged. Write `JOB/spec.json` ([job format](references/job-format.md)) with steps in order, text and a first-guess `dress`. Look at every photo before writing its step.
2. **Prep.** Run `python scripts/sop.py prep JOB/spec.json`. View each `dressed/<key>.grid.jpg`; the yellow grid is at 0.1 intervals. Fix crop and rotate, rerun, then place marks and callouts in fractions of the **dressed** photo.
3. **Preview.** Run `python scripts/sop.py preview JOB/spec.json`. View `check-rN.jpg`: every crosshair must sit inside the named part. Fix any misses and rerun. Screenshot `preview-rN.html` if a browser is available, check that no label hides its feature, then share the HTML.
4. **Comments.** The user clicks Comment mode, pins C1/C2 on a photo or step text, then Copy comments into chat. Apply them to `spec.json`, increment `revision`, then run prep and preview again. Comments are feedback, not approval.
5. **Approve.** Only on explicit approval ("looks good", "finalize", "make the Word file"), run `python scripts/sop.py approve JOB/spec.json --note '<their words>'`. Any change to the spec or photos makes the approval stale.
6. **Export.** Run `python scripts/sop.py export JOB/spec.json --render`. The file is named `<doc_no> - <part no> <part name>.docx`, e.g. `A0866 - 36611 Tastic Luminate Heat Module.docx`. It fills the IXL template (`assets/templates/`) with the photos and native, editable Word shapes, then checks the page count, photos and header. View the rendered PNGs before delivering the `.docx`. A `WARNING … pages` result means the header title wrapped onto a second line, so set a shorter `part.title`.

## Setup

Needs Python 3.10+ with `pip install python-docx Pillow`. `--render` needs LibreOffice, `pdftoppm` and `pdfinfo`. Page counts are only realistic when Century Gothic or URW Gothic (its metric twin, from `fonts-urw-base35` or github.com/ArtifexSoftware/urw-base35-fonts) is mapped by fontconfig. Without it the render says the page count is unreliable. Paths in the spec are relative to it. Job outputs stay in the job folder, never in the skill.

`scripts/fill.py` is the BIXL Studio SOP engine (`bixl-studio/modules/sop/fill.py`) with two portrait fixes: it finds the step table after the PPE table and writes the title into the last header cell. Keep the two in sync.

Tests: `python -m unittest discover -s tests -v`.
