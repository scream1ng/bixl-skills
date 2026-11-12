#!/usr/bin/env python3
"""Small shaded isometric picture of a STEP part or assembly for the quote sheet.

Usage: python3 iso_view.py PART.step --out PART.jpg [--px 520] [--view iso|iso-rear]
       [--colours "#9aa0a6,#d0313d"]
Each solid gets the next colour in the list (default grey, red, dark grey, light grey).
Requires the CAD engine (cadquery-ocp), numpy and matplotlib from requirements.txt.
"""
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgb
from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRep import BRep_Tool
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID, TopAbs_FACE, TopAbs_REVERSED
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS

DEFAULT = '#9aa0a6,#d0313d,#6f757b,#b8bcc0'
_face = getattr(TopoDS, 'Face_s', None) or TopoDS.Face   # name differs across OCP versions


def load(fn):
    r = STEPControl_Reader()
    if r.ReadFile(fn) != IFSelect_RetDone:
        raise SystemExit(f'Could not read {fn}')
    r.TransferRoots()
    return r.OneShape()


def triangles(shape, deflection):
    BRepMesh_IncrementalMesh(shape, deflection, False, 0.3, True)
    solids, ex = [], TopExp_Explorer(shape, TopAbs_SOLID)
    while ex.More():
        solids.append(ex.Current()); ex.Next()
    if not solids:
        solids = [shape]
    out = []
    for si, s in enumerate(solids):
        fx = TopExp_Explorer(s, TopAbs_FACE)
        while fx.More():
            f = _face(fx.Current()); loc = TopLoc_Location()
            tri = BRep_Tool.Triangulation_s(f, loc)
            if tri is not None:
                tr = loc.Transformation()
                pts = []
                for i in range(1, tri.NbNodes() + 1):
                    p = tri.Node(i).Transformed(tr); pts.append((p.X(), p.Y(), p.Z()))
                pts = np.array(pts); rev = f.Orientation() == TopAbs_REVERSED
                for i in range(1, tri.NbTriangles() + 1):
                    a, b, c = tri.Triangle(i).Get()
                    t = (a - 1, c - 1, b - 1) if rev else (a - 1, b - 1, c - 1)
                    out.append((si, pts[list(t)]))
            fx.Next()
    return out


def render(fn, out, px=520, view='iso', colours=DEFAULT):
    shape = load(fn)
    cols = [np.array(to_rgb(c)) for c in colours.split(',')]
    allp = None
    tris = triangles(shape, 0.5)
    allp = np.concatenate([t for _, t in tris])
    size = float(np.ptp(allp, axis=0).max())
    tris = triangles(shape, max(size / 400, 0.2)) if size > 200 else tris
    az = np.radians(-45 if view == 'iso' else 135); el = np.radians(35.264)
    # camera looks from (cos az cos el, sin az cos el, sin el) toward the origin
    d = np.array([np.cos(az) * np.cos(el), np.sin(az) * np.cos(el), np.sin(el)])
    right = np.cross([0, 0, 1], d); right /= np.linalg.norm(right); up = np.cross(d, right)
    light = 0.55 * d + 0.45 * np.array([0.3, 0.2, 1.0]); light /= np.linalg.norm(light)
    limit = size / 60                       # split long triangles so depth sorting stays correct
    def split(t):
        e = [np.linalg.norm(t[1] - t[0]), np.linalg.norm(t[2] - t[1]), np.linalg.norm(t[0] - t[2])]
        if max(e) <= limit:
            return [t]
        i = int(np.argmax(e)); a, b, c = t[i], t[(i + 1) % 3], t[(i + 2) % 3]; m = (a + b) / 2
        return split(np.array([a, m, c])) + split(np.array([m, b, c]))
    tris = [(si, u) for si, t in tris for u in split(t)]
    polys, shade, depth = [], [], []
    for si, t in tris:
        n = np.cross(t[1] - t[0], t[2] - t[0]); ln = np.linalg.norm(n)
        if ln < 1e-12:
            continue
        n /= ln
        if n @ d < -1e-6:      # back face
            continue
        lam = 0.38 + 0.62 * max(0.0, float(n @ light))
        polys.append(np.c_[t @ right, t @ up]); shade.append(np.clip(cols[si % len(cols)] * lam, 0, 1))
        depth.append(float((t @ d).mean()))
    order = np.argsort(depth)
    fig = plt.figure(figsize=(px / 100, px * 0.75 / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
    pc = PolyCollection([polys[i] for i in order], facecolors=[shade[i] for i in order],
                        edgecolors=[shade[i] for i in order], linewidths=0.5, antialiased=True)
    ax.add_collection(pc)
    xy = np.concatenate(polys); lo, hi = xy.min(0), xy.max(0); pad = 0.04 * (hi - lo).max()
    span = hi - lo + 2 * pad; aspect = 0.75
    if span[1] / span[0] < aspect:
        c = (lo[1] + hi[1]) / 2; h = span[0] * aspect; ax.set_ylim(c - h / 2, c + h / 2); ax.set_xlim(lo[0] - pad, hi[0] + pad)
    else:
        c = (lo[0] + hi[0]) / 2; w = span[1] / aspect; ax.set_xlim(c - w / 2, c + w / 2); ax.set_ylim(lo[1] - pad, hi[1] + pad)
    ax.set_aspect('equal', adjustable='datalim')
    fig.patch.set_facecolor('#fafafa')
    fig.savefig(out, dpi=100, facecolor='#fafafa', pil_kwargs={'quality': 80} if out.lower().endswith(('.jpg', '.jpeg')) else {})
    plt.close(fig)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('step'); ap.add_argument('--out', required=True)
    ap.add_argument('--px', type=int, default=520); ap.add_argument('--view', default='iso', choices=('iso', 'iso-rear'))
    ap.add_argument('--colours', default=DEFAULT)
    a = ap.parse_args()
    render(a.step, a.out, a.px, a.view, a.colours)
    print(a.out)
