#!/usr/bin/env python3
"""True-shape sheet nest for flat blanks from step_geometry.py --outline.

Usage: python nest.py NAME=FLAT.json [NAME2=FLAT2.json ...] [--sheet 1200 2400]
       [--margin 10] [--gap 5] [--clamp 100] [--svg PREFIX]
       [--html PAGE.html --title "Job name" --sheet-price 106] > NEST.json
Requires numpy, scipy, shapely, matplotlib.

Greedy bottom-left fill on a 1 mm raster. Rotation is 0 or 180 degrees only
(no mirroring). Each part keeps one fixed alignment; four alignments are tried
(as unfolded, +90, and both sides of its minimum-area rectangle) and the one
fitting the most parts is kept. No part may enter the clamp zone along one
long edge. Every result is re-checked with exact geometry.
"""
import argparse, json, sys
from collections import Counter
from itertools import count

import numpy as np
from matplotlib.path import Path
from scipy.signal import fftconvolve
from shapely import affinity
from shapely.geometry import Polygon, box

RES = 1.0


def load(fn):
    d = json.load(open(fn))
    return Polygon(d["exterior"], d["interiors"])


def bases(p):
    c = list(p.minimum_rotated_rectangle.exterior.coords)
    th = np.degrees(np.arctan2(c[1][1] - c[0][1], c[1][0] - c[0][0]))
    return sorted({round(a % 180, 3) for a in (0, 90, -th, -th + 90)})


def mask(poly, gap):
    b = poly.buffer(gap / 2 + RES * 0.75, join_style=2)
    x0, y0, x1, y1 = b.bounds
    nx, ny = int(np.ceil((x1 - x0) / RES)) + 1, int(np.ceil((y1 - y0) / RES)) + 1
    X, Y = np.meshgrid(x0 + np.arange(nx) * RES, y0 + np.arange(ny) * RES)
    inside = Path(np.array(b.exterior.coords)).contains_points(np.c_[X.ravel(), Y.ravel()])
    return inside.reshape(ny, nx).astype(float), (x0, y0)


def nest(parts, base, seq, a):
    """parts: name -> Polygon; base: name -> angle; seq: names placed in turn until none fit."""
    sw, sl = a.sheet
    W, L = int((sw - 2 * a.margin + a.gap) / RES), int((sl - 2 * a.margin + a.gap) / RES)
    occ = np.zeros((W, L))
    if a.clamp > a.margin:
        occ[:int((a.clamp - a.margin + 1) / RES), :] = 1
    pre = {}
    for k in set(seq):
        solid = Polygon(parts[k].exterior)
        pre[k] = [(ang,) + mask(affinity.rotate(solid, ang, origin=(0, 0)), a.gap)
                  for ang in (base[k], base[k] + 180)]
    placed, fails, i = [], set(), 0
    while len(fails) < len(set(seq)):
        k = seq[i % len(seq)]
        i += 1
        if k in fails:
            continue
        best = None
        for ang, mk, (ox, oy) in pre[k]:
            if mk.shape[0] > W or mk.shape[1] > L:
                continue
            ok = np.argwhere(fftconvolve(occ, mk[::-1, ::-1], mode="valid") < 0.5)
            if len(ok) == 0:
                continue
            score = ok[:, 1] * 10000 + ok[:, 0]
            j = np.argmin(score)
            if best is None or score[j] < best[0]:
                best = (score[j], ok[j][0], ok[j][1], ang, mk, ox, oy)
        if best is None:
            fails.add(k)
            continue
        _, r, c, ang, mk, ox, oy = best
        occ[r:r + mk.shape[0], c:c + mk.shape[1]] += mk
        dx, dy = a.margin - a.gap / 2 + c * RES - ox, a.margin - a.gap / 2 + r * RES - oy
        placed.append((k, affinity.translate(affinity.rotate(parts[k], ang, origin=(0, 0)), dx, dy), ang, dx, dy))
    return placed


def verify(placed, a):
    sw, sl = a.sheet
    ok = box(a.margin - 0.05, max(a.clamp, a.margin) - 0.05, sl - a.margin + 0.05, sw - a.margin + 0.05)
    gs = [g for _, g, *_ in placed]
    mind = None
    for i, g in enumerate(gs):
        if not ok.contains(g):
            sys.exit(f"nest check failed: part {i} outside usable area")
        for h in gs[i + 1:]:
            d = g.distance(h)
            mind = d if mind is None else min(mind, d)
    if mind is not None and mind < a.gap - 0.05:
        sys.exit(f"nest check failed: gap {mind:.2f} < {a.gap}")
    return mind


