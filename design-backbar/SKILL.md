---
name: design-backbar
description: "v1.2 · Design LVD press-brake backbar jigs from one STEP file. Use a supplied flat pattern or estimate unfolding from the formed part; check direct gauging first, then deliver only required backbar DXFs and a formed STEP with programming gauge tabs, plus a commentable HTML preview. Trimming is only applied when explicitly requested in a user message or preview comment."
---

# Design Backbar

## Contract

Accept **one STEP file**. Prefer its supplied flat pattern when present. Otherwise estimate the flat from the formed solid; do not demand another flat-pattern export before trying the supported unfolding route.

Deliver:
- **DXF:** one per required backbar plate, mm at 1:1, for 6 mm material.
- **STEP:** formed part with required gauge tabs merged into one valid solid, for CADMAN-B.
- **HTML review:** dimensioned backbars and tabs, folded part with highlighted tabs, direct-gauge bends, and pinned comments.

Keep estimated flat patterns, intermediate geometry, logs and JSON internal unless requested. Do not deliver a ZIP unless the user asks for one. When packaging, include only the current run's required plates; exclude superseded plates and internal files.

The physical blank has **no programming tabs**. Its outline defines the jig pocket. The STEP tabs provide straight gauge edges for bending software. They do not enlarge the programmed gauge distance beyond the blank tip.

## Trimming: user instruction only

**Never suggest, consider as a default design step, or apply edge trimming automatically.** A nearly parallel edge is not permission to change the part. Report its measured angular mismatch if relevant, then design to the existing contour.

Use trimming only when explicitly requested in the user's message or a pasted preview comment. Apply the requested trim to the real blank, affected backbar pockets and formed STEP together. Record maximum material removal. Never reuse a previous part's trimming request on a new part.

`--trim-for N` implements the narrow request “trim the gauged free edge parallel to bend N.” It removes material back to the nearer end of a straight end edge (up to 2 mm automatically, never adds material). A larger or differently located user-requested trim needs explicit geometry implementation and checks; do not force this option to approximate unrelated changes.

## Workflow

1. Run the bundled script on the STEP. Inspect every bend's direct-gauge classification before discussing plates.
2. If a genuine parallel contact edge at least 10 mm long exists at the chosen end, use direct gauging: no plate, no tab and no +50 mm offset. Do not silently treat a nearly parallel edge as parallel.
3. For other bends, generate the contour pocket and the programming tab together. Reuse identical plates when their shape and position agree.
4. If the user requests a trim or provides pinned comments, rerun with the appropriate option. Trimming must not be inferred from a near-parallel result.
5. Check the report, STEP validation and preview. Render the preview or extract its SVGs for visual inspection. Highlight tabs clearly; never call an unvalidated result production-ready.
6. Save and deliver the DXFs, formed STEP and HTML preview. State estimated unfolding assumptions and any bend-order or tooling constraints.

## Run

Use the scripts in this skill directory directly; do not copy a large code block from SKILL.md.

```bash
uv run --no-project --python 3.12 \
  --with 'cadquery-ocp>=7.8,<7.9' --with 'ezdxf>=1.3,<2' --with 'numpy>=1.26,<3' \
  python '<skill directory>/scripts/backbar.py' PART.step OUT
```

If these dependencies are already available, run plain Python. Without `uv`, install them into a task-local virtual environment. OCP 8 is unsupported. If dependencies cannot be installed, report the specific blocker.

Use a fresh output directory for each revision so old plates cannot leak into delivery. The console JSON and `OUT/report.json` are internal records; manufacturing files and the review preview are the only default deliverables.

### Options

| Option | Use |
|---|---|
| `--side N=+` / `--side N=-` | Use the other gauging end for bend N. Read its current sign first. |
| `--at N=X` | Place a tab's outer side X mm along the bend from the tip; signed coordinate. |
| `--tab-width MM` | Default 5 mm; only change when requested. |
| `--wrap MM` | 10–20 mm; default 20. |
| `--die-clear MM` | Assumed minimum bend-line-to-plate-front clearance; default 8. |
| `--flat N` | Select supplied flat body N if ambiguous. |
| `--trim-for N` | **Explicit user-requested trim only**, to make the gauged free edge parallel to bend N. |

Do not infer an option value from a screenshot dimension when exact geometry or comment coordinates are available.

## Shop standard

| Item | Value |
|---|---|
| Plate width × thickness | 100 × 6 mm |
| Finger slot | 50.2 mm wide × 20 mm deep, centred at rear |
| Blank tip to finger tip | 50 mm |
| Blank tip to plate rear | 70 mm |
| Wrap toward bend | 20 mm nominal; minimum 10 mm |
| Pocket clearance | 0.1 mm |
| Material each side of pocket | Minimum 10 mm |
| Tab width | 5 mm |
| Automatic maximum tab height | 10 mm |
| Tab end | Through blank tip, parallel to bend |

