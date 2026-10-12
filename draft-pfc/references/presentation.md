# PFC presentation

## Controlled form

Use `assets/reference-pfc.xlsx` only for layout and styles, and `assets/logo.png` for the company logo. The form is a masked copy: header, item codes, author and part pictures were replaced with placeholders (PART-NO, SIDE-PART, MAT-CODE, HW-CODE, CARTON-CODE, blank images), and its macros were removed. `scripts/form.py` finds sample shapes by that placeholder text, so keep it if the form is replaced. Keep the bundle independent of draft-icl/design-fixture. Never reuse the reference's author, dates, bracket/stud photos or material/process claims for another job.

Use the form geometry extracted by `scripts/form.py`: original row/column sizes, A1:X52 grid, complete outside border, measured main/side box slots and boxed legend. Preserve blank border-carrying cells, including A/X sides and row 52. Keep Arial 10 pt operation text, italic/underlined operation numbers and original paragraph settings; PACK retains its blank-paragraph spacing. Use stage-specific original symbol selection, placement, proportions, gold FFC000 fill and blue 385D8A outlines. The reference's pasted PACK circle is recreated as an editable ellipse at its measured bounds.

Use blue 4F81BD open-arrow connectors. Keep all main-route connections on one vertical axis through the overlapping box widths, even when original box centres differ. Side connections use horizontal/vertical segments and right-angle turns. Attach ends to box boundaries. Preserve legible gaps; arrows must not cross text, symbols or images. Check every join and direction visually.

Keep A4 portrait by default. Do not inherit draft-icl's landscape orientation. Original margins/centering and the 1 × 1 print fit belong to Excel. Conversation revision numbers are not form page numbers. The HTML review shows the same process scene and image bytes; Excel owns the original worksheet header/grid.

## Isometric placement

Keep process boxes compact. Put the formed main part in clear middle space near Bend, the small secondary component at right near its own route, the stud/hardware left and the finished assembly bottom right near Finish/PACK. Prefer pictures beside/around boxes; put one inside only when requested. Keep the small component visibly smaller than the main part. Views illustrate shape, not a common measurement scale.

Record mapping to stable nodes and inspect clearances against all boxes, arrows, other pictures and the legend. Preserve aspect ratios/transparency in both outputs. Use the drawing's finish for the assembly, with readable lighting; never choose a finish merely for appearance. Follow isometric-views.md for exact source geometry and rendering.

## Review card and revisions

Use one right-hand card with title, part/revision, Comment mode and Copy comments. Put only concise item-specific unresolved decisions under To confirm; retain explanations/evidence in the spec. Do not display generic assumptions, repeated approval instructions, the word “none”, empty status/comment lists or Download comments. Show one short placement hint while Comment mode is active.

Use numbered anchored pins with direct editing, collapse/reopen and deletion/renumbering. Keep readable comment text/node names in the list. Persist revision, fingerprint, node key and normalized position. If local storage or clipboard is blocked, retain usable editing and selectable text. The user pastes copied feedback into chat; comments do not execute changes or constitute approval.

Complete required graphics and flow in one preview. Inspect all text and connections before sharing; do not use the user's review to find defects already visible locally. Match incoming feedback to revision/fingerprint/key, preserve the graph evidence and increment the revision. Keep source notes and unresolved decisions outside the printed diagram.