def summary(placed, parts, a):
    cnt = Counter(k for k, *_ in placed)
    used = sum(parts[k].area * n for k, n in cnt.items())
    return {"counts": dict(cnt), "utilisation": round(used / (a.sheet[0] * a.sheet[1]), 4),
            "min_gap_mm": round(verify(placed, a) or 0, 2)}


_SVG_IDS = count()
COLOURS = ["#2f6fa3", "#c47d24", "#3c8a5a", "#8a4fa3"]


def svg(placed, parts, a, fn=None):
    """Sheet drawing; 2400 length across, clamp zone at the bottom. Writes fn or returns markup.
    Each blank outline is defined once and placed with <use>, keeping the page small."""
    sw, sl = a.sheet
    names = list(parts)
    uid = next(_SVG_IDS)  # unique ids when several drawings share one page
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-40 -20 {sl + 100} {sw + 90}">',
           f'<rect x="0" y="0" width="{sl}" height="{sw}" fill="#dfe4e8" stroke="#7a8690" stroke-width="3"/>',
           f'<rect x="0" y="{sw - a.clamp}" width="{sl}" height="{a.clamp}" fill="#c3cad0"/>',
           f'<text x="{sl / 2}" y="{sw - a.clamp / 2 + 10}" text-anchor="middle" fill="#5b6770" '
           f'font-family="monospace" font-size="30">CLAMP ZONE {a.clamp:g} mm</text>']
    out.append("<defs>")
    for i, k in enumerate(names):
        g = parts[k].simplify(0.3)
        d = "".join("M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in r.coords) + "Z" for r in [g.exterior, *g.interiors])
        out.append(f'<path id="p{uid}_{i}" d="{d}" fill="{COLOURS[i % 4]}" fill-opacity=".85" fill-rule="evenodd"/>')
    out.append(f'</defs><g transform="translate(0 {sw}) scale(1 -1)">')
    for k, _, ang, dx, dy in placed:
        out.append(f'<use href="#p{uid}_{names.index(k)}" transform="translate({dx:.1f} {dy:.1f}) rotate({ang:.3f})"/>')
    out.append("</g>")
    for x in range(0, int(sl) + 1, 200):
        out.append(f'<text x="{x}" y="{sw + 50}" text-anchor="middle" fill="#7a8690" '
                   f'font-family="monospace" font-size="28">{x}</text>')
    out.append("</svg>")
    if fn is None:
        return "\n".join(out)
    open(fn, "w").write("\n".join(out))


PAGE = """<title>{title}</title>
<style>
:root{{--bg:#eef1f3;--ink:#1b2328;--muted:#5b6770;--line:#c8d0d6;--panel:#f8fafb}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{color-scheme:dark;--bg:#12171b;--ink:#e3e8ec;--muted:#93a0aa;--line:#2c353c;--panel:#182025}}}}
:root[data-theme="dark"]{{color-scheme:dark;--bg:#12171b;--ink:#e3e8ec;--muted:#93a0aa;--line:#2c353c;--panel:#182025}}
body{{background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif;padding-inline:16px;padding-block:28px 48px}}
main{{max-width:1100px;margin:0 auto;display:grid;gap:24px}}
h1{{font-size:24px;margin:0;text-wrap:balance}} h2{{font-size:18px;margin:0}}
.intro p,.notes{{color:var(--muted);max-width:75ch;margin:6px 0 0}}
.key{{display:flex;gap:18px;flex-wrap:wrap;margin-top:10px;font-size:13px;color:var(--muted)}}
.sw{{width:14px;height:14px;border-radius:2px;display:inline-block;vertical-align:-2px;margin-right:6px}}
section{{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:18px;display:grid;gap:12px}}
header{{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}}
dl{{display:flex;flex-wrap:wrap;gap:6px 22px;margin:0}} dl div{{display:grid}}
dt{{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}}
dd{{margin:0;font:500 15px ui-monospace,monospace;font-variant-numeric:tabular-nums}}
.plot{{overflow-x:auto}} .plot svg{{width:100%;min-width:560px;height:auto;display:block}}
</style>
<main>
<div class="intro"><h1>{title}</h1>
<p>{basis}</p>
<div class="key">{key}</div></div>
{sections}
</main>"""


def html(results, parts, a, fn, title, price):
    names = list(parts)
    key = "".join(f'<span><i class="sw" style="background:{COLOURS[i % 4]}"></i>{k}</span>' for i, k in enumerate(names))
    secs = []
    for name, (placed, summ) in results.items():
        cnt = " + ".join(f"{n} {k}" for k, n in summ["counts"].items())
        cost = ""
        if price and name != "kit":
            cost = f"<div><dt>Sheet cost / part</dt><dd>${price / sum(summ['counts'].values()):.2f}</dd></div>"
        secs.append(f'<section><header><h2>{"Mixed kit" if name == "kit" else name}</h2><dl>'
                    f"<div><dt>Per sheet</dt><dd>{cnt}</dd></div>"
                    f"<div><dt>Utilisation</dt><dd>{summ['utilisation'] * 100:.1f}%</dd></div>"
                    f"<div><dt>Min gap</dt><dd>{summ['min_gap_mm']:.1f} mm</dd></div>{cost}</dl></header>"
                    f'<div class="plot">{svg(placed, parts, a)}</div></section>')
    basis = (f"{a.sheet[0]:g} × {a.sheet[1]:g} mm sheet, {a.margin:g} mm edge margin, {a.gap:g} mm gap, "
             f"{a.clamp:g} mm clamp zone on one long edge, rotation 0°/180° only, no mirroring. "
             "Greedy true-shape nest of the unfolded blanks on a 1 mm raster, re-checked with exact geometry; "
             "a commercial nester may fit a part or two more."
             + (f" Sheet cost ${price:g}/sheet." if price else ""))
    page = PAGE.format(title=title, basis=basis, key=key, sections="\n".join(secs))
    open(fn, "w").write(page)
    size = len(page.encode())
    print(f"{fn}: {size:,} bytes" + (" (over 250,000 target)" if size > 250_000 else ""), file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("parts", nargs="+", help="NAME=FLAT.json from step_geometry.py --outline")
    ap.add_argument("--sheet", type=float, nargs=2, default=[1200, 2400], metavar=("W", "L"))
    ap.add_argument("--margin", type=float, default=10, help="edge margin, mm")
    ap.add_argument("--gap", type=float, default=5, help="part-to-part gap, mm")
    ap.add_argument("--clamp", type=float, default=100, help="no-part clamp zone along one long edge, mm")
    ap.add_argument("--svg", help="write PREFIX_<layout>.svg for each layout")
    ap.add_argument("--html", help="write a self-contained nest page for publishing")
    ap.add_argument("--title", default="Sheet Nest", help="page title for --html")
    ap.add_argument("--sheet-price", type=float, help="$/sheet shown as sheet cost per part in --html")
    a = ap.parse_args()
    parts = dict(p.split("=", 1) for p in a.parts)
    parts = {k: load(v) for k, v in parts.items()}

    out = {"sheet_mm": a.sheet, "margin_mm": a.margin, "gap_mm": a.gap, "clamp_zone_mm": a.clamp,
           "rotation": "0/180 only, no mirroring", "basis": "greedy true-shape nest, 1 mm raster",
           "layouts": {}}
    base, results = {}, {}
    for k in parts:
        best = None
        for b in bases(Polygon(parts[k].exterior)):
            pl = nest(parts, {k: b}, [k], a)
            if best is None or len(pl) > len(best[1]):
                best = (b, pl)
        base[k] = best[0]
        out["layouts"][k] = {"base_angle_deg": best[0], **summary(best[1], parts, a)}
        results[k] = (best[1], out["layouts"][k])
        if a.svg:
            svg(best[1], parts, a, f"{a.svg}_{k}.svg")
    if len(parts) > 1:
        pl = nest(parts, base, list(parts), a)
        out["layouts"]["kit"] = {"base_angle_deg": base, **summary(pl, parts, a)}
        results["kit"] = (pl, out["layouts"]["kit"])
        if a.svg:
            svg(pl, parts, a, f"{a.svg}_kit.svg")
    if a.html:
        html(results, parts, a, a.html, a.title, a.sheet_price)
    json.dump(out, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
