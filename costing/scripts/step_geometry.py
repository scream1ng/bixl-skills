#!/usr/bin/env python3
"""Extract sheet-metal costing geometry from a single-body STEP file.

Usage: python step_geometry.py PART.step [--png FLAT.png] [--outline FLAT.json] [--thickness T] > GEOMETRY.json
Requires OCP (pip install cadquery-ocp) and numpy; matplotlib only for --png;
shapely only for --outline (flat polygon with holes, input for nest.py).

Unfolds one skin of the formed solid by isometric triangle placement, so
results are skin-based approximations (not neutral-axis flat patterns).
"""
import argparse, json, sys
from collections import defaultdict, deque

import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepGProp import BRepGProp
from OCP.BRepLProp import BRepLProp_SLProps
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepTools import BRepTools
from OCP.Bnd import Bnd_Box
from OCP.GProp import GProp_GProps
from OCP.GeomAbs import GeomAbs_Plane
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_IN, TopAbs_REVERSED, TopAbs_SOLID, TopAbs_WIRE
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape, TopTools_IndexedMapOfShape
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Pnt

STEEL_DENSITY = 7.85e-6  # kg/mm3


def props(shape, kind):
    g = GProp_GProps()
    {"vol": BRepGProp.VolumeProperties_s, "area": BRepGProp.SurfaceProperties_s,
     "len": BRepGProp.LinearProperties_s}[kind](shape, g)
    return g.Mass()


def is_plane(face):
    return BRepAdaptor_Surface(face).GetType() == GeomAbs_Plane


def plane_normal(face):
    d = BRepAdaptor_Surface(face).Plane().Axis().Direction()
    v = np.array([d.X(), d.Y(), d.Z()])
    return -v if face.Orientation() == TopAbs_REVERSED else v


