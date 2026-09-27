#!/usr/bin/env python3
"""Tab-and-slot joints between clamp/carrier cap plates and the cheeks under them.

laser-cut-construction.md requires every supported cap to be located by at least two separated
tabs; base-tab automation does not create them. This module is that automation: each cap plate
named by a clamp, every pin pad named by pin_locators[].pad (plus spec.cap_joints.extra_caps) gets
two tabs from the cheeks it sits on.

Run before tabs_slots.design: cap tabs change cheek profile above tab_slot.foot_height_mm, and
the foot search asserts that region is unchanged. Run before clamp_mount.mount: the clamp tap
pilots do not exist in the plate yet, so the pilot and base-footprint clearances are computed
here from the hardware record.

Overrides in spec.cap_joints: pinned {cap: [[cheek, s_a, s_b], ...]}, skip [cap], extra_caps [cap].
"""
from __future__ import annotations

import argparse
import itertools

import numpy as np
from shapely.geometry import LineString, Polygon, box

import clamp_mount
from fixture_common import clean, load_spec, poly, set_profile, write_json

class Infeasible(Exception):
    """No tab layout satisfies the min-width rule for this cap; reported, not raised out of design()."""


FACE_TOL_MM = 1e-5  # cheek top on cap face; absorbs 6-decimal rounding of plate frames
DEFAULTS = {"tab_length_mm": 12.0, "slot_clearance_mm": 0.2, "search_step_mm": 1.0,
            "pinned": {}, "skip": [], "extra_caps": []}


def params(spec):
    return {**DEFAULTS, **spec.get("cap_joints", {})}


def axes(d):
    return (np.array(d[k], float) for k in ("origin", "u", "v", "w"))


def cap_local(cap, p):
    o, U, V, _ = axes(cap)
    return float((p - o) @ U), float((p - o) @ V)


def cap_faces(cap, d, T):
    """Cheek-local v of the cap's (near, far) faces, and the cheek's top edge."""
    o, _, V, W = axes(cap)
    do, _, dv, _ = axes(d)
    tops = sorted(float((o + W * s * T / 2 - do) @ dv) for s in (-1, 1))
    return tops[0], tops[1], max(y for _, y in d["outer"])


def cheek_top(cap, d, T):
    """Cheek-local v of the near cap face the cheek stops on, or None if it does not stop there."""
    near, _, high = cap_faces(cap, d, T)
    return near if abs(near - high) < FACE_TOL_MM else None


def through_cap(cap, plates, T):
    """Cheeks whose top edge sits on the cap's far face under the cap: their body runs through it.

    Call before any cap tabs are cut: a tab legitimately reaches the far face."""
    _, _, _, W = axes(cap)
    outer = Polygon(cap["outer"])
    out = []
    for d in plates:
        if d["name"] == cap["name"]:
            continue
        do, du, dv, dw = axes(d)
        if abs(dw @ W) > 1e-6 or abs(abs(dv @ W) - 1) > 1e-6:
            continue
        _, far, high = cap_faces(cap, d, T)
        if abs(far - high) >= FACE_TOL_MM:
            continue
        top = poly(d).intersection(box(-1e4, far - FACE_TOL_MM, 1e4, far + FACE_TOL_MM))
        if top.is_empty:
            continue
        lo, _, hi, _ = top.bounds
        edge = LineString([cap_local(cap, do + du * u + dv * far) for u in (lo, hi)])
        if edge.intersection(outer).length > FACE_TOL_MM:
            out.append(d["name"])
    return out


def cheeks_of(cap, plates, T):
    """Plates standing under the cap: plane parallel to the cap normal, top edge on the cap face."""
    _, _, _, W = axes(cap)
    out = []
    for d in plates:
        if d["name"] == cap["name"]:
            continue
        _, _, dv, dw = axes(d)
        if abs(dw @ W) > 1e-6 or abs(abs(dv @ W) - 1) > 1e-6:
            continue
        top = cheek_top(cap, d, T)
        if top is not None:
            out.append((d, top))
    return out


