# Grilling question rounds

Adapted from Matt Pocock's `grilling` skill (github.com/mattpocock/skills, version of 2026-08-20). The method is built in here; do not call another skill. Compare with upstream occasionally.

Stage 1 of the workflow: gather the decisions the proposal needs, in as few rounds as possible. Questions stay in chat as plain text.

## Design tree and frontier

Map the job as a **design tree**: every decision branches into the decisions that hang off it (process → draft angle; mounting method → hole pattern; surface character → rib pitch and depth). The coverage checklist below gives the top-level branches.

The **frontier** is every decision whose prerequisites are already settled. Ask every **consequential** frontier decision in one round: one that changes the envelope, an interface, the layout, the surface character, the process or the scope. Routine details (minor radii, standard fasteners, cosmetic offsets, values a datasheet or standard fixes) get no question; record your recommended value in the element table as `estimated` with approval `open`, and the proposal board confirms them. For a decision that depends on another, ask the parent with your recommendation and state the default you will use for the dependent. Ask a follow-up round only when an answer opens a decision that materially changes the proposal.

Finding **facts** is your job, never the user's: measure supplied CAD, read files, inspect images and check tools yourself before asking. Only questions downstream of an unfinished lookup wait for it. The **decisions** are the user's: put each one to them with your recommendation.

The interview is done when no remaining open decision would materially change the proposal: every branch visited, nothing left silently assumed. Record the rest as `estimated` with approval `open`; the proposal board settles them. Size the interview to the job: usually one round, occasionally a follow-up. Then build the proposal without asking.

## Round format

Use exactly this shape, with a horizontal rule between questions:

```
❓ **Q1** - **<question title>**: <question body; options lettered when it is a choice; point at the option picture when it is about shape>

➡️ <your recommended answer and the one-line reason>

---

❓ **Q2** - **<question title>**: ...

➡️ ...
```

For a question about shape or style, show the option pictures (reference crops, rendered variants, sketches) with the question itself, inline or as image files, and name them ("see options A/B/C"). The design board is first shown complete, in stage 2.

## Coverage checklist (top-level branches)

Every item ends **answered** (by the user, the brief or supplied files), **assumed** (a recommendation the user explicitly accepted) or **recommended** on the proposal board, which board approval settles. Track status in the relevant element and internal working spec.

| Branch | Settle |
|---|---|
| Use and context | What the object is for, where it lives, who handles it |
| Outputs | Render, STEP, both; formats, resolution, views to deliver |
| Scale and envelope | Overall size or a reliable reference dimension; limits on width/depth/height |
| Interfaces | Mounting, mating parts, connectors, openings that must fit something; what existing geometry is protected |
| Layout and packaging | Assemblies only: which components go inside, their orientation (inlet/outlet, connector exits), functional paths (air, fluid, cable, heat, load), how each is supported and retained, assembly order and service access, and whether the body form suits the layout. Offer layout alternatives on the board when the arrangement is not obvious |
| Elements | Every visible or functional feature, one by one: presence, count, position, size, shape. Point at each in the reference ("the three slots on the left face") |
| Form and proportions | Silhouette, key ratios, edge treatment, symmetry |
| Surface character | For textures/relief: continuous blended surface or discrete features; pitch, depth, cross-section profile, how it ends at edges and openings (see concept translation) |
| Material and finish | Material, colour, texture, transparency; process when it shapes geometry |
| Hidden and unseen regions | Rear, underside, internals: copy, invent, or leave out |
| Tolerances and checks | Which dimensions are fit-critical; what must be verified |

Skip a branch only when it is irrelevant to the requested output (e.g. finish for a CAD-only bracket) and record why.

## Dependency examples

Do not ask "Which manufacturing process?" and "What injection-molding draft angle?" as two questions when molding is not yet selected; ask the process and state the draft you would use if molding is chosen. Do not ask for a hole pattern before the mounting method is settled. Do not ask for rib pitch before "continuous wave or separate ribs" is settled. Overall size and output format are independent and go in the same round.

## Changes and approvals

Honor authorization already given. Ask when a proposed fix changes the agreed envelope, a functional interface, the requested scope, the agreed surface character, or another consequential constraint: state the concrete change and its effect, with the before/after pictures on the board. Do not treat silence or an elapsed timeout as an answer to an open question.

During CAD delivery, ask only for a consequential departure from the approved proposal: envelope, functional interface, scope, mechanism, process, surface character, or a visible change to the approved look. Resolve everything else internally and record it on the final board.

An explicit instruction to proceed ("you have enough information — keep going", "use your recommendations", "continue") accepts the recommendation you showed for each open question. Mark those decisions **assumed** (`"approval": "assumed"` on affected elements), record them under the affected elements, say so in one line, and keep going. A decision you never put to the user with a recommendation is not covered and stays open.

## Unresolved engineering work

Resolve consequential inputs in chat before the next stage relies on them. If the user explicitly approves deferral, record the question, working assumption and actual approval in the affected element. Do not invent an owner or due date. Keep physical validation requirements separate from design-choice approval. A supplied process or sufficient brief needs no repeated interview, and a complete board needs no separate questions form.