def is_edge_face(shape, face, probe_mm):
    """Thickness (edge) face if points probe_mm inside along -normal stay in material."""
    loc = TopLoc_Location()
    tri = BRep_Tool.Triangulation_s(face, loc)
    ad = BRepAdaptor_Surface(face)
    inside = total = 0
    for j in range(1, tri.NbTriangles() + 1, max(1, tri.NbTriangles() // 7)):
        uv = [tri.UVNode(k) for k in tri.Triangle(j).Get()]
        u = sum(p.X() for p in uv) / 3
        v = sum(p.Y() for p in uv) / 3
        pr = BRepLProp_SLProps(ad, u, v, 1, 1e-6)
        if not pr.IsNormalDefined():
            continue
        n, p = pr.Normal(), pr.Value()
        if face.Orientation() == TopAbs_REVERSED:
            n.Reverse()
        q = gp_Pnt(p.X() - probe_mm * n.X(), p.Y() - probe_mm * n.Y(), p.Z() - probe_mm * n.Z())
        total += 1
        inside += BRepClass3d_SolidClassifier(shape, q, 1e-4).State() == TopAbs_IN
    return total and inside / total > 0.5


def unfold(faces):
    """Place one skin's triangles in 2D preserving edge lengths. Returns 2D points, tris, cut length, area, pieces."""
    vid, P, T = {}, [], []
    for f in faces:
        loc = TopLoc_Location()
        t = BRep_Tool.Triangulation_s(f, loc)
        tr = loc.Transformation()
        pts = []
        for j in range(1, t.NbNodes() + 1):
            q = t.Node(j).Transformed(tr)
            key = (round(q.X(), 3), round(q.Y(), 3), round(q.Z(), 3))
            if key not in vid:
                vid[key] = len(P)
                P.append(key)
            pts.append(vid[key])
        for j in range(1, t.NbTriangles() + 1):
            a, b, c = (pts[k - 1] for k in t.Triangle(j).Get())
            if len({a, b, c}) == 3:
                T.append((a, b, c))
    P = np.array(P)
    edges = defaultdict(list)
    for ti, tv in enumerate(T):
        for e in ((tv[0], tv[1]), (tv[1], tv[2]), (tv[2], tv[0])):
            edges[tuple(sorted(e))].append(ti)

    Q = {}

    def place(a, b, c, away=None):
        pa, pb = Q[a], Q[b]
        L = np.linalg.norm(P[b] - P[a])
        la, lb = np.linalg.norm(P[c] - P[a]), np.linalg.norm(P[c] - P[b])
        u = (pb - pa) / np.linalg.norm(pb - pa)
        x = (la ** 2 - lb ** 2 + L ** 2) / (2 * L)
        y = np.sqrt(max(la ** 2 - x ** 2, 0))
        n = np.array([-u[1], u[0]])
        base = pa + x * u
        c1, c2 = base + y * n, base - y * n
        if away is None:
            return c1
        return c1 if np.dot(c1 - base, away - base) < 0 else c2

    placed = [False] * len(T)
    pieces = 0
    for start in range(len(T)):  # each disconnected piece starts its own frame
        if placed[start]:
            continue
        pieces += 1
        a, b, c = T[start]
        if a not in Q and b not in Q:
            off = np.array([0.0, 0.0]) if not Q else np.array([max(p[0] for p in Q.values()) + 50, 0.0])
            Q[a] = off
            Q[b] = off + np.array([np.linalg.norm(P[b] - P[a]), 0.0])
        elif b not in Q:  # touches an earlier piece at a vertex: keep that vertex
            Q[b] = Q[a] + np.array([np.linalg.norm(P[b] - P[a]), 0.0])
        elif a not in Q:
            Q[a] = Q[b] - np.array([np.linalg.norm(P[b] - P[a]), 0.0])
        if c not in Q:
            Q[c] = place(a, b, c)
        placed[start] = True
        dq = deque([start])
        while dq:
            tv = T[dq.popleft()]
            for e in ((tv[0], tv[1]), (tv[1], tv[2]), (tv[2], tv[0])):
                opp = next(x for x in tv if x not in e)
                for tj in edges[tuple(sorted(e))]:
                    if placed[tj]:
                        continue
                    w = next(x for x in T[tj] if x not in e)
                    if w not in Q:
                        Q[w] = place(e[0], e[1], w, Q[opp])
                    placed[tj] = True
                    dq.append(tj)
    boundary = sum(np.linalg.norm(Q[a] - Q[b]) for (a, b), ts in edges.items() if len(ts) == 1)
    area = sum(np.linalg.norm(np.cross(P[b] - P[a], P[c] - P[a])) / 2 for a, b, c in T)
    return Q, T, boundary, area, pieces


def min_rect(points):
    best = None
    for ang in np.arange(0, 180, 0.25):
        t = np.radians(ang)
        R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
        with np.errstate(all="ignore"):  # spurious BLAS warnings on macOS
            G = points @ R.T
        w, h = np.ptp(G[:, 0]), np.ptp(G[:, 1])
        if best is None or w * h < best[0]:
            best = (w * h, w, h, ang)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step")
    ap.add_argument("--png", help="write flat-pattern preview image")
    ap.add_argument("--short-flat-mm", type=float, default=10.0,
                    help="flag flats narrower than this between bends")
    ap.add_argument("--outline", help="write unfolded flat polygon (exterior + holes) as JSON for nest.py")
    ap.add_argument("--thickness", type=float, help="override auto-detected thickness (mm)")
    args = ap.parse_args()

    r = STEPControl_Reader()
    if r.ReadFile(args.step) != 1:
        sys.exit("cannot read STEP")
    r.TransferRoots()
    s = r.OneShape()
    solids = 0
    ex = TopExp_Explorer(s, TopAbs_SOLID)
    while ex.More():
        solids += 1
        ex.Next()
    BRepMesh_IncrementalMesh(s, 0.1, False, 0.1, True)

    box = Bnd_Box()
    BRepBndLib.Add_s(s, box)
    x0, y0, z0, x1, y1, z1 = box.Get()
    vol = props(s, "vol")

    # Thickness: most common offset between parallel planar face pairs.
    planes = []
    fmap = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(s, TopAbs_FACE, fmap)
    nf = fmap.Extent()
    face = lambda i: TopoDS.Face_s(fmap.FindKey(i))
    for i in range(1, nf + 1):
        f = face(i)
        if is_plane(f):
            pl = BRepAdaptor_Surface(f).Plane()
            d, o = pl.Axis().Direction(), pl.Location()
            n = np.array([d.X(), d.Y(), d.Z()])
            planes.append((n, np.dot(n, [o.X(), o.Y(), o.Z()]), props(f, "area")))
    gaps = defaultdict(float)
    for i, (n1, d1, a1) in enumerate(planes):
        for n2, d2, a2 in planes[i + 1:]:
            dot = np.dot(n1, n2)
            if abs(dot) > 0.9999:
                g = round(abs(d1 - np.sign(dot) * d2), 2)
                if 0.3 < g < 25:
                    gaps[g] += min(a1, a2)
    thickness = max(gaps, key=gaps.get) if gaps else round(2 * vol / props(s, "area"), 2)
    if args.thickness:
        thickness = args.thickness

    # Split faces into edge faces and the two skins.
    edge_faces = {i for i in range(1, nf + 1) if is_edge_face(s, face(i), thickness * 1.5)}
    efm = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(s, TopAbs_EDGE, TopAbs_FACE, efm)
    adj = defaultdict(set)
    for k in range(1, efm.Extent() + 1):
        ids = [fmap.FindIndex(x) for x in efm.FindFromIndex(k)]
        for a in ids:
            adj[a].update(b for b in ids if b != a)
    seen, skins = set(), []
    for i in range(1, nf + 1):
        if i in edge_faces or i in seen:
            continue
        stack, comp = [i], []
        seen.add(i)
        while stack:
            x = stack.pop()
            comp.append(x)
            for y in adj[x]:
                if y not in edge_faces and y not in seen:
                    seen.add(y)
                    stack.append(y)
        skins.append(comp)
    skins.sort(key=len, reverse=True)
    skin = skins[0]
    skin_set = set(skin)

    # Bends: connected non-planar groups on the skin, angle from planar neighbours.
    bends, used = [], set()
    for i in skin:
        if is_plane(face(i)) or i in used:
            continue
        group, stack = [i], [i]
        used.add(i)
        while stack:
            x = stack.pop()
            for y in adj[x]:
                if y in skin_set and not is_plane(face(y)) and y not in used:
                    used.add(y)
                    group.append(y)
                    stack.append(y)
        nbrs = sorted({y for x in group for y in adj[x] if y in skin_set and is_plane(face(y))})
        ang = None
        if len(nbrs) == 2:
            dot = np.clip(np.dot(plane_normal(face(nbrs[0])), plane_normal(face(nbrs[1]))), -1, 1)
            ang = round(float(np.degrees(np.arccos(dot))), 1)
        bends.append({"deviation_deg": ang, "adjacent_flats": len(nbrs)})

    # Holes: inner wires on skin planar faces.
    holes = []
    for i in skin:
        f = face(i)
        if not is_plane(f):
            continue
        outer = BRepTools.OuterWire_s(f)
        w = TopExp_Explorer(f, TopAbs_WIRE)
        while w.More():
            wire = TopoDS.Wire_s(w.Current())
            if not wire.IsSame(outer):
                per = props(wire, "len")
                holes.append({"perimeter_mm": round(per, 1), "round_equiv_dia_mm": round(per / np.pi, 1)})
            w.Next()

    Q, T, cut_len, skin_area, pieces = unfold([face(i) for i in skin])
    pts = np.array(list(Q.values()))
    _, w, h, ang = min_rect(pts)
    envelope = sorted([round(w, 1), round(h, 1)])

    # Short flats: planar skin faces touching two or more bends, width ~ area / long side.
    short = []
    bend_faces = {i for i in skin if not is_plane(face(i))}
    for i in skin:
        f = face(i)
        if is_plane(f) and len(adj[i] & bend_faces) >= 2:
            a = props(f, "area")
            fb = Bnd_Box()
            BRepBndLib.Add_s(f, fb)
            b = fb.Get()
            longest = max(b[3] - b[0], b[4] - b[1], b[5] - b[2])
            if longest and a / longest < args.short_flat_mm:
                short.append({"area_mm2": round(a), "approx_width_mm": round(a / longest, 1)})

    out = {
        "source": args.step,
        "solids": solids,
        "bbox_mm": [round(x1 - x0, 1), round(y1 - y0, 1), round(z1 - z0, 1)],
        "thickness_mm": thickness,
        "volume_mm3": round(vol),
        "mass_kg_steel": round(vol * STEEL_DENSITY, 3),
        "skins_found": len(skins),
        "skin_face_counts": [len(c) for c in skins],
        "flat_envelope_mm": envelope,
        "flat_envelope_basis": "min-area rectangle of one unfolded skin; approximate, not neutral-axis",
        "flat_area_mm2": round(skin_area),
        "coated_area_m2_approx": round((2 * skin_area + cut_len * thickness) / 1e6, 4),
        "cut_length_mm": round(cut_len),
        "pierces": len(holes) + 1,
        "holes": holes,
        "bend_count": len(bends),
        "bends": bends,
        "short_flats_between_bends": short,
        "warnings": [],
    }
    if solids != 1:
        out["warnings"].append("expected one solid; multi-body files need per-body handling")
    if len(skins) != 2:
        out["warnings"].append("skin split is not two components; check edge-face classification")
    if any(b["adjacent_flats"] != 2 for b in bends):
        out["warnings"].append("some bend groups do not sit between exactly two flats; audit visually")
    if pieces != 1:
        out["warnings"].append(f"disconnected unfold: {pieces} pieces laid 50 mm apart; flat envelope spans them all")
    json.dump(out, sys.stdout, indent=1)
    print()

    if args.outline:
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        tris = [Polygon([Q[a], Q[b], Q[c]]) for a, b, c in T]
        u = unary_union([p.buffer(0.01) for p in tris if p.area > 1e-9]).buffer(-0.01)
        if u.geom_type != "Polygon":
            u = max(u.geoms, key=lambda g: g.area)
        u = u.simplify(0.2)
        x0, y0 = u.bounds[:2]
        ring = lambda r: [[round(x - x0, 3), round(y - y0, 3)] for x, y in r.coords]
        with open(args.outline, "w") as fh:
            json.dump({"source": args.step, "thickness_mm": thickness, "area_mm2": round(u.area),
                       "exterior": ring(u.exterior), "interiors": [ring(r) for r in u.interiors]}, fh)

    if args.png:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        t = np.radians(ang)
        R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
        fig, ax = plt.subplots(figsize=(8, 8))
        for a, b, c in T:
            tri = np.array([Q[a], Q[b], Q[c]]) @ R.T
            ax.fill(tri[:, 0], tri[:, 1], color=(0.5, 0.6, 0.85), lw=0)
        ax.set_aspect("equal")
        ax.grid(True)
        ax.set_title(f"Unfolded skin, envelope {envelope[0]} x {envelope[1]} mm")
        plt.savefig(args.png, dpi=80)


if __name__ == "__main__":
    main()