def slot_poly(cap, d, top, a, b, T, clr):
    do, du, dv, _ = axes(d)
    ends = [cap_local(cap, do + du * s + dv * top) for s in (a, b)]
    return LineString(ends).buffer((T + clr) / 2, cap_style=2, join_style=2)


def obstacles(spec, cap, min_width):
    """(cutouts, keepouts): cutouts keep the min-width rule, keepouts only have to stay clear.

    A clamp's tap pilots are cutouts; its base footprint is not a hole in the plate, so like
    clamp_mount it only requires the slot not to break the seated area.
    """
    import clamp_mount
    cuts, keep = [Polygon(h) for h in cap["holes"]], []
    for clamp in spec.get("clamps", []):
        if clamp["mount_plate"] != cap["name"]:
            continue
        _, holes, footprint = clamp_mount.place(clamp, cap, spec["thickness_mm"], min_width)
        cuts += holes
        keep.append(footprint)
    return cuts, keep


def spans(cap, d, top, L, T, P, min_width, obs, keep, placed):
    """Feasible [a, a+L] tab spans on cheek d, best clearance first."""
    p = poly(d)
    outer = Polygon(cap["outer"])
    lo, _, hi, _ = p.bounds
    out = []
    a = lo
    while a + L <= hi + 1e-9:
        b = a + L
        if p.buffer(FACE_TOL_MM).covers(box(a, top - min(3.0, L), b, top)) and p.intersection(box(a, top + FACE_TOL_MM, b, 1e4)).area < 1e-9:
            q = slot_poly(cap, d, top, a, b, T, P["slot_clearance_mm"])
            if outer.covers(q):
                gaps = [outer.exterior.distance(q)] + [q.distance(o) for o in obs + placed]
                if min(gaps) >= min_width - 1e-6 and all(q.disjoint(k) for k in keep):
                    out.append((min(gaps), a, b))
        a += P["search_step_mm"]
    mid = sum(r[1] for r in out) / len(out) if out else 0.0
    out.sort(key=lambda r: (-r[0], abs(r[1] - mid)))
    return out


def apply(cap, d, top, a, b, T, clr, joints):
    grown = poly(d).union(box(a, top, b, top + T))
    assert grown.geom_type == "Polygon", f"{d['name']}: cap tab splits the profile"
    set_profile(d, clean(grown))
    q = slot_poly(cap, d, top, a, b, T, clr)
    cap["holes"] = cap["holes"] + [[list(map(float, c)) for c in list(q.exterior.coords)[:-1]]]
    joints.append({"a": d["name"], "b": cap["name"], "tab_mm": [round(a, 3), round(b, 3)],
                   "engagement_mm": T, "slot_width_mm": T + clr, "a_slot": "tab", "b_slot": "through"})


def select(cap, avail, obs, keep, P, T, min_width, family_span):
    """Choose (cheek, top, a, b) for two tabs, or raise Infeasible."""
    placed, chosen = [], []
    if cap["name"] in P["pinned"]:
        for name, a, b in P["pinned"][cap["name"]]:
            d, top = next((x for x in avail if x[0]["name"] == name), (None, None))
            if d is None:
                raise Infeasible(f"pinned cheek {name} does not reach the cap")
            ok = spans(cap, d, top, b - a, T, P, min_width, obs, keep, placed)
            if not any(abs(r[1] - a) < 1e-6 for r in ok):
                near = min(ok, key=lambda r: abs(r[1] - a)) if ok else None
                hint = (f"nearest feasible {name} tab is {near[1]:g}..{near[2]:g}" if near else
                         f"no {b - a:g} mm span on {name} is feasible: extend the cheek or the cap")
                raise Infeasible(f"pinned tab {name} {a}..{b} breaks the {min_width} mm rule; {hint}")
            chosen.append((d, top, a, b))
            placed.append(slot_poly(cap, d, top, a, b, T, P["slot_clearance_mm"]))
        return chosen, placed, "pinned"
    feasible = [(d, top, spans(cap, d, top, P["tab_length_mm"], T, P, min_width, obs, keep, [])) for d, top in avail]
    feasible = [f for f in feasible if f[2]]
    if len(feasible) < 2:
        raise Infeasible(f"{len(feasible)} of {len(avail)} cheeks reaching the cap can take a {P['tab_length_mm']} mm tab "
                         f"{min_width} mm clear of the cap edges, tap pilots and clamp base. "
                         f"Move a cheek or the clamp, or pin the tabs in spec.cap_joints.pinned")
    for d, top, opts in max(itertools.combinations(feasible, 2), key=lambda c: separation(cap, c)):
        # Cheeks sharing a part number are cut from one profile, so they share the tab span.
        fam = family_span.get(d["part_number"])
        if fam:
            opts = [o for o in opts if abs(o[1] - fam[0]) < 1e-6 and abs(o[2] - fam[1]) < 1e-6]
            if not opts:
                raise Infeasible(f"{d['name']} cannot take the {fam[0]}..{fam[1]} tab already cut into part "
                                 f"{d['part_number']}. Give it its own part number, or pin both tabs")
        ok = [o for o in opts if all(slot_poly(cap, d, top, o[1], o[2], T, P["slot_clearance_mm"]).distance(q) >= min_width - 1e-6 for q in placed)]
        if not ok:
            raise Infeasible(f"no tab on {d['name']} keeps {min_width} mm from the other slot")
        _, a, b = ok[0]
        family_span[d["part_number"]] = (a, b)
        chosen.append((d, top, a, b))
        placed.append(slot_poly(cap, d, top, a, b, T, P["slot_clearance_mm"]))
    return chosen, placed, "search"


