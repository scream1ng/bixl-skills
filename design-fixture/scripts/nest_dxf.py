#!/usr/bin/env python3
"""Search configured single-sheet sizes with heuristic rectangle packing; write the cutting DXF and re-read it.

Rectangle packing (largest profile first, 0/90 deg, best short-side fit into maximal free rectangles).
DXF layers: CUT (closed contours), ETCH (plate names), STOCK_REFERENCE (sheet outline); units mm.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import ezdxf
from shapely import affinity
from shapely.geometry import Polygon, box

from fixture_common import load_spec, poly, write_json

DEFAULTS = {"gap_mm": 8.0, "margin_mm": 15.0, "sheet_width_mm": [500, 1000, 50], "sheet_height_mm": [450, 650, 50]}


def fits(a, b):
    return a[0] >= b[0] - 1e-7 and a[1] >= b[1] - 1e-7 and a[2] <= b[2] + 1e-7 and a[3] <= b[3] + 1e-7


def pack(plates, W, H, gap, margin):
    free = [(margin, margin, W - margin + gap, H - margin + gap)]
    out = []
    for d in sorted(plates, key=lambda d: -Polygon(d["outer"]).area):
        p = poly(d)
        candidates = []
        for angle in (0, 90):
            q = affinity.rotate(p, angle, origin=(0, 0))
            b = q.bounds
            w, h = b[2] - b[0] + gap, b[3] - b[1] + gap
            for f in free:
                dw, dh = f[2] - f[0] - w, f[3] - f[1] - h
                if min(dw, dh) >= -1e-6:
                    candidates.append(((min(dw, dh), max(dw, dh), f[1], f[0]), q, b, w, h, angle, f))
        if not candidates:
            return None
        _, q, b, w, h, angle, f = min(candidates, key=lambda c: c[0])
        x, y = f[:2]
        used = (x, y, x + w, y + h)
        out.append((d, affinity.translate(q, xoff=x - b[0], yoff=y - b[1]), angle, [x - b[0], y - b[1]]))
        new = []
        for a in free:
            if a[2] <= used[0] or a[0] >= used[2] or a[3] <= used[1] or a[1] >= used[3]:
                new.append(a)
                continue
            if a[0] < used[0]:
                new.append((a[0], a[1], used[0], a[3]))
            if a[2] > used[2]:
                new.append((used[2], a[1], a[2], a[3]))
            if a[1] < used[1]:
                new.append((a[0], a[1], a[2], used[1]))
            if a[3] > used[3]:
                new.append((a[0], used[3], a[2], a[3]))
        free = [a for i, a in enumerate(new) if a[2] - a[0] > .01 and a[3] - a[1] > .01
                and not any(i != j and fits(a, b) and (a != b or j < i) for j, b in enumerate(new))]
    return out


def nest(spec, dxf_path):
    P = {**DEFAULTS, **spec.get("nest", {})}
    gap, margin, plates = P["gap_mm"], P["margin_mm"], spec["plates"]
    w0, w1, ws = P["sheet_width_mm"]
    h0, h1, hs = P["sheet_height_mm"]
    nested = None
    for _, W, H in sorted((w * h, w, h) for w in range(w0, w1 + 1, ws) for h in range(h0, h1 + 1, hs)):
        nested = pack(plates, W, H, gap, margin)
        if nested:
            break
    if not nested:
        raise ValueError("No single-sheet solution found in the configured sizes. Use a documented multi-sheet nesting workflow; do not omit plates or enlarge stock silently.")

    doc = ezdxf.new("R2010")
    doc.units = 4
    for layer, color in (("CUT", 7), ("ETCH", 3), ("STOCK_REFERENCE", 8)):
        doc.layers.new(layer, dxfattribs={"color": color})
    ms = doc.modelspace()
    ms.add_lwpolyline([(0, 0), (W, 0), (W, H), (0, H)], close=True, dxfattribs={"layer": "STOCK_REFERENCE"})
    expected = []
    for d, p, angle, offset in nested:
        d["nest_rotation_degrees"], d["nest_offset"] = angle, offset
        for ring in [p.exterior] + list(p.interiors):
            coords = list(ring.coords)[:-1]
            ms.add_lwpolyline(coords, close=True, dxfattribs={"layer": "CUT"})
            expected.append(Polygon(coords))
        rp = p.representative_point()
        ms.add_text(d["name"], dxfattribs={"layer": "ETCH", "height": 3.5, "insert": (rp.x, rp.y)})
    doc.saveas(dxf_path)

    back = ezdxf.readfile(dxf_path)
    cuts = list(back.modelspace().query('LWPOLYLINE[layer=="CUT"]'))
    etch = list(back.modelspace().query('TEXT[layer=="ETCH"]'))
    assert len(cuts) == len(expected) and all(e.closed for e in cuts)
    err = max(Polygon([(v[0], v[1]) for v in e.get_points()]).symmetric_difference(p).area for e, p in zip(cuts, expected))
    assert err < 1e-5 and back.units == 4
    inside = all(box(margin, margin, W - margin, H - margin).buffer(1e-4).covers(p) for _, p, _, _ in nested)
    min_gap = min(a.distance(b) for i, (_, a, _, _) in enumerate(nested) for _, b, _, _ in nested[i + 1:])
    return {"plate_count": len(plates), "sheet_mm": [W, H], "thickness_mm": spec["thickness_mm"],
            "area_utilization_percent": round(100 * sum(poly(d).area for d in plates) / (W * H), 1),
            "min_gap_mm": min_gap, "gap_limit_mm": gap, "margin_mm": margin, "inside_margin": inside,
            "closed_cut_contours": len(cuts), "etch_labels": len(etch), "dxf_units": "mm",
            "dxf_roundtrip_max_area_error_mm2": err,
            "status": "pass" if inside and min_gap >= gap - 1e-3 else "fail"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", help="spec whose plates are final (e.g. output of build.py)")
    ap.add_argument("dxf")
    ap.add_argument("report")
    a = ap.parse_args()
    report = nest(load_spec(a.spec), Path(a.dxf))
    write_json(a.report, report)
    print(report)


if __name__ == "__main__":
    main()
