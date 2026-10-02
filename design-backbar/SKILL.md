---
name: design-backbar
description: Design laser-cut backbar (backgauge) jig plates for the LVD press brake from a STEP holding a formed sheet-metal part and its flat pattern, for bends where the blank edge is not parallel to the bend line. Gives one DXF per plate and an HTML preview. Use when the user asks for a backbar, backgauge jig or bend gauge plate, or wants to bend a part without gauge tabs.
---

# Design Backbar

A backbar is a 6 mm laser-cut plate that slips over an LVD backgauge finger. Its front edge carries a pocket cut to the blank's own outline, so a blank whose edge is not parallel to the bend still gauges square, with no sacrificial gauge tab on the part. One plate per bend.

Every number comes from exact OCP geometry in the bundled script. Never read a dimension off a picture, and never draw a plate by hand.

## Shop standard (fixed)

| Item | Value |
|---|---|
| Plate | 100 mm wide (along the bend) × 6 mm thick |
| Finger slot | 50.2 wide × 20 deep, centred, at the back edge |
| Blank tip to finger tip | 50 mm (so blank tip to plate back edge is 70) |
| Wrap past the blank tip toward the bend | 20 mm, never under 10 |
| Pocket clearance around the blank | 0.1 mm |
| Plate left each side of the pocket | at least 10 mm (less is an error, no DXF) |

The plate is not resized to suit a part. If a part does not fit, say so and stop; the user decides what to do.

## Input

One STEP holding both the formed part and its flat pattern body (SolidWorks: export both bodies together). The flat pattern must keep its bend regions as separate faces (Flat-Pattern feature, "Merge faces" unticked) because the bend lines are read from them. Extra bodies in the file are ignored. If the flat pattern cannot be told apart, the script says so; ask the user which body it is and pass `--flat N`.

Ask for the flat pattern without gauge tabs. If tabs are still on it the pocket simply includes them (it still fits a blank cut with or without tabs) and the script adds a note.

## Run

1. Tell the user the CAD engine takes about a minute to install the first time.
2. Extract the script from this file; do not retype it:
   `awk '/^```python backbar.py$/{f=1;next}/^```$/{f=0}f' "<this skill's folder>/SKILL.md" > backbar.py`
   Only if this file is not on disk, write the code block below to `backbar.py` exactly as it is.
3. `uv run --no-project --python 3.12 --with "cadquery-ocp>=7.8,<7.9" --with "ezdxf>=1.3,<2" python backbar.py PART.step OUT`
   Without `uv`: `pip install "cadquery-ocp>=7.8,<7.9" "ezdxf>=1.3,<2"` once, then plain `python`. OCP 8 does not work. If it cannot install (no network), say so and stop.
4. Give the user `OUT/preview.html` (overview, one dimensioned drawing per plate, results table) and every `OUT/*_backbar_B<n>.dxf`, with a short plain-words summary per plate (below). Do not ask setup questions first; the standard is fixed.

Options, used only when the user asks or a result calls for it:

- `--wrap 10..20`: wrap past the blank tip (default 20).
- `--die-clear MM`: least distance from the bend line to the plate front edge (default 8). The wrap is shortened to keep it.
- `--side N=+` or `N=-`: gauge bend N from the other end of the blank. Run once, read `side` in the output, pass the opposite sign.
- `--flat N`: solid number of the flat pattern.

## What the script decides

- **Bend lines**: the centre of each bend strip on the flat pattern.
- **Gauged end**: for each bend, the end of the blank that has no other bend between it and the bend line, so the blank lies flat in the pocket. When both ends are free (one-bend parts) it takes the nearer end; check the preview and flip with `--side` if the user gauges the other end.
- **Plate position**: front edge parallel to the bend line, 20 mm forward of the deepest point of the blank; finger slot centred on the pocket.
- **Pocket**: the blank's outer outline offset 0.1 mm outward, with arc corners. Holes in the blank are ignored.

## Reading the result

The script prints JSON; the same numbers are in the preview table. Report them in plain words, per plate:

