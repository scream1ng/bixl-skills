# Evaluate modeling reliability

Use when the user requests skill testing or improvement. This procedure is not a claim that the skill has already demonstrated a given modeling quality.

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

Keep comparison settings consistent when assessing an improvement. More render samples, different lighting, or a new camera can conceal a geometry regression; include neutral views and CAD measurements where relevant.

Independent evaluation is useful when available and authorized, but is not mandatory. Never claim independent evaluation if the same agent performed it. A table-top scenario review, a structural validator, and an executed modeling benchmark are different levels of evidence; report which actually occurred.

## Report

Link the actual artifacts and summarize the criteria that passed, failed or remain unverified. Explain any supported skill change and its retest outcome. A successful example demonstrates that case, not universal mastery of image-to-CAD reconstruction.
