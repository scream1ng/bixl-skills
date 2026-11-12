# design-backbar changes

## v1.7 (2026-10-22)

Found on WAG-113342 (Rhino-converted STEP, 7 bends).

**Imported STEP robustness**
- Unfold: flattened pieces rebuilt on the exact XY plane; merged blank rebuilt from exact lines/arcs with collinear joins (≤0.002 mm deviation check). Fixes false "overlap or gap", invalid-blank and pocket-offset failures on spline-trimmed imports.
- Overlap check uses boundary-polygon areas; tab volume check uses Boolean add/remove volumes.
- Plate pocket faces built on the XY plane (no plane fitting through spline edges).
- Physical-change regions under 0.001 mm (Boolean slivers) are ignored.

**New options**
- `--gauge-edge N=Y`: gauge on a user-picked parallel edge nearer than the half-plane tip.
- `--formed-ok N=A+B`: explicit, reported waiver of a flat-region dependency for bends clear of the gauging path.
- Dependency-conflict error now lists each bend's requirement.

**Review page**
- Banner: Physical blank UNCHANGED / N CHANGE(S); change details moved below the sequence.
- Method names: TRIM EDGE / TRIM EDGE TRIAL when the contact edge was trimmed (also in report and README).
- Picture-first step views: bend badges with angle and state, gauge-distance arrow, green/red contact edge, keep-fingers-clear hatch, TRIAL tag, shared PLATE label; step labels for existing vs trimmed edges and unused near-parallel edges.
- Comment mode: hover highlights edges; pins record edge ID, status, length, angle and distance (or plate/tab); quick-intent buttons; Copy all copies plain text via a textarea buffer (design-fixture pattern).

**Tests**: 39 pass (test_revision15 updated for the new section order; new test_revision17.py).