- `wrap_mm`: how far the plate wraps past the blank tip. Under 20 means the die clearance shortened it; under 10 comes with a warning.
- `front_edge_to_bend_mm`: bend line to plate front edge. Always quote it and ask the user to check it against the die in use. The 8 mm default is an assumption, not a measured tooling limit.
- `bend_to_finger_tip_mm`: bend line to backgauge finger tip with the plate fitted and the blank seated in the pocket.
- `clearance_mm`: measured gap between plate and blank; must read 0.1. Anything else is a failure: say so and do not hand over that DXF.
- `warnings`, `error`, `notes`: pass each on as one plain sentence with the next action. A plate with an `error` has no DXF. Never hide a warning and never call a warned plate ready.

DXF: mm, 1:1, front edge along X, lines and arcs as true entities, spline edges as fine polylines. Cut one per bend from 6 mm.

## Not checked (say so when relevant, never imply it was)

- Collision of the plate with the die, punch or an already formed flange.
- Whether the backgauge can reach the stated distance, and finger height (R).
- Bend order, and whether the operator can hold the part.
- Parts whose bend has other bends on both sides: the script reports an error for that bend. Do not improvise a plate.

## Rules

- Change the constants at the top of the script only when the user says the shop standard changed.
- Never hand-edit a DXF or the preview; change an option and rerun.
- A script error is reported as one plain sentence plus the next action, never raw output.
- The preview is a picture for checking. The DXF is what gets cut.

## Script

