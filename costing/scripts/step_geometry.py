#!/usr/bin/env python3
"""Extract sheet-metal costing geometry from a STEP file.

Usage: python step_geometry.py PART.step [--png FLAT.png] [--outline FLAT.json] [--thickness T] > GEOMETRY.json

A multi-body file is split into bodies; identical bodies are grouped with a
quantity and each group is reported under "bodies" with its STEP product
names. Sheet groups get their own FLAT-B<n>.png / FLAT-B<n>.json.
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
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_Label, TDF_LabelSequence
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import XCAFDoc_DocumentTool
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


def is_edge_face(clf, face, probe_mm):
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
        clf.Perform(q, 1e-4)
        inside += clf.State() == TopAbs_IN
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


def read_bodies(path):
    """Every solid in the file with its STEP product name, in assembly placement."""
    doc = TDocStd_Document(TCollection_ExtendedString("costing"))
    r = STEPCAFControl_Reader()
    r.SetNameMode(True)
    if r.ReadFile(path) != 1 or not r.Transfer(doc):
        sys.exit("cannot read STEP")
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

    def name(label):
        a = TDataStd_Name()
        return a.Get().ToExtString() if label.FindAttribute(TDataStd_Name.GetID_s(), a) else "unnamed"

    bodies = []

    def visit(label, loc):
        ref = label
        if st.IsReference_s(label):
            ref = TDF_Label()
            st.GetReferredShape_s(label, ref)
        if st.IsAssembly_s(ref):
            kids = TDF_LabelSequence()
            st.GetComponents_s(ref, kids)
            for j in range(1, kids.Length() + 1):
                visit(kids.Value(j), loc.Multiplied(st.GetLocation_s(label)))
        else:
            shape = st.GetShape_s(label).Moved(loc)
            ex = TopExp_Explorer(shape, TopAbs_SOLID)
            while ex.More():
                bodies.append((ex.Current(), name(ref)))
                ex.Next()

    roots = TDF_LabelSequence()
    st.GetFreeShapes(roots)
    for i in range(1, roots.Length() + 1):
        visit(roots.Value(i), TopLoc_Location())
    return bodies


def analyse(s, short_flat_mm, thickness_override=None):
    """Costing geometry of one shape. Returns (fields, unfold data for outline/png)."""
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
    if thickness_override:
        thickness = thickness_override

    # Split faces into edge faces and the two skins.
    clf = BRepClass3d_SolidClassifier(s)  # built once; per-point construction dominated run time
    edge_faces = {i for i in range(1, nf + 1) if is_edge_face(clf, face(i), thickness * 1.5)}
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
    if not skins:  # every face reads as an edge face: a solid part (bush, stud, block), not sheet
        return {
            "bbox_mm": [round(x1 - x0, 1), round(y1 - y0, 1), round(z1 - z0, 1)],
            "thickness_mm": thickness,
            "volume_mm3": round(vol),
            "mass_kg_steel": round(vol * STEEL_DENSITY, 3),
            "skins_found": 0,
            "warnings": ["no sheet skin found; solid part, not sheet metal"],
        }, None
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
            if longest and a / longest < short_flat_mm:
                short.append({"area_mm2": round(a), "approx_width_mm": round(a / longest, 1)})

    out = {
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
    if len(skins) != 2:
        out["warnings"].append("skin split is not two components; check edge-face classification")
    if any(b["adjacent_flats"] != 2 for b in bends):
        out["warnings"].append("some bend groups do not sit between exactly two flats; audit visually")
    if pieces != 1:
        out["warnings"].append(f"disconnected unfold: {pieces} pieces laid 50 mm apart; flat envelope spans them all")
    return out, (Q, T, ang, envelope, thickness)


def write_outline(path, source, unf):
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    Q, T, _, _, thickness = unf
    tris = [Polygon([Q[a], Q[b], Q[c]]) for a, b, c in T]
    u = unary_union([p.buffer(0.01) for p in tris if p.area > 1e-9]).buffer(-0.01)
    if u.geom_type != "Polygon":
        u = max(u.geoms, key=lambda g: g.area)
    u = u.simplify(0.2)
    x0, y0 = u.bounds[:2]
    ring = lambda r: [[round(x - x0, 3), round(y - y0, 3)] for x, y in r.coords]
    with open(path, "w") as fh:
        json.dump({"source": source, "thickness_mm": thickness, "area_mm2": round(u.area),
                   "exterior": ring(u.exterior), "interiors": [ring(r) for r in u.interiors]}, fh)


def write_png(path, unf):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    Q, T, ang, envelope, _ = unf
    t = np.radians(ang)
    R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
    fig, ax = plt.subplots(figsize=(8, 8))
    for a, b, c in T:
        tri = np.array([Q[a], Q[b], Q[c]]) @ R.T
        ax.fill(tri[:, 0], tri[:, 1], color=(0.5, 0.6, 0.85), lw=0)
    ax.set_aspect("equal")
    ax.grid(True)
    ax.set_title(f"Unfolded skin, envelope {envelope[0]} x {envelope[1]} mm")
    plt.savefig(path, dpi=80)
    plt.close(fig)


def suffixed(path, tag):
    stem, dot, ext = path.rpartition(".")
    return f"{stem}-{tag}.{ext}" if dot else f"{path}-{tag}"


def fingerprint(solid):
    """Identical bodies share volume, area and sorted box size."""
    box = Bnd_Box()
    BRepBndLib.Add_s(solid, box)
    x0, y0, z0, x1, y1, z1 = box.Get()
    dims = sorted(round((v1 - v0) * 2) / 2 for v0, v1 in ((x0, x1), (y0, y1), (z0, z1)))
    return (round(props(solid, "vol")), round(props(solid, "area")), *dims)


def is_sheet(g):
    """Sheet body: two skins whose area times thickness explains the volume."""
    vol = g["volume_mm3"]
    return g["skins_found"] == 2 and vol and abs(g["flat_area_mm2"] * g["thickness_mm"] - vol) / vol < 0.15


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step")
    ap.add_argument("--png", help="write flat-pattern preview image")
    ap.add_argument("--short-flat-mm", type=float, default=10.0,
                    help="flag flats narrower than this between bends")
    ap.add_argument("--outline", help="write unfolded flat polygon (exterior + holes) as JSON for nest.py")
    ap.add_argument("--thickness", type=float, help="override auto-detected thickness (mm)")
    args = ap.parse_args()

    bodies = read_bodies(args.step)
    if len(bodies) == 1:
        g, unf = analyse(bodies[0][0], args.short_flat_mm, args.thickness)
        json.dump({"source": args.step, "solids": 1, **g}, sys.stdout, indent=1)
        print()
        if args.outline and unf:
            write_outline(args.outline, args.step, unf)
        if args.png and unf:
            write_png(args.png, unf)
        return

    groups = {}
    for solid, name in bodies:
        groups.setdefault(fingerprint(solid), []).append((solid, name))
    rows, total_vol = [], 0.0
    for n, members in enumerate(sorted(groups.values(), key=lambda m: -props(m[0][0], "vol")), 1):
        tag = f"B{n}"
        names = sorted({nm for _, nm in members})
        row = {"body": tag, "qty": len(members), "product_names": names}
        try:
            g, unf = analyse(members[0][0], args.short_flat_mm, args.thickness)
        except Exception as e:  # odd bodies (threads, fillets) should not stop the job
            vol = props(members[0][0], "vol")
            g, unf = {"volume_mm3": round(vol), "mass_kg_steel": round(vol * STEEL_DENSITY, 3),
                      "warnings": [f"analysis failed: {e}"]}, None
        total_vol += g["volume_mm3"] * len(members)
        if unf and is_sheet(g):
            row["role"] = "sheet"
            if args.outline:
                row["outline"] = suffixed(args.outline, tag)
                write_outline(row["outline"], args.step, unf)
            if args.png:
                row["png"] = suffixed(args.png, tag)
                write_png(row["png"], unf)
            row.update(g)
        else:
            row["role"] = "non-sheet (probable hardware or weld; confirm)"
            row.update({k: g[k] for k in ("bbox_mm", "volume_mm3", "mass_kg_steel", "warnings") if k in g})
        rows.append(row)
    json.dump({"source": args.step, "solids": len(bodies), "body_groups": len(rows),
               "mass_kg_steel": round(total_vol * STEEL_DENSITY, 3), "bodies": rows}, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
