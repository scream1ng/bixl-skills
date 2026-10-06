# Evaluate modeling reliability

Use when the user requests skill testing or improvement.

## Small representative evaluation set

Choose available, permitted examples that exercise different decisions:

| Case | Inputs | Observable success |
|---|---|---|
| Dimensioned mechanical part | Drawing or STEP with known feature dimensions | Valid solids; correct dimensions and feature locations; preserved interfaces; export reopens correctly |
| Curved enclosure | Several views, a scale dimension, and mounting/keep-out constraints | Consistent silhouette across views; smooth intended transitions; required internal space and mounting geometry retained |
| Detailed visual model | A reference image and explicit output requirements | Inspected framing, silhouette, proportions, important detail and final render; inferred geometry identified |

Start with one relevant case if that resolves the current uncertainty. Run all three only when broader reliability evaluation is requested and the needed artifacts and tools are available. Do not invent missing ground-truth dimensions. Identify what cannot yet be evaluated.

## Run and retain evidence

1. Record inputs, intended outputs, acceptance criteria, tool versions and the skill version or copy used. Keep benchmark artifacts in an isolated job folder.
2. Execute the task using the skill. Retain the editable model, first useful draft, final result, and actual verification results. Test the independent question-round behavior only when the case genuinely requires clarification.
3. Assess silhouette, proportions, feature placement, surface quality and dimensions separately using the review protocol. Include failures and unverifiable criteria; avoid a blended score that hides them.
4. Record the specific failed behavior and its evidence. Determine whether it comes from missing input, tool capability, an implementation error or an instruction gap before changing the skill.
5. When skill changes are authorized, make the smallest generalizable correction. Repeat the failing case and test a different example to check transfer. Do not optimize only for the original picture.

## Comparing hosts (ChatGPT vs Claude)

Run the same case on each host with the same skill version, inputs and scripted user answers (write the answers before the first run; reuse them verbatim; when a host asks something the script does not cover, answer "use your recommendation" and log it). Record per run:

- Host, model and the capabilities table from `design-spec.md` (which path was used: generated concepts or rendered variants, inline HTML or file).
- The final `board.html` and `board.json`: the run's visual record of questions, pictures, stops and decisions.
- Interview: rounds asked, checklist items covered, items left as unconfirmed assumptions.
- Stages: user stops (expected: three), board revisions before approval, any stage-3 pauses and why; elements in `elements.json`; any `preview.py` or `board.py` blocks and how they were resolved.
- Results: the same silhouette, proportion, feature, surface and dimension criteria as above, from the final `sheet.png` and CAD measurements.

Compare hosts on these records, not on prose quality. Note where a difference comes from a missing host capability rather than modeling skill.

Keep comparison settings consistent when assessing an improvement. More render samples, different lighting, or a new camera can conceal a geometry regression; include neutral views and CAD measurements where relevant.

Report which evidence actually occurred: table-top scenario review, structural validator, or executed modeling benchmark. Never claim independent evaluation if the same agent performed it.

## Report

Link the actual artifacts and summarize the criteria that passed, failed or remain unverified. Explain any supported skill change and its retest outcome.