```python backbar.py
#!/usr/bin/env python3
"""Backbar jig plates for an LVD press brake: STEP (formed part + flat pattern) -> DXF per plate + preview.html."""
import argparse, html, json, math, os, sys
import ezdxf
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon,
                                BRepBuilderAPI_Sewing, BRepBuilderAPI_Transform)
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepGProp import BRepGProp
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffset
from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
from OCP.Bnd import Bnd_Box
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.GProp import GProp_GProps
from OCP.GeomAbs import GeomAbs_Arc, GeomAbs_Circle, GeomAbs_Line, GeomAbs_Plane
from OCP.STEPControl import STEPControl_Reader
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_REVERSED, TopAbs_SOLID, TopAbs_VERTEX, TopAbs_WIRE
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape, TopTools_IndexedMapOfShape
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Ax3, gp_Dir, gp_Pnt, gp_Trsf

# Shop standard (measured from 818165 Backbar.STEP). Change here only if the standard changes.
PLATE_W, PLATE_T = 100.0, 6.0        # plate width along the bend; thickness (cut from 6 mm)
NOTCH_W, NOTCH_D = 50.2, 20.0        # slot over the 50 mm LVD backgauge finger
TIP_TO_FINGER = 50.0                 # deepest point of the blank -> finger tip (notch bottom)
CLEAR = 0.1                          # pocket offset around the blank
PROT_MAX, PROT_MIN = 20.0, 10.0      # how far the plate wraps forward past the blank tip
MIN_WALL = 10.0                      # plate material left each side of the pocket


def die(msg):
    sys.exit("ERROR: " + msg)


def sub(shape, kind, cast):
    e, out = TopExp_Explorer(shape, kind), []
    while e.More():
        out.append(cast(e.Current())); e.Next()
    return out


def faces(s): return sub(s, TopAbs_FACE, TopoDS.Face_s)
def edges(s): return sub(s, TopAbs_EDGE, TopoDS.Edge_s)
def pts(s): return [(p.X(), p.Y(), p.Z()) for p in (BRep_Tool.Pnt_s(v) for v in sub(s, TopAbs_VERTEX, TopoDS.Vertex_s))]
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def vsub(a, b): return tuple(x - y for x, y in zip(a, b))
def moved(shape, trsf): return BRepBuilderAPI_Transform(shape, trsf, True).Shape()


def area(s):
    g = GProp_GProps(); BRepGProp.SurfaceProperties_s(s, g); return g.Mass()


def volume(s):
    g = GProp_GProps(); BRepGProp.VolumeProperties_s(s, g); return g.Mass()


def bbox(s):
    b = Bnd_Box(); BRepBndLib.AddOptimal_s(s, b, False, False); return b.Get()  # xmin ymin zmin xmax ymax zmax


def plane_of(face):
    a = BRepAdaptor_Surface(face)
    if a.GetType() != GeomAbs_Plane:
        return None
    d = a.Plane().Axis().Direction()
    return (d.X(), d.Y(), d.Z())


def flat_info(solid):
    """(normal, top faces, thickness) when the solid is one flat sheet, else None."""
    planar = [(f, plane_of(f)) for f in faces(solid)]
    planar = [(f, n) for f, n in planar if n]
    if not planar:
        return None
    n = max(planar, key=lambda fn: area(fn[0]))[1]
    hs = [dot(p, n) for p in pts(solid)]
    t = max(hs) - min(hs)
    top = [f for f, m in planar if abs(dot(m, n)) > 0.9999 and abs(dot(pts(f)[0], n) - max(hs)) < 0.02]
    a = sum(area(f) for f in top)
    return (n, top, t) if t > 0.3 and abs(volume(solid) - a * t) < 0.03 * a * t else None


def find_bends(solid, top):
    """Bend zones = strip faces between flanges on the flat pattern's top side."""
    fmap = TopTools_IndexedMapOfShape(); TopExp.MapShapes_s(solid, TopAbs_FACE, fmap)
    emap = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(solid, TopAbs_EDGE, TopAbs_FACE, emap)
    ids = {fmap.FindIndex(f): f for f in top}
    adj = {i: [] for i in ids}
    for k in range(1, emap.Extent() + 1):
        fs = [fmap.FindIndex(f) for f in emap.FindFromIndex(k)]
        if len(fs) == 2 and fs[0] != fs[1] and all(i in ids for i in fs):
            e = TopoDS.Edge_s(emap.FindKey(k))
            adj[fs[0]].append((fs[1], e)); adj[fs[1]].append((fs[0], e))
    root = max(ids, key=lambda i: area(ids[i]))
    depth, queue = {root: 0}, [root]
    while queue:
        i = queue.pop(0)
        for j, _ in adj[i]:
            if j not in depth:
                depth[j] = depth[i] + 1; queue.append(j)
    bends = []
    for i in sorted(i for i in depth if depth[i] % 2):
        es = [e for _, e in adj[i]]
        if len(es) != 2 or any(BRepAdaptor_Curve(e).GetType() != GeomAbs_Line for e in es):
            die("a bend zone on the flat pattern is not a simple strip between two straight lines.")
        (a1, b1), (a2, _) = pts(es[0]), pts(es[1])
        L = math.dist(a1, b1); d = tuple(x / L for x in vsub(b1, a1))
        m1 = tuple((x + y) / 2 for x, y in zip(a1, b1))
        w = vsub(a2, a1); off = vsub(w, tuple(dot(w, d) * x for x in d))   # line 1 -> line 2, square to the bend
        bends.append(dict(face=ids[i], p=tuple(x + o / 2 for x, o in zip(m1, off)), d=d, half=math.hypot(*off) / 2))
    return bends


def rect(x0, y0, x1, y1):
    p = BRepBuilderAPI_MakePolygon()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        p.Add(gp_Pnt(x, y, 0))
    p.Close()
    return BRepBuilderAPI_MakeFace(p.Wire()).Face()


def outline(face, defl=0.02):
    """Outer wire as an ordered 2D point list (preview only)."""
    out, we = [], BRepTools_WireExplorer(BRepTools.OuterWire_s(face))
    while we.More():
        e = we.Current(); c = BRepAdaptor_Curve(e); d = GCPnts_QuasiUniformDeflection(c, defl)
        seg = [(d.Value(k).X(), d.Value(k).Y()) for k in range(1, d.NbPoints() + 1)]
        out += seg[::-1] if e.Orientation() == TopAbs_REVERSED else seg
        we.Next()
    return out


def write_dxf(face, path):
    doc = ezdxf.new("R2000"); doc.units = ezdxf.units.MM; msp = doc.modelspace()
    for e in edges(face):
        c = BRepAdaptor_Curve(e); a, b = c.FirstParameter(), c.LastParameter()
        P = lambda t: (c.Value(t).X(), c.Value(t).Y())
        if c.GetType() == GeomAbs_Line:
            msp.add_line(P(a), P(b))
        elif c.GetType() == GeomAbs_Circle:
            o, r = c.Circle().Location(), c.Circle().Radius()
            ang = lambda t: math.degrees(math.atan2(P(t)[1] - o.Y(), P(t)[0] - o.X())) % 360
            if abs(b - a) > 2 * math.pi - 1e-9:
                msp.add_circle((o.X(), o.Y()), r)
            else:
                s, m, f = ang(a), ang((a + b) / 2), ang(b)
                if (m - s) % 360 > (f - s) % 360:   # mid point not on the CCW sweep s->f: swap
                    s, f = f, s
                msp.add_arc((o.X(), o.Y()), r, s, f)
        else:   # spline / offset curve: fine polyline
            d = GCPnts_QuasiUniformDeflection(c, 0.005)
            msp.add_lwpolyline([(d.Value(k).X(), d.Value(k).Y()) for k in range(1, d.NbPoints() + 1)])
    doc.saveas(path)


def build_plate(blank, bends, i, side, prot_max, die_clear):
    """Plate for bend i in its own frame: X along the bend, Y from the bend line toward the backgauge."""
    b = bends[i]
    n = b["n"]
    for s in ((1, -1) if side is None else (side,)):
        d = tuple(s * x for x in b["d"])
        T = gp_Trsf(); T.SetTransformation(gp_Ax3(gp_Pnt(*b["p"]), gp_Dir(*n), gp_Dir(*d)))
        loc = TopoDS.Face_s(moved(blank, T))
        others = [y for j, o in enumerate(bends) if j != i for _, y, _ in pts(moved(o["face"], T))]
        b.setdefault("opts", []).append(dict(s=s, T=T, loc=loc, tip=bbox(loc)[4], free=all(y < b["half"] + 0.01 for y in others)))
    free = [o for o in b["opts"] if o["free"]]
    if not free:
        return dict(bend=i + 1, error="another bend lies on the gauged side of this bend; the blank cannot lie flat in a pocket for it")
    o = min(free, key=lambda o: o["tip"])            # nearer blank end
    tip, loc = o["tip"], o["loc"]
    prot = min(prot_max, tip - die_clear)
    warn = []
    if prot < PROT_MIN:
        warn.append(f"blank reaches only {tip:.1f} mm behind the bend line: wrap is {prot:.1f} mm, under {PROT_MIN:.0f}")
    if prot <= 1:
        return dict(bend=i + 1, error=f"blank reaches only {tip:.1f} mm behind the bend line; no room for a pocket")
    front = tip - prot
    x0, _, _, x1, _, _ = bbox(BRepAlgoAPI_Common(loc, rect(-1e4, front, 1e4, tip + 1)).Shape())
    cx = (x0 + x1) / 2
    wall = PLATE_W / 2 - (x1 - x0) / 2 - CLEAR
    if wall < MIN_WALL:
        return dict(bend=i + 1, error=f"blank is {x1 - x0:.1f} mm wide at the pocket: does not fit the {PLATE_W:.0f} mm "
                    f"standard plate with {MIN_WALL:.0f} mm of material each side")
    body = BRepAlgoAPI_Cut(rect(cx - PLATE_W / 2, front, cx + PLATE_W / 2, tip + TIP_TO_FINGER + NOTCH_D),
                           rect(cx - NOTCH_W / 2, tip + TIP_TO_FINGER, cx + NOTCH_W / 2, tip + TIP_TO_FINGER + NOTCH_D + 1)).Shape()
    solid_blank = BRepBuilderAPI_MakeFace(BRepTools.OuterWire_s(loc)).Face()     # holes ignored
    off = BRepOffsetAPI_MakeOffset(solid_blank, GeomAbs_Arc); off.Perform(CLEAR)
    if not off.IsDone():
        return dict(bend=i + 1, error="could not offset the blank outline by the pocket clearance")
    if off.Shape().ShapeType() != TopAbs_WIRE:
        return dict(bend=i + 1, error="pocket offset did not give one closed outline; check the flat pattern outline")
    pocket = BRepBuilderAPI_MakeFace(TopoDS.Wire_s(off.Shape())).Face()
    if area(pocket) < area(solid_blank):
        return dict(bend=i + 1, error="pocket offset went inward; check the flat pattern outline")
    pieces = sorted(faces(BRepAlgoAPI_Cut(body, pocket).Shape()), key=area, reverse=True)
    if len(pieces) > 1 and area(pieces[1]) > 1:
        warn.append("the pocket cuts the plate into separate pieces; largest kept")
    plate = pieces[0]
    gap = BRepExtrema_DistShapeShape(plate, solid_blank); gap.Perform()
    return dict(bend=i + 1, side="+" if o["s"] > 0 else "-", plate=plate, T=o["T"], loc=loc, cx=cx, x0=x0, x1=x1, front=front, tip=tip, warnings=warn,
                wrap_mm=round(prot, 2), front_edge_to_bend_mm=round(front, 2),
                bend_to_finger_tip_mm=round(tip + TIP_TO_FINGER, 2), wall_each_side_mm=round(wall, 2),
                clearance_mm=round(gap.Value(), 3), plate_area_mm2=round(area(plate), 1))


def detail(p):
    """Dimensioned drawing of one plate in its own frame (bend line horizontal at the bottom, backgauge up)."""
    cx, front, tip = p["cx"], p["front"], p["tip"]
    finger, back, L, R = tip + TIP_TO_FINGER, tip + TIP_TO_FINGER + NOTCH_D, cx - PLATE_W / 2, cx + PLATE_W / 2
    num = lambda v: f"{round(v, 2):g}"
    shape = lambda pp, cls: f'<polygon class="{cls}" points="' + " ".join(f"{x:.2f},{-y:.2f}" for x, y in pp) + '"/>'
    line = lambda cls, x0, y0, x1, y1: f'<line class="{cls}" x1="{x0:.2f}" y1="{-y0:.2f}" x2="{x1:.2f}" y2="{-y1:.2f}"/>'
    def dim(x0, y0, x1, y1, label, side):
        mx, my = (x0 + x1) / 2, -(y0 + y1) / 2
        tx, ty, anchor = {"l": (mx - 1.5, my + 1.2, "end"), "r": (mx + 1.5, my + 1.2, "start"), "t": (mx, my - 1.2, "middle")}[side]
        return line("dim", x0, y0, x1, y1) + f'<text class="dt" x="{tx:.2f}" y="{ty:.2f}" text-anchor="{anchor}">{label}</text>'
    out = [shape(outline(rect(cx - 25, finger, cx + 25, back + 24)), "finger"), shape(outline(p["plate"]), "plate"),
           shape(outline(p["loc"]), "blank"), line("bend", L - 40, 0, R + 24, 0),
           line("ref", L, tip, R, tip), line("ref", L, finger, R, finger)]
    xr, xl, xl2 = R + 10, L - 10, L - 24
    for y in (0, front, tip, finger, back):                                   # right chain, bend line upward
        out.append(line("ext", R + 1, y, xr + 2, y))
    for y0, y1 in ((0, front), (front, tip), (tip, finger), (finger, back)):
        out.append(dim(xr, y0, xr, y1, num(y1 - y0), "r"))
    out += [line("ext", L - 1, front, xl - 2, front), line("ext", L - 1, back, xl - 2, back), dim(xl, front, xl, back, num(back - front), "l"),
            line("ext", L - 1, finger, xl2 - 2, finger), dim(xl2, 0, xl2, finger, num(finger), "l")]
    for x, y in ((cx - NOTCH_W / 2, back + 8), (cx + NOTCH_W / 2, back + 8), (L, back + 18), (R, back + 18)):
        out.append(line("ext", x, back + 1, x, y + 2))
    out += [dim(cx - NOTCH_W / 2, back + 8, cx + NOTCH_W / 2, back + 8, num(NOTCH_W), "t"), dim(L, back + 18, R, back + 18, num(PLATE_W), "t")]
    for a, b in ((L, p["x0"] - CLEAR), (p["x1"] + CLEAR, R)):                  # plate left each side of the pocket
        if b - a > 5:
            out += [line("ext", a, front - 1, a, front - 8), line("ext", b, front - 1, b, front - 8), dim(a, front - 6, b, front - 6, num(b - a), "t")]
    vb = f"{L - 46:.0f} {-(back + 26):.0f} {PLATE_W + 78:.0f} {back + 38:.0f}"
    return (f'<h4>Plate B{p["bend"]}: dimensions in mm (plate {PLATE_T:g} thick, pocket = part outline + {CLEAR:g})</h4>'
            f'<svg class="det" viewBox="{vb}">{"".join(out)}</svg>')


def preview(path, title, blank, bends, plates, thickness, notes):
    T0 = bends[0]["opts"][0]["T"]
    def poly(shape, T, cls):
        g = gp_Trsf(); g.Multiply(T0); g.Multiply(T.Inverted())
        pp = outline(TopoDS.Face_s(moved(shape, g)))
        allp.extend(pp)
        return f'<polygon class="{cls}" points="' + " ".join(f"{x:.2f},{-y:.2f}" for x, y in pp) + '"/>'
    allp, svg = [], []
    for p in plates:
        if "plate" in p:
            y = p["tip"] + TIP_TO_FINGER
            svg.append(poly(rect(p["cx"] - 25, y, p["cx"] + 25, y + 60), p["T"], "finger"))
            svg.append(poly(p["plate"], p["T"], "plate"))
            g = gp_Trsf(); g.Multiply(T0); g.Multiply(p["T"].Inverted())
            c = gp_Pnt(p["cx"], p["tip"] + 30, 0).Transformed(g)
            svg.append(f'<text class="id" x="{c.X():.1f}" y="{-c.Y():.1f}">B{p["bend"]}</text>')
    svg.append(poly(moved(blank, T0), T0, "blank"))
    for k, b in enumerate(bends):
        a = [gp_Pnt(*[b["p"][m] + s * 60 * b["d"][m] for m in range(3)]).Transformed(T0) for s in (-1, 1)]
        svg.append(f'<line class="bend" x1="{a[0].X():.2f}" y1="{-a[0].Y():.2f}" x2="{a[1].X():.2f}" y2="{-a[1].Y():.2f}"/>')
        c = gp_Pnt(*b["p"]).Transformed(T0)
        svg.append(f'<text x="{c.X():.1f}" y="{-c.Y() - 1.5:.1f}">bend {k + 1}</text>')
    xs, ys = [x for x, _ in allp], [-y for _, y in allp]
    vb = f"{min(xs) - 10:.0f} {min(ys) - 10:.0f} {max(xs) - min(xs) + 20:.0f} {max(ys) - min(ys) + 20:.0f}"
    cols = ["bend", "wrap_mm", "front_edge_to_bend_mm", "bend_to_finger_tip_mm", "wall_each_side_mm", "clearance_mm", "dxf"]
    rows = "".join("<tr>" + "".join(f"<td>{p.get(c, '')}</td>" for c in cols) + f"<td>{'; '.join(p.get('warnings', [])) or p.get('error', '')}</td></tr>" for p in plates)
    page = f"""<!doctype html><meta charset="utf-8"><title>{title} backbar</title>
<style>body{{font:14px system-ui;margin:16px;background:#fff;color:#111}}svg{{width:100%;max-height:70vh;border:1px solid #ccc}}
.plate{{fill:#8f93c8;fill-opacity:.55;stroke:#2b2f77;stroke-width:.4}}.blank{{fill:#c9a27a;fill-opacity:.6;stroke:#6b4a2a;stroke-width:.4}}
.finger{{fill:#999;fill-opacity:.35;stroke:#555;stroke-width:.3;stroke-dasharray:2 1}}.bend{{stroke:#d00;stroke-width:.4;stroke-dasharray:4 2}}
text{{font-size:4px;fill:#d00}}text.id{{font-size:9px;fill:#2b2f77;text-anchor:middle}}text.dt{{font-size:3.6px;fill:#111}}
svg.det{{max-width:680px;display:block}}.dim{{stroke:#111;stroke-width:.25;marker-start:url(#a);marker-end:url(#a)}}.ext{{stroke:#111;stroke-width:.15}}.ref{{stroke:#111;stroke-width:.2;stroke-dasharray:1.5 1}}table{{border-collapse:collapse;margin-top:12px}}td,th{{border:1px solid #ccc;padding:4px 8px;text-align:left}}</style>
<h3>{title}: backbar plates ({PLATE_W:.0f} wide &times; {PLATE_T:.0f} mm, blank {thickness:.2f} mm)</h3>
<svg viewBox="{vb}"><defs><marker id="a" viewBox="0 0 6 6" refX="6" refY="3" markerWidth="2.4" markerHeight="2.4" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0,0L6,3L0,6z"/></marker></defs>{''.join(svg)}</svg>
<p>Brown = flat blank, purple = plate, grey dashed = backgauge finger, red = bend line, black dashed = part tip and finger tip. Picture is for checking only; cut from the DXF.</p>
{''.join(detail(p) for p in plates if "plate" in p)}
<table><tr>{''.join(f'<th>{c.replace("_", " ")}</th>' for c in cols)}<th>notes</th></tr>{rows}</table>{''.join(f'<p><b>Note:</b> {x}</p>' for x in notes)}"""
    open(path, "w").write(page)
    return len(page)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step"); ap.add_argument("out")
    ap.add_argument("--wrap", type=float, default=PROT_MAX, help="mm the plate wraps past the blank tip (10-20)")
    ap.add_argument("--die-clear", type=float, default=8.0, help="min mm from bend line to plate front edge")
    ap.add_argument("--side", action="append", default=[], help="N=+ or N=- : force the gauged side of bend N")
    ap.add_argument("--flat", type=int, help="solid number of the flat pattern when it cannot be told apart")
    a = ap.parse_args()
    if not PROT_MIN <= a.wrap <= PROT_MAX:
        die(f"--wrap must be {PROT_MIN:.0f} to {PROT_MAX:.0f} mm.")
    sides = {}
    for s in a.side:
        k, _, v = s.partition("=")
        if not k.isdigit() or int(k) < 1 or v not in ("+", "-"):
            die("--side must look like 1=+ or 2=-.")
        sides[int(k) - 1] = 1 if v == "+" else -1
    r = STEPControl_Reader()
    if r.ReadFile(a.step) != 1:
        die("cannot read the STEP file.")
    r.TransferRoots()
    solids = sub(r.OneShape(), TopAbs_SOLID, TopoDS.Solid_s)
    info = {i: flat_info(s) for i, s in enumerate(solids)}
    flats = [i for i in info if info[i]]
    formed = [volume(s) for i, s in enumerate(solids) if not info[i]]
    if a.flat is not None:
        flats = [a.flat - 1] if info.get(a.flat - 1) else []
    elif len(flats) > 1:   # keep the flat body whose volume matches a formed body
        flats = [i for i in flats if any(abs(volume(solids[i]) - v) < 0.1 * v for v in formed)]
    if len(flats) != 1:
        die(f"need exactly one flat pattern body; found {len(flats)} among {len(solids)} solids. "
            "Export the formed part and its flat pattern together, or pass --flat N.")
    flat = solids[flats[0]]; n, top, t = info[flats[0]]
    notes = []
    if formed and volume(flat) > 1.01 * min(formed, key=lambda v: abs(v - volume(flat))):
        notes.append("flat pattern has more material than the formed part: gauge tabs are probably still on the blank, "
                     "so the pockets include them. Re-export the flat pattern without tabs for a clean pocket.")
    bends = find_bends(flat, top)
    if not bends:
        die("the flat pattern has no bend zones (one merged face). In SolidWorks untick 'Merge faces' on the Flat-Pattern feature and re-export.")
    for b in bends:
        b["n"] = n
    sew = BRepBuilderAPI_Sewing()
    for f in top:
        sew.Add(f)
    sew.Perform()
    uni = ShapeUpgrade_UnifySameDomain(sew.SewedShape(), True, True, False); uni.Build()
    fs = faces(uni.Shape())
    if len(fs) != 1:
        die("could not merge the flat pattern faces into one outline.")
    blank = fs[0]
    if any(k >= len(bends) for k in sides):
        die(f"--side names a bend the part does not have; it has {len(bends)} bend(s).")
    os.makedirs(a.out, exist_ok=True)
    title = os.path.splitext(os.path.basename(a.step))[0]
    plates = [build_plate(blank, bends, i, sides.get(i), a.wrap, a.die_clear) for i in range(len(bends))]
    for p in plates:
        if "plate" in p:
            p["dxf"] = f"{title}_backbar_B{p['bend']}.dxf"
            write_dxf(p["plate"], os.path.join(a.out, p["dxf"]))
    size = preview(os.path.join(a.out, "preview.html"), html.escape(title), blank, bends, plates, t, notes)
    keep = lambda p: {k: v for k, v in p.items() if k not in ("plate", "T", "loc", "cx", "x0", "x1", "front", "tip")}
    print(json.dumps(dict(part=title, blank_thickness_mm=round(t, 2), bends=len(bends), preview="preview.html",
                          preview_bytes=size, notes=notes, plates=[keep(p) for p in plates]), indent=1))


if __name__ == "__main__":
    main()
```