def design(spec, log=print):
    """Mutates spec['plates'] and spec['joints'] in place; returns the cap-joint report.

    A cap with no valid layout is reported as fail and left unjoined: the preview still renders
    so the designer can see it, and verify's cap_joints check fails on the same cap.
    """
    P, T = params(spec), spec["thickness_mm"]
    plates = spec["plates"]
    by = {d["name"]: d for d in plates}
    names = [c["mount_plate"] for c in spec.get("clamps", [])] + sorted(clamp_mount.pin_pads(spec)) + list(P["extra_caps"])
    joints = spec.setdefault("joints", [])
    rows, family_span = [], {}
    through_of = {n: through_cap(by[n], plates, T) for n in dict.fromkeys(names) if n not in P["skip"]}
    for name in dict.fromkeys(names):
        if name in P["skip"]:
            rows.append({"cap": name, "mode": "skipped", "cheeks": [], "tabs_mm": [], "status": "unknown",
                         "reason": "listed in cap_joints.skip"})
            log(f"  {name}: skipped by spec.cap_joints.skip")
            continue
        cap = by[name]
        from clamp_mount import min_width_for
        min_width = min_width_for(spec, name)
        avail = cheeks_of(cap, plates, T)
        through = through_of[name]
        if through:
            reason = (f"{', '.join(through)} run(s) through {name} to its far face: stop the cheek top edge on the "
                      f"cap face nearer the cheek (one plate thickness lower)")
            rows.append({"cap": name, "mode": "none", "cheeks": [], "tabs_mm": [], "cheeks_available": len(avail),
                         "status": "fail", "reason": reason})
            log(f"  {name}: NO CAP JOINT - {reason}")
            continue
        obs, keep = obstacles(spec, cap, min_width)
        try:
            chosen, placed, mode = select(cap, avail, obs, keep, P, T, min_width, family_span)
        except Infeasible as exc:
            rows.append({"cap": name, "mode": "none", "cheeks": [], "tabs_mm": [], "cheeks_available": len(avail),
                         "status": "fail", "reason": str(exc)})
            log(f"  {name}: NO CAP JOINT - {exc}")
            continue
        for d, top, a, b in chosen:
            apply(cap, d, top, a, b, T, P["slot_clearance_mm"], joints)
        gaps = [Polygon(cap["outer"]).exterior.distance(q) for q in placed]
        gaps += [q.distance(o) for q in placed for o in obs] + [x.distance(y) for x, y in itertools.combinations(placed, 2)]
        used = [d["name"] for d, _, _, _ in chosen]
        rows.append({"cap": name, "mode": mode, "cheeks": used, "tabs_mm": [[a, b] for _, _, a, b in chosen],
                     "cheeks_available": len(avail), "minimum_clearance_mm": float(min(gaps)), "status": "pass", "reason": ""})
        log(f"  {name}: tabs on {', '.join(used)} ({mode}, {min(gaps):.1f} mm clear)")
    families = {}
    for d in plates:
        families.setdefault(d["part_number"], []).append(d)
    for pn, fam in families.items():
        odd = [f["name"] for f in fam if f["outer"] != fam[0]["outer"] or f["holes"] != fam[0]["holes"]]
        assert not odd, (f"cap tabs made {pn} profiles differ ({fam[0]['name']} vs {', '.join(odd)}). "
                         f"Tab the same cheeks on every {pn}, or give the tabbed one its own part number.")
    status = ("unknown" if not rows else "fail" if any(r["status"] == "fail" for r in rows)
              else "pass" if all(r["status"] == "pass" for r in rows) else "unknown")
    return {"status": status, "caps": rows, "cap_count": len(rows),
            "params": {k: v for k, v in P.items() if k not in ("pinned", "skip", "extra_caps")}}