Keep these fixed unless the user changes the shop standard. A part that does not fit the fixed-width plate must be reported; never resize silently.

## Input handling and supported unfolding

For a supplied flat, use its separate bend-strip faces. If they have been merged, ask for an unmerged export or a formed-only file; do not guess bend locations from an undifferentiated flat.

For formed-only input, `scripts/unfold.py`:
- Infers thickness from paired planar faces.
- Finds connected planar flanges and paired curved bend strips, including supported imported spline surfaces.
- Unfolds flange geometry by rigid transformations, preserving flange holes and contours.
- Estimates neutral bend widths from paired surface areas and tangent lengths with **K=0.50**; this is an estimate, not a material-specific calibrated allowance.
- Retains flange transforms so tabs and explicitly requested trims map back to the original folded geometry.
- Rejects curved tangent lines, incomplete/ambiguous topology, cyclic connections, overlaps and invalid blanks instead of fabricating a result.

One formed solid without an unambiguous match is required. Extra solids can be matched against a supplied flat; an ambiguous assembly needs the intended part identified. Do not claim support for arbitrary stampings, variable-thickness solids, hems or nondevelopable surfaces.

For a supplied flat, tab mapping must identify one unique formed flange. A symmetric or unsupported mapping must fail clearly rather than attach a tab to an arbitrary flange.

## Gauging and sequence

Prefer a free gauging end with no intervening bend; when both are free choose the nearer end. If neither end is free, use the nearer end only with an explicit report of which intervening bends must remain flat. This is a conditional gauge setup, not a complete collision-checked bending sequence. Honor user-selected ends through `--side`.

Design every tab against the real blank contour. Check each tab's own gauge edge independently. If a programming tab for another bend projects beyond that gauge line, report the conflict and tell the user to select the intended edge in CADMAN-B; do not shift the gauge distance to the other tab.

Preserve bend-order warnings on direct-gauge bends too. A parallel edge may still sit beyond another bend.

Report per jig-assisted bend:
- Programmed bend-to-tab-edge distance.
- Actual bend-to-finger-tip distance, **program distance +50 mm**.
- Plate front to bend line; ask the user to check against the die in use.
- Wrap and measured pocket clearance.
- Tab width, near/far heights and zero offset from its intended gauge line.
- Shared plate identity, warnings, or any failed operation.

For direct-gauge bends, report contact length and gauge distance with **no jig offset**. Never label a direct-gauge bend as requiring a backbar.

## Validation

- Require one valid, non-overlapping flat outline.
- Measure 0.1 mm clearance against the actual working contour (estimated if unfolded).
- Reject split or invalid plates; do not silently export only the largest piece.
- Require each tab to join one unambiguous flange and its edge to agree with the gauge line within 0.001 mm.
- Require final formed STEP to contain one valid solid, with tab-added volume agreeing with tab area × thickness within max(0.1 mm³, 0.1% of tab volume).
- Read the exported STEP back; require one valid solid and volume difference within **max(0.5 mm³, 0.001% of part volume)**. Report the actual difference and limit. This accounts for STEP surface-integration precision; never loosen the threshold to rescue a failed run.
- Audit DXFs and inspect the rendered preview, including dimension labels and visible tab placement.

If a check fails, fix the cause or report the precise limitation. Do not present stale outputs from an earlier run as successful current deliverables.

## Review comments

The user enables **Comment mode**, clicks a drawing, types notes, then uses **Copy all** to paste comments into chat. Coordinates refer to the named drawing.

- Change gauging end: rerun `--side N=` with the opposite sign.
- Move tab: use the signed pin coordinate along the bend plus half tab width farther from the tip as `--at N=X`.
- Request a parallel-edge trim: only then use `--trim-for N` and report removal.
- Other explicit geometry changes: implement in the reusable geometry workflow, validate and regenerate all affected outputs. Never patch only the displayed picture or a DXF independently of its STEP and contour source.

## Limits to state when relevant

The script does not simulate punch/die collisions, backgauge reach or finger height, complete bending sequence, operator handling, or CADMAN-B's automatic choice of gauge edge. The 8 mm die clearance is an assumption. Verify estimated jig fit on a real blank.

## Maintenance

Keep instructions concise and geometry in `scripts/`. Test ordinary parallel-edge parts, angled-edge parts, supplied flats, formed-only inputs, explicit trim comments and refusal cases. Never hard-code sample face numbers or part-specific bend counts. Preserve the no-trim default in both code and instructions.