def audit(spec, tol=0.01):
    """Backstop for the evaluated spec: two separated tabs per cap, none standing proud of it."""
    P, T = params(spec), spec["thickness_mm"]
    by = {d["name"]: d for d in spec["plates"]}
    names = [c["mount_plate"] for c in spec.get("clamps", [])] + sorted(clamp_mount.pin_pads(spec)) + list(P["extra_caps"])
    rows = []
    for name in dict.fromkeys(names):
        if name in P["skip"]:
            rows.append({"cap": name, "status": "unknown", "reason": "listed in cap_joints.skip"})
            continue
        if name not in by:
            rows.append({"cap": name, "status": "fail", "reason": "no plate of this name to take the cap tabs"})
            continue
        cap = by[name]
        tabs = [j for j in spec.get("joints", []) if j.get("b") == name and j.get("a_slot") == "tab"]
        proud = []
        o, _, _, W = axes(cap)
        for j in tabs:
            d = by[j["a"]]
            do, _, dv, _ = axes(d)
            # The tab grows +v through the cap, so a flush end sits on the cap's far face.
            far = max(float((o + W * s * T / 2 - do) @ dv) for s in (-1, 1))
            a, b = j["tab_mm"]
            proud.append(poly(d).intersection(box(a, -1e4, b, 1e4)).bounds[3] - far)
        cheeks = {j["a"] for j in tabs}
        bad = [j["a"] for j, x in zip(tabs, proud) if x is None or x > tol]
        rows.append({"cap": name, "tab_count": len(tabs), "cheeks": sorted(cheeks),
                     "max_proud_mm": max([x for x in proud if x is not None], default=None),
                     "status": "fail" if len(cheeks) < 2 or bad else "pass",
                     "reason": (f"tabs from {len(cheeks)} cheek(s), two separated tabs required" if len(cheeks) < 2 else
                                f"tab ends stand proud of the mounting face on {', '.join(bad)}" if bad else "")})
    status = ("unknown" if not rows else "fail" if any(r["status"] == "fail" for r in rows)
              else "pass" if all(r["status"] == "pass" for r in rows) else "unknown")
    return {"status": status, "caps": rows,
            "scope": "cap tab count, separation and flush tab ends; weld preparation and strength are separate"}


def separation(cap, combo):
    (d1, t1, o1), (d2, t2, o2) = combo
    q1 = LineString([cap_local(cap, np.array(d1["origin"], float) + np.array(d1["u"], float) * s + np.array(d1["v"], float) * t1) for s in (o1[0][1], o1[0][2])])
    q2 = LineString([cap_local(cap, np.array(d2["origin"], float) + np.array(d2["u"], float) * s + np.array(d2["v"], float) * t2) for s in (o2[0][1], o2[0][2])])
    return q1.distance(q2)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec")
    ap.add_argument("out")
    a = ap.parse_args()
    spec = load_spec(a.spec)
    report = design(spec)
    write_json(a.out, report)
    print({k: v for k, v in report.items() if k != "caps"})


if __name__ == "__main__":
    main()
