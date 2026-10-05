#!/usr/bin/env python3
"""Backbar jig plates for an LVD press brake, plus the folded part with gauge tabs for the bending software.
STEP (formed part + flat pattern, no tabs) -> DXF per plate + <part>_with_tab.step + preview.html."""
import argparse, html, json, math, os, sys
import ezdxf
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon,
                                BRepBuilderAPI_Sewing, BRepBuilderAPI_Transform)
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepGProp import BRepGProp
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffset
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.BRepTools import BRepTools, BRepTools_WireExplorer
from OCP.Bnd import Bnd_Box
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.GProp import GProp_GProps
from OCP.GeomAbs import GeomAbs_Arc, GeomAbs_Circle, GeomAbs_Cylinder, GeomAbs_Line, GeomAbs_Plane
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Reader, STEPControl_Writer
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_REVERSED, TopAbs_SOLID, TopAbs_VERTEX, TopAbs_WIRE
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape, TopTools_IndexedMapOfShape
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Ax3, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec

# Shop standard (measured from 818165 Backbar.STEP). Change here only if the standard changes.
PLATE_W, PLATE_T = 100.0, 6.0        # plate width along the bend; thickness (cut from 6 mm)
NOTCH_W, NOTCH_D = 50.2, 20.0        # slot over the 50 mm LVD backgauge finger
TIP_TO_FINGER = 50.0                 # deepest point of the blank -> finger tip (notch bottom)
CLEAR = 0.1                          # pocket offset around the blank
PROT_MAX, PROT_MIN = 20.0, 10.0      # how far the plate wraps forward past the blank tip
MIN_WALL = 10.0                      # plate material left each side of the pocket
# Gauge tab, added only to the STEP for the bending software (the real blank is cut without it).
TAB_W = 5.0                          # tab width along the bend
TAB_H_MAX = 10.0                     # tallest tab side the automatic placement will make
SNAP = 5.0                           # use an outline corner when one is this close to the widest position
CONTACT_MIN = 10.0                   # blank already touches the tip line over this width: no tab needed

# Comment pins for the preview: plain HTML/JS, appended to the page as is.
COMMENT_UI = """
<style>
#cbar{position:sticky;top:0;z-index:9;background:#fff;border:1px solid #ccc;border-radius:8px;padding:8px 10px;margin-bottom:10px;font-size:13px}
#cbar button{margin-right:6px}#cmode.on{background:#c0392b;color:#fff;border-color:#c0392b}#cnotes{font:12px ui-monospace,monospace;white-space:pre-wrap;margin:6px 0 0}
.fig{position:relative}body.commenting .fig svg{cursor:crosshair}
.pin{position:absolute;z-index:7}.pin b{position:absolute;left:-11px;top:-26px;display:flex;width:22px;height:22px;border-radius:50% 50% 50% 3px;background:#c0392b;color:#fff;font:600 12px system-ui;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 2px 7px #0006;transform:rotate(-45deg)}.pin b span{transform:rotate(45deg)}
.pin .box{position:absolute;left:16px;bottom:8px;width:210px;background:#fff;border-radius:9px;box-shadow:0 3px 14px #1234;padding:7px}.pin textarea{width:100%;box-sizing:border-box;height:58px;font:13px system-ui}.pin.shut .box{display:none}
</style>
<script>
(()=>{const NL=String.fromCharCode(10),r=v=>Math.round(v*100)/100,notes=[];let on=false;
const bar=document.createElement('div');bar.id='cbar';
bar.innerHTML='<button id="cmode">Comment mode</button><button id="ccopy">Copy all</button><span id="cmsg"></span><pre id="cnotes">none</pre>';
document.body.prepend(bar);
const $=s=>document.querySelector(s),say=m=>{$('#cmsg').textContent=m;},idle='Turn on Comment mode, then click a drawing to pin a note.';say(idle);
$('#cmode').onclick=()=>{on=!on;$('#cmode').classList.toggle('on',on);document.body.classList.toggle('commenting',on);say(on?'Click a drawing to pin a note. Click Comment mode again to stop.':idle);};
const list=()=>{notes.forEach((n,i)=>{n.el.querySelector('span').textContent=i+1;});$('#cnotes').textContent=notes.length?notes.map((n,i)=>(i+1)+'. '+(n.text||'(empty)')+'  @ '+n.where).join(NL):'none';};
const place=n=>{const p=new DOMPoint(n.x,n.y).matrixTransform(n.svg.getScreenCTM()),b=n.fig.getBoundingClientRect();n.el.style.left=(p.x-b.left)+'px';n.el.style.top=(p.y-b.top)+'px';};
addEventListener('resize',()=>notes.forEach(place));
for(const fig of document.querySelectorAll('.fig')){const svg=fig.querySelector('svg');svg.addEventListener('click',e=>{if(!on)return;
  const p=new DOMPoint(e.clientX,e.clientY).matrixTransform(svg.getScreenCTM().inverse()),d=fig.dataset,x=p.x,y=-p.y;
  let where=d.name+': ('+r(x)+', '+r(y)+') mm';
  if(d.xref){const lo=+d.xlo,hi=+d.xhi,along=x<lo?x-lo:x>hi?x-hi:0;where=d.name+': '+r(along)+' mm along the bend from the '+d.xref+', '+r(y)+' mm from the bend line';}
  const n={x:p.x,y:p.y,svg,fig,where,text:''},el=document.createElement('div');el.className='pin';n.el=el;
  el.innerHTML='<b><span></span></b><div class="box"><textarea placeholder="What should change here?"></textarea><button>Delete</button></div>';
  el.querySelector('b').onclick=()=>el.classList.toggle('shut');
  el.querySelector('button').onclick=()=>{notes.splice(notes.indexOf(n),1);el.remove();list();};
  const t=el.querySelector('textarea');t.oninput=()=>{n.text=t.value;list();};
  fig.append(el);notes.push(n);place(n);list();t.focus();});}
$('#ccopy').onclick=()=>{const text='Comments on '+document.title+':'+NL+$('#cnotes').textContent;
  const sel=()=>{const g=document.createRange();g.selectNodeContents($('#cnotes'));const s=getSelection();s.removeAllRanges();s.addRange(g);say('Clipboard blocked here: text selected, press Ctrl+C or Cmd+C.');};
  if(!navigator.clipboard)return sel();navigator.clipboard.writeText(text).then(()=>say('Copied. Paste it into the chat.'),sel);};
})();
</script>"""


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


def one_face(shape):
    """Merge coplanar touching faces into a single face (None when they do not merge)."""
    u = ShapeUpgrade_UnifySameDomain(shape, True, True, False)
    u.SetLinearTolerance(1e-3); u.SetAngularTolerance(1e-3); u.Build()
    fs = faces(u.Shape())
    return fs[0] if len(fs) == 1 else None


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
        bends.append(dict(face=ids[i], edges=es, p=tuple(x + o / 2 for x, o in zip(m1, off)), d=d, half=math.hypot(*off) / 2))
    return bends


def rect(x0, y0, x1, y1):
    p = BRepBuilderAPI_MakePolygon()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        p.Add(gp_Pnt(x, y, 0))
    p.Close()
    return BRepBuilderAPI_MakeFace(p.Wire()).Face()


def loop(wire, defl=0.02):
    """Wire as an ordered 2D point list (tab placement search and preview only)."""
    out, we = [], BRepTools_WireExplorer(wire)
    while we.More():
        e = we.Current(); c = BRepAdaptor_Curve(e); d = GCPnts_QuasiUniformDeflection(c, defl)
        seg = [(d.Value(k).X(), d.Value(k).Y()) for k in range(1, d.NbPoints() + 1)]
        out += seg[::-1] if e.Orientation() == TopAbs_REVERSED else seg
        we.Next()
    return out


def outline(face, defl=0.02):
    return loop(BRepTools.OuterWire_s(face), defl)


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


def write_step(shape, path):
    """Write one solid as STEP and read it back; True when it comes back as one solid of the same volume."""
    sys.stdout.flush(); keep = os.dup(1); null = os.open(os.devnull, os.O_WRONLY); os.dup2(null, 1)   # OCC prints progress on stdout
    try:
        w = STEPControl_Writer(); w.Transfer(shape, STEPControl_AsIs); w.Write(path)
        r = STEPControl_Reader(); ok = r.ReadFile(path) == 1 and r.TransferRoots() > 0
        back = sub(r.OneShape(), TopAbs_SOLID, TopoDS.Solid_s) if ok else []
    finally:
        os.dup2(keep, 1); os.close(keep); os.close(null)
    return len(back) == 1 and abs(volume(back[0]) - volume(shape)) < 0.05


def choose_end(blank, bends, i, side):
    """Frame for bend i: X along the bend, Y from the bend line toward the gauged end. None when the user must choose."""
    b, opts = bends[i], []
    for s in ((1, -1) if side is None else (side,)):
        d = tuple(s * x for x in b["d"])
        T = gp_Trsf(); T.SetTransformation(gp_Ax3(gp_Pnt(*b["p"]), gp_Dir(*b["n"]), gp_Dir(*d)))
        loc = TopoDS.Face_s(moved(blank, T))
        between = [j + 1 for j, o in enumerate(bends) if j != i and any(y > b["half"] + 0.01 for _, y, _ in pts(moved(o["face"], T)))]
        opts.append(dict(s=s, T=T, loc=loc, tip=bbox(loc)[4], between=between))
    b["T"] = opts[0]["T"]
    free = [o for o in opts if not o["between"]]
    if side is None:
        return min(free, key=lambda o: o["tip"]) if free else None   # nearer free end
    return opts[0]                                                   # the end the user chose


def build_plate(o, prot_max, die_clear, warn):
    """Backbar plate for the chosen end, in the bend frame. The pocket is the plain blank outline (no tab)."""
    tip, loc = o["tip"], o["loc"]
    prot = min(prot_max, tip - die_clear)
    if prot < PROT_MIN:
        warn.append(f"blank reaches only {tip:.1f} mm behind the bend line: wrap is {prot:.1f} mm, under {PROT_MIN:.0f}")
    if prot <= 1:
        return dict(plate_error=f"blank reaches only {tip:.1f} mm behind the bend line; no room for a pocket")
    front = tip - prot
    x0, _, _, x1, _, _ = bbox(BRepAlgoAPI_Common(loc, rect(-1e4, front, 1e4, tip + 1)).Shape())
    cx = (x0 + x1) / 2
    wall = PLATE_W / 2 - (x1 - x0) / 2 - CLEAR
    if wall < MIN_WALL:
        return dict(plate_error=f"blank is {x1 - x0:.1f} mm wide at the pocket: does not fit the {PLATE_W:.0f} mm standard plate "
                                f"with {MIN_WALL:.0f} mm of material each side")
    body = BRepAlgoAPI_Cut(rect(cx - PLATE_W / 2, front, cx + PLATE_W / 2, tip + TIP_TO_FINGER + NOTCH_D),
                           rect(cx - NOTCH_W / 2, tip + TIP_TO_FINGER, cx + NOTCH_W / 2, tip + TIP_TO_FINGER + NOTCH_D + 1)).Shape()
    solid_blank = BRepBuilderAPI_MakeFace(BRepTools.OuterWire_s(loc)).Face()     # holes ignored
    off = BRepOffsetAPI_MakeOffset(solid_blank, GeomAbs_Arc); off.Perform(CLEAR)
    if not off.IsDone():
        return dict(plate_error="could not offset the blank outline by the pocket clearance")
    if off.Shape().ShapeType() != TopAbs_WIRE:
        return dict(plate_error="pocket offset did not give one closed outline; check the flat pattern outline")
    pocket = BRepBuilderAPI_MakeFace(TopoDS.Wire_s(off.Shape())).Face()
    if area(pocket) < area(solid_blank):
        return dict(plate_error="pocket offset went inward; check the flat pattern outline")
    pieces = sorted(faces(BRepAlgoAPI_Cut(body, pocket).Shape()), key=area, reverse=True)
    if len(pieces) > 1 and area(pieces[1]) > 1:
        warn.append("the pocket cuts the plate into separate pieces; largest kept")
    plate = pieces[0]
    gap = BRepExtrema_DistShapeShape(plate, solid_blank); gap.Perform()
    return dict(plate=plate, cx=cx, x0=x0, x1=x1, front=front, wrap_mm=round(prot, 2), front_edge_to_bend_mm=round(front, 2),
                bend_to_finger_tip_mm=round(tip + TIP_TO_FINGER, 2), wall_each_side_mm=round(wall, 2),
                clearance_mm=round(gap.Value(), 3), plate_area_mm2=round(area(plate), 1))


def top_at(poly, x):
    """Highest outline point on the vertical line at x (None when the line misses the blank)."""
    ys = [y0 + (y1 - y0) * (x - x0) / (x1 - x0)
          for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]) if x0 != x1 and (x0 - x) * (x1 - x) <= 0]
    return max(ys) if ys else None


def contacts(wire, tip):
    """X of every point where the outline touches the tip line y = tip (exact for lines and arcs)."""
    xs = [x for x, y, _ in pts(wire) if y > tip - 1e-6]
    for e in edges(wire):
        if bbox(e)[4] < tip - 1e-6:
            continue
        c = BRepAdaptor_Curve(e); a, b = c.FirstParameter(), c.LastParameter()
        k = max(range(201), key=lambda k: c.Value(a + (b - a) * k / 200).Y())
        lo, hi = a + (b - a) * max(k - 1, 0) / 200, a + (b - a) * min(k + 1, 200) / 200
        for _ in range(60):                           # ternary search for the highest point of the edge
            m1, m2 = lo + (hi - lo) / 3, hi - (hi - lo) / 3
            lo, hi = (m1, hi) if c.Value(m1).Y() < c.Value(m2).Y() else (lo, m2)
        p = c.Value((lo + hi) / 2)
        if p.Y() > tip - 1e-6:
            xs.append(p.X())
    return xs


def g_to(T_to, T_from):
    """Transform from one bend frame to another."""
    g = gp_Trsf(); g.Multiply(T_to); g.Multiply(T_from.Inverted())
    return g


def cut_tab(loc, tip, floor, x_out, x_in):
    """The part of a tab-wide column that lies between the blank outline and the tip line, or None."""
    col = rect(min(x_out, x_in), 0, max(x_out, x_in), tip)
    top = [f for f in faces(BRepAlgoAPI_Cut(col, loc).Shape()) if bbox(f)[4] > tip - 1e-6]
    if len(top) != 1:
        return None
    b = bbox(top[0])
    return top[0] if b[3] - b[0] > abs(x_out - x_in) - 1e-6 and b[1] > floor else None


def build_tab(o, floor, tabbed, at, width, earlier):
    """Gauge tab for the chosen end: its end edge on the tip line, so tab and blank tip gauge on one line parallel to the bend."""
    tip = o["tip"]
    loc = TopoDS.Face_s(moved(tabbed, o["T"]))        # blank with the tabs already added for earlier bends
    wire = BRepTools.OuterWire_s(loc)
    poly = loop(wire, 0.01)
    touch = contacts(wire, tip)                       # where the blank touches the tip line
    tlo, thi = min(touch), max(touch)
    if thi - tlo >= CONTACT_MIN:
        used = [q["bend"] for q in earlier if bbox(moved(q["tab"]["piece"], g_to(o["T"], q["T"])))[4] > tip - 1e-6]
        why = f"uses the tab added for bend {used[0]}" if used else "blank already touches a line parallel to the bend"
        return dict(skipped=f"{why} (contact {thi - tlo:.1f} mm wide); no tab needed")
    if at is not None:
        if abs(at) < width:
            return dict(error=f"--at must be at least the tab width ({width:g} mm) away from the tip")
        sgn, t0, dist, how = (1 if at > 0 else -1), (thi if at > 0 else tlo), abs(at), "forced"
    else:
        cand = []
        for sgn, t0 in ((-1, tlo), (1, thi)):
            dist, last = width + 0.5, None
            y = top_at(poly, t0 + sgn * dist)
            if y is None:
                continue                              # blank ends here: no room on this side
            while y is not None and tip - y <= TAB_H_MAX:
                last = dist; dist += 0.25; y = top_at(poly, t0 + sgn * dist)
            cand.append((last if last is not None else width + 0.5, sgn, t0))
        if not cand:
            return dict(error="no room beside the blank tip for a tab")
        dist, sgn, t0 = max(cand)
        how = "widest"
        corners = [sgn * (x - t0) for x, y, _ in pts(wire) if tip - y <= TAB_H_MAX and width + 0.5 <= sgn * (x - t0) <= dist + 0.25]
        if corners and dist - max(corners) <= SNAP:
            dist, how = max(corners), "corner"
    piece = None
    for _ in range(12):                               # step toward the tip until the column gives one clean tab
        x_out = t0 + sgn * dist; x_in = x_out - sgn * width
        piece = cut_tab(loc, tip, floor, x_out, x_in)
        if piece is not None or at is not None or dist - 0.5 < width + 0.5:
            break
        dist -= 0.5; how = "widest"
    if piece is None:
        return dict(error="a tab at that position does not sit on the flange edge; move it with --at")
    side_h = lambda x: tip - min(y for px, y, _ in pts(piece) if abs(px - x) < 1e-6)
    h_out, h_in = side_h(x_out), side_h(x_in)
    res = dict(piece=piece, x_out=x_out, x_in=x_in, t0=t0, tlo=tlo, thi=thi, placed=how, width_mm=round(width, 2),
               heights_mm=[round(h_in, 2), round(h_out, 2)], tip_to_tab_mm=round(sgn * (x_in - t0), 2), tip_to_tab_outer_mm=round(sgn * dist, 2))
    if max(h_out, h_in) > TAB_H_MAX + 0.01:
        res["warning"] = f"tab is {max(h_out, h_in):.1f} mm tall for {width:g} mm wide"
    return res


def outward(face):
    d = plane_of(face)
    return tuple(-x for x in d) if face.Orientation() == TopAbs_REVERSED else d


def centroid(s):
    g = GProp_GProps(); BRepGProp.SurfaceProperties_s(s, g); c = g.CentreOfMass()
    return (c.X(), c.Y(), c.Z())


def carry(F, bends, solid):
    """Rigid moves that put flat-pattern flange face F onto its twin on the folded part.
    Anchored on the bend edge (straight edge next to a bend), then checked by area and centroid."""
    eF = [e for e in edges(F) if any(e.IsSame(x) for b in bends for x in b["edges"])]
    if not eF:
        return []
    (p0, p1), A, cF, nF = pts(eF[0]), area(F), centroid(F), outward(F)
    L = math.dist(p0, p1)
    emap = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(solid, TopAbs_EDGE, TopAbs_FACE, emap)
    ax = lambda o, z, a, b: gp_Ax3(gp_Pnt(*o), gp_Dir(*z), gp_Dir(*vsub(b, a)))
    out = []
    for k in range(1, emap.Extent() + 1):
        e = TopoDS.Edge_s(emap.FindKey(k)); fs = [TopoDS.Face_s(f) for f in emap.FindFromIndex(k)]
        if len(fs) != 2 or BRepAdaptor_Curve(e).GetType() != GeomAbs_Line:
            continue
        cyl = [BRepAdaptor_Surface(f).GetType() == GeomAbs_Cylinder for f in fs]
        if cyl.count(True) != 1:
            continue
        G = fs[cyl.index(False)]
        if plane_of(G) is None or abs(area(G) - A) > max(0.05, 0.002 * A):
            continue
        qa, qb = pts(e)
        if abs(math.dist(qa, qb) - L) > 0.01:
            continue
        for a, b in ((qa, qb), (qb, qa)):
            M = gp_Trsf(); M.SetDisplacement(ax(p0, nF, p0, p1), ax(a, outward(G), a, b))
            c = gp_Pnt(*cF).Transformed(M)
            if math.dist((c.X(), c.Y(), c.Z()), centroid(G)) < 0.02:
                out.append(M)
    return out


def tab_step(formed, top, bends, n, t, rows):
    """Folded part with every tab carried onto its flange: (solid, tab solids) or (None, reason)."""
    out, exp, prisms = formed, 0.0, []
    for p in rows:
        if "piece" not in p.get("tab", {}):
            continue
        pc = moved(p["tab"]["piece"], p["T"].Inverted())             # tab on the flat pattern's top face
        near = lambda f: (lambda d: (d.Perform(), d.Value())[1])(BRepExtrema_DistShapeShape(f, pc)) < 1e-6
        touch = [f for f in top if not any(f.IsSame(b["face"]) for b in bends) and near(f)]
        if len(touch) != 1:
            return None, f"the tab for bend {p['bend']} does not sit on exactly one flange"
        moves = carry(touch[0], bends, formed)
        if len(moves) != 1:
            return None, (f"no flange on the folded part matches the flat-pattern flange that carries the tab for bend {p['bend']}" if not moves
                          else f"more than one flange on the folded part matches the one that carries the tab for bend {p['bend']} (symmetric part)")
        prism = moved(BRepPrimAPI_MakePrism(pc, gp_Vec(*[-t * x for x in n])).Shape(), moves[0])
        out = BRepAlgoAPI_Fuse(out, prism).Shape(); exp += area(pc) * t; prisms.append(prism)
    if not prisms:
        return None, "no tab was added"
    u = ShapeUpgrade_UnifySameDomain(out, True, True, False); u.Build(); out = u.Shape()
    if len(sub(out, TopAbs_SOLID, TopoDS.Solid_s)) != 1 or not BRepCheck_Analyzer(out).IsValid() or abs(volume(out) - volume(formed) - exp) > 0.01 * exp + 0.05:
        return None, "the folded part with tabs did not come out as one valid solid"
    return out, prisms


def iso_svg(shape, prisms, T):
    """Isometric wireframe of the folded part (tabs highlighted), in the frame T. Picture only."""
    allq = []
    def lines(s, cls):
        m = TopTools_IndexedMapOfShape(); TopExp.MapShapes_s(moved(s, T), TopAbs_EDGE, m)
        out = []
        for k in range(1, m.Extent() + 1):
            c = BRepAdaptor_Curve(TopoDS.Edge_s(m.FindKey(k))); d = GCPnts_QuasiUniformDeflection(c, 0.05)
            q = [((d.Value(j).X() - d.Value(j).Y()) * 0.7071, -(d.Value(j).X() + d.Value(j).Y()) * 0.4082 - d.Value(j).Z() * 0.8165)
                 for j in range(1, d.NbPoints() + 1)]
            allq.extend(q)
            out.append(f'<polyline class="{cls}" points="' + " ".join(f"{u:.2f},{v:.2f}" for u, v in q) + '"/>')
        return "".join(out)
    body = lines(shape, "wire") + "".join(lines(p, "wtab") for p in prisms)
    xs, ys = [u for u, _ in allq], [v for _, v in allq]
    vb = f"{min(xs) - 8:.0f} {min(ys) - 8:.0f} {max(xs) - min(xs) + 16:.0f} {max(ys) - min(ys) + 16:.0f}"
    return f'<div class="fig" data-name="folded part with tab (picture)"><svg class="det" viewBox="{vb}">{body}</svg></div>'


def poly_svg(pp, cls):
    return f'<polygon class="{cls}" points="' + " ".join(f"{x:.2f},{-y:.2f}" for x, y in pp) + '"/>'


def line_svg(cls, x0, y0, x1, y1):
    return f'<line class="{cls}" x1="{x0:.2f}" y1="{-y0:.2f}" x2="{x1:.2f}" y2="{-y1:.2f}"/>'


def dim(x0, y0, x1, y1, label, side):
    mx, my = (x0 + x1) / 2, -(y0 + y1) / 2
    tx, ty, anchor = {"l": (mx - 1.5, my + 1.2, "end"), "r": (mx + 1.5, my + 1.2, "start"), "t": (mx, my - 1.2, "middle")}[side]
    return line_svg("dim", x0, y0, x1, y1) + f'<text class="dt" x="{tx:.2f}" y="{ty:.2f}" text-anchor="{anchor}">{label}</text>'


def num(v):
    return f"{round(v, 2):g}"


def plate_detail(p):
    """Dimensioned drawing of one plate in its bend frame (bend line horizontal at the bottom, backgauge up)."""
    cx, front, tip = p["cx"], p["front"], p["tip"]
    finger, back, L, R = tip + TIP_TO_FINGER, tip + TIP_TO_FINGER + NOTCH_D, cx - PLATE_W / 2, cx + PLATE_W / 2
    out = [poly_svg(outline(rect(cx - 25, finger, cx + 25, back + 24)), "finger"), poly_svg(outline(p["plate"]), "plate"),
           poly_svg(outline(p["loc"]), "blank"), line_svg("bend", L - 40, 0, R + 24, 0),
           line_svg("ref", L, tip, R, tip), line_svg("ref", L, finger, R, finger)]
    xr, xl, xl2 = R + 10, L - 10, L - 24
    for y in (0, front, tip, finger, back):                                   # right chain, bend line upward
        out.append(line_svg("ext", R + 1, y, xr + 2, y))
    for y0, y1 in ((0, front), (front, tip), (tip, finger), (finger, back)):
        out.append(dim(xr, y0, xr, y1, num(y1 - y0), "r"))
    out += [line_svg("ext", L - 1, front, xl - 2, front), line_svg("ext", L - 1, back, xl - 2, back), dim(xl, front, xl, back, num(back - front), "l"),
            line_svg("ext", L - 1, finger, xl2 - 2, finger), dim(xl2, 0, xl2, finger, num(finger), "l")]
    for x, y in ((cx - NOTCH_W / 2, back + 8), (cx + NOTCH_W / 2, back + 8), (L, back + 18), (R, back + 18)):
        out.append(line_svg("ext", x, back + 1, x, y + 2))
    out += [dim(cx - NOTCH_W / 2, back + 8, cx + NOTCH_W / 2, back + 8, num(NOTCH_W), "t"), dim(L, back + 18, R, back + 18, num(PLATE_W), "t")]
    for a, b in ((L, p["x0"] - CLEAR), (p["x1"] + CLEAR, R)):                  # plate left each side of the pocket
        if b - a > 5:
            out += [line_svg("ext", a, front - 1, a, front - 8), line_svg("ext", b, front - 1, b, front - 8), dim(a, front - 6, b, front - 6, num(b - a), "t")]
    vb = f"{L - 46:.0f} {-(back + 26):.0f} {PLATE_W + 78:.0f} {back + 38:.0f}"
    same = f' = plate B{p["same_plate_as"]}, same plate at a different gauge distance' if "same_plate_as" in p else ""
    return (f'<h4>Plate B{p["bend"]}{same}: dimensions in mm (plate {PLATE_T:g} thick, pocket = part outline + {CLEAR:g})</h4>'
            f'<div class="fig" data-name="plate B{p["bend"]}" data-xref="plate centre" data-xlo="{cx:.3f}" data-xhi="{cx:.3f}">'
            f'<svg class="det" viewBox="{vb}">{"".join(out)}</svg></div>')


def tab_detail(p, tabbed):
    """Dimensioned drawing of one tab in its bend frame. The tab exists only in the STEP for the bending software."""
    tb, tip = p["tab"], p["tip"]
    xo, xi, t0 = tb["x_out"], tb["x_in"], tb["t0"]
    s = 1 if xo > xi else -1
    f = TopoDS.Face_s(moved(tabbed, p["T"])); ow = BRepTools.OuterWire_s(f)
    pp = loop(ow)
    xs = [x for x, y in pp if y > -5]
    L, R = min(xs), max(xs)
    far = R + 10 if s < 0 else L - 10                 # bend line -> tab edge, on the side away from the tab
    h_out = tb["heights_mm"][1]
    out = [poly_svg(pp, "blank")] + [poly_svg(loop(w), "hole") for w in sub(f, TopAbs_WIRE, TopoDS.Wire_s) if not w.IsSame(ow)]
    out += [poly_svg(outline(tb["piece"]), "tab"), line_svg("bend", L - 26, 0, R + 26, 0), line_svg("ref", L - 14, tip, R + 14, tip),
            line_svg("ext", xo, tip + 1, xo, tip + 8), line_svg("ext", xi, tip + 1, xi, tip + 14), line_svg("ext", t0, tip + 1, t0, tip + 14),
            dim(xi, tip + 6, xo, tip + 6, num(abs(xo - xi)), "t"), dim(t0, tip + 12, xi, tip + 12, num(abs(xi - t0)), "t"),
            line_svg("ext", xo + s, tip - h_out, xo + s * 7, tip - h_out),
            dim(xo + s * 5, tip - h_out, xo + s * 5, tip, num(h_out), "r" if s > 0 else "l"),
            dim(far, 0, far, tip, num(tip), "r" if s < 0 else "l")]
    vb = f"{L - 30:.0f} {-(tip + 20):.0f} {R - L + 60:.0f} {tip + 28:.0f}"
    return (f'<h4>Bend {p["bend"]}: gauge tab in the STEP, dimensions in mm (tab edge and blank tip on one line, parallel to the bend)</h4>'
            f'<div class="fig" data-name="bend {p["bend"]} tab" data-xref="blank tip" data-xlo="{tb["tlo"]:.3f}" data-xhi="{tb["thi"]:.3f}">'
            f'<svg class="tabfig" viewBox="{vb}">{"".join(out)}</svg></div>')


def preview(path, title, blank, tabbed, bends, rows, thickness, notes, iso, step):
    T0 = bends[0]["T"]
    allp, svg = [], []
    def poly(shape, T, cls):
        pp = outline(TopoDS.Face_s(moved(shape, g_to(T0, T))))
        allp.extend(pp)
        return poly_svg(pp, cls)
    for p in rows:
        if "plate" in p and "same_plate_as" not in p:
            y = p["tip"] + TIP_TO_FINGER
            svg.append(poly(rect(p["cx"] - 25, y, p["cx"] + 25, y + 60), p["T"], "finger"))
            svg.append(poly(p["plate"], p["T"], "plate"))
            c = gp_Pnt(p["cx"], p["tip"] + 30, 0).Transformed(g_to(T0, p["T"]))
            names = "+".join(f"B{q['bend']}" for q in rows if q is p or q.get("same_plate_as") == p["bend"])
            svg.append(f'<text class="id" x="{c.X():.1f}" y="{-c.Y():.1f}">{names}</text>')
    svg.append(poly(moved(blank, T0), T0, "blank"))
    svg += [poly(p["tab"]["piece"], p["T"], "ghost") for p in rows if "piece" in p.get("tab", {})]
    for k, b in enumerate(bends):
        a = [gp_Pnt(*[b["p"][m] + s * 60 * b["d"][m] for m in range(3)]).Transformed(T0) for s in (-1, 1)]
        svg.append(line_svg("bend", a[0].X(), a[0].Y(), a[1].X(), a[1].Y()))
        c = gp_Pnt(*b["p"]).Transformed(T0)
        svg.append(f'<text x="{c.X():.1f}" y="{-c.Y() - 1.5:.1f}">bend {k + 1}</text>')
    xs, ys = [x for x, _ in allp], [-y for _, y in allp]
    vb = f"{min(xs) - 10:.0f} {min(ys) - 10:.0f} {max(xs) - min(xs) + 20:.0f} {max(ys) - min(ys) + 20:.0f}"
    def tab_text(tb):
        if "piece" in tb:
            return f"{tb['width_mm']:g} wide, {tb['tip_to_tab_mm']:g} from the tip ({tb['placed']})"
        return tb.get("skipped") or tb.get("error", "")
    cols = ["bend", "dxf", "wrap_mm", "front_edge_to_bend_mm", "program_gauge_mm", "bend_to_finger_tip_mm", "clearance_mm"]
    heads = ["bend", "plate dxf", "wrap", "front edge to bend", "CADMAN gauge: bend to tab edge", "finger tip with jig", "clearance"]
    note = lambda p: "; ".join(p.get("warnings", []) + [x for x in (p.get("error"), p.get("plate_error")) if x])
    body = "".join("<tr>" + "".join(f"<td>{p.get(c, '')}</td>" for c in cols) + f"<td>{tab_text(p.get('tab', {}))}</td><td>{note(p)}</td></tr>" for p in rows)
    step_html = (f"<h4>Folded part with gauge tab: {step} (for CADMAN-B)</h4>{iso}<p>Black = folded part, orange = tab. The real blank is cut without the tab; "
                 f"with the jig fitted the finger tip sits {TIP_TO_FINGER:g} mm behind the programmed gauge line.</p>") if step else ""
    page = f"""<!doctype html><meta charset="utf-8"><title>{title} backbar</title>
<style>body{{font:14px system-ui;margin:16px;background:#fff;color:#111}}svg{{width:100%;max-height:70vh;border:1px solid #ccc}}
.plate{{fill:#8f93c8;fill-opacity:.55;stroke:#2b2f77;stroke-width:.4}}.blank{{fill:#c9a27a;fill-opacity:.6;stroke:#6b4a2a;stroke-width:.4}}.hole{{fill:#fff;stroke:#6b4a2a;stroke-width:.35}}
.tab{{fill:#e4572e;fill-opacity:.75;stroke:#8a2a10;stroke-width:.3}}.ghost{{fill:#e4572e;fill-opacity:.35;stroke:#8a2a10;stroke-width:.3;stroke-dasharray:1.2 .8}}
.wire{{fill:none;stroke:#222;stroke-width:.25}}.wtab{{fill:none;stroke:#e4572e;stroke-width:.6}}
.finger{{fill:#999;fill-opacity:.35;stroke:#555;stroke-width:.3;stroke-dasharray:2 1}}.bend{{stroke:#d00;stroke-width:.4;stroke-dasharray:4 2}}
text{{font-size:4px;fill:#d00}}text.id{{font-size:9px;fill:#2b2f77;text-anchor:middle}}text.dt{{font-size:3.6px;fill:#111}}svg.tabfig text.dt{{font-size:2.8px}}
svg.det,svg.tabfig{{max-width:680px;display:block}}.dim{{stroke:#111;stroke-width:.25;marker-start:url(#a);marker-end:url(#a)}}svg.tabfig .dim{{marker-start:url(#b);marker-end:url(#b)}}.ext{{stroke:#111;stroke-width:.15}}.ref{{stroke:#111;stroke-width:.2;stroke-dasharray:1.5 1}}table{{border-collapse:collapse;margin-top:12px}}td,th{{border:1px solid #ccc;padding:4px 8px;text-align:left}}</style>
<h3>{title}: backbar plates ({PLATE_W:.0f} wide &times; {PLATE_T:.0f} mm, blank {thickness:.2f} mm)</h3>
<div class="fig" data-name="overview (bend 1 frame)"><svg viewBox="{vb}"><defs><marker id="a" viewBox="0 0 6 6" refX="6" refY="3" markerWidth="2.4" markerHeight="2.4" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0,0L6,3L0,6z"/></marker><marker id="b" viewBox="0 0 6 6" refX="6" refY="3" markerWidth="1.6" markerHeight="1.6" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0,0L6,3L0,6z"/></marker></defs>{''.join(svg)}</svg></div>
<p>Brown = flat blank, purple = backbar plate, grey dashed = backgauge finger, red = bend line, orange dashed = gauge tab (in the STEP only), black dashed = part tip and finger tip. Pictures are for checking only; cut from the DXF.</p>
{step_html}
{''.join(plate_detail(p) for p in rows if "plate" in p)}
{''.join(tab_detail(p, tabbed) for p in rows if "piece" in p.get("tab", {}))}
<table><tr>{''.join(f'<th>{h}</th>' for h in heads)}<th>tab in STEP</th><th>notes</th></tr>{body}</table>{''.join(f'<p><b>Note:</b> {x}</p>' for x in notes)}""" + COMMENT_UI
    open(path, "w").write(page)
    return len(page)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step"); ap.add_argument("out")
    ap.add_argument("--wrap", type=float, default=PROT_MAX, help="mm the plate wraps past the blank tip (10-20)")
    ap.add_argument("--die-clear", type=float, default=8.0, help="min mm from bend line to plate front edge")
    ap.add_argument("--side", action="append", default=[], help="N=+ or N=- : force the gauged side of bend N")
    ap.add_argument("--at", action="append", default=[], help="N=X : outer side of the tab on bend N, X mm from the blank tip (signed)")
    ap.add_argument("--tab-width", type=float, default=TAB_W, help="tab width in mm")
    ap.add_argument("--flat", type=int, help="solid number of the flat pattern when it cannot be told apart")
    a = ap.parse_args()
    if not PROT_MIN <= a.wrap <= PROT_MAX:
        die(f"--wrap must be {PROT_MIN:.0f} to {PROT_MAX:.0f} mm.")
    if not 2 <= a.tab_width <= 20:
        die("--tab-width must be 2 to 20 mm.")
    sides, at = {}, {}
    for s in a.side:
        k, _, v = s.partition("=")
        if not k.isdigit() or int(k) < 1 or v not in ("+", "-"):
            die("--side must look like 1=+ or 2=-.")
        sides[int(k) - 1] = 1 if v == "+" else -1
    for s in a.at:
        k, _, v = s.partition("=")
        try:
            x = float(v)
        except ValueError:
            x = math.nan
        if not k.isdigit() or int(k) < 1 or not math.isfinite(x):
            die("--at must look like 1=-12.5 or 2=9.")
        at[int(k) - 1] = x
    r = STEPControl_Reader()
    if r.ReadFile(a.step) != 1:
        die("cannot read the STEP file.")
    r.TransferRoots()
    solids = sub(r.OneShape(), TopAbs_SOLID, TopoDS.Solid_s)
    info = {i: flat_info(s) for i, s in enumerate(solids)}
    flats = [i for i in info if info[i]]
    formed = [s for i, s in enumerate(solids) if not info[i]]
    if a.flat is not None:
        flats = [a.flat - 1] if info.get(a.flat - 1) else []
    elif len(flats) > 1:   # keep the flat body whose volume matches a formed body
        flats = [i for i in flats if any(abs(volume(solids[i]) - volume(f)) < 0.1 * volume(f) for f in formed)]
    if len(flats) != 1:
        die(f"need exactly one flat pattern body; found {len(flats)} among {len(solids)} solids. "
            "Export the formed part and its flat pattern together, or pass --flat N.")
    flat = solids[flats[0]]; n, top, t = info[flats[0]]
    formed = min(formed, key=lambda f: abs(volume(f) - volume(flat))) if formed else None
    notes = []
    if formed is not None and volume(flat) > 1.01 * volume(formed):
        notes.append("flat pattern has more material than the formed part: gauge tabs are probably already on the blank, "
                     "so the pockets include them. Re-export the flat pattern without tabs for a clean pocket.")
    bends = find_bends(flat, top)
    if not bends:
        die("the flat pattern has no bend zones (one merged face). In SolidWorks untick 'Merge faces' on the Flat-Pattern feature and re-export.")
    for opt, given in (("--side", sides), ("--at", at)):
        if any(i >= len(bends) for i in given):
            die(f"{opt} names a bend this part does not have; it has {len(bends)}.")
    for b in bends:
        b["n"] = n
    sew = BRepBuilderAPI_Sewing()
    for f in top:
        sew.Add(f)
    sew.Perform()
    blank = one_face(sew.SewedShape())
    if blank is None:
        die("could not merge the flat pattern faces into one outline.")
    os.makedirs(a.out, exist_ok=True)
    title = os.path.splitext(os.path.basename(a.step))[0]
    rows, tabbed, done = [], blank, []
    for i in range(len(bends)):
        o = choose_end(blank, bends, i, sides.get(i))
        if o is None:
            rows.append(dict(bend=i + 1, error="other bends lie on both sides of this bend; choose the gauged end with --side and bend this one before the bends in between"))
            continue
        p = dict(bend=i + 1, side="+" if o["s"] > 0 else "-", T=o["T"], loc=o["loc"], tip=o["tip"], program_gauge_mm=round(o["tip"], 2), warnings=[])
        if o["between"]:
            p["warnings"].append("gauged from the end beyond bend " + ", ".join(map(str, o["between"])) + ": bend this one first, while that end is still flat")
        p.update(build_plate(o, a.wrap, a.die_clear, p["warnings"]))
        for q in done:                                # same plate as an earlier bend (parallel bends gauged from one end)?
            if "plate" in p and abs(area(p["plate"]) - area(q["plate"])) < 0.01 and all(
                    abs(u - v) < 1e-3 for u, v in zip(bbox(moved(p["plate"], g_to(q["T"], p["T"]))), bbox(q["plate"]))):
                p["same_plate_as"], p["dxf"] = q["bend"], q["dxf"]
                break
        else:
            if "plate" in p:
                p["dxf"] = f"{title}_backbar_B{p['bend']}.dxf"
                write_dxf(p["plate"], os.path.join(a.out, p["dxf"]))
                done.append(p)
        p["tab"] = build_tab(o, bends[i]["half"] + 0.01, tabbed, at.get(i), a.tab_width, [q for q in rows if "piece" in q.get("tab", {})])
        if "warning" in p["tab"]:
            p["warnings"].append(p["tab"].pop("warning"))
        if "piece" in p["tab"]:
            tabbed = one_face(BRepAlgoAPI_Fuse(tabbed, moved(p["tab"]["piece"], o["T"].Inverted())).Shape())
            if tabbed is None:
                die(f"the tab for bend {p['bend']} did not join the blank into one outline.")
        rows.append(p)
    for p in rows:                                    # the tab edge must sit on the tip line: the blank must not get any longer
        if "piece" in p.get("tab", {}):
            p["tab"]["edge_off_tip_line_mm"] = round(abs(bbox(moved(tabbed, p["T"]))[4] - p["tip"]), 3)
    step, iso = None, ""
    if formed is None:
        notes.append("no folded part in the file, so no STEP with tab was written.")
    else:
        solid, extra = tab_step(formed, top, bends, n, t, rows)
        if solid is None:
            notes.append(f"STEP with tab not written: {extra}.")
        else:
            step = f"{title}_with_tab.step"
            if not write_step(solid, os.path.join(a.out, step)):
                os.remove(os.path.join(a.out, step)); step = None
                notes.append("STEP with tab not written: it did not read back as one solid of the same volume.")
            else:
                iso = iso_svg(solid, extra, bends[0]["T"])
    size = preview(os.path.join(a.out, "preview.html"), html.escape(title), blank, tabbed, bends, rows, t, notes, iso, step)
    hide = ("plate", "T", "loc", "cx", "x0", "x1", "front", "tip", "piece", "x_out", "x_in", "t0", "tlo", "thi")
    keep = lambda p: {k: (keep(v) if isinstance(v, dict) else v) for k, v in p.items() if k not in hide}
    print(json.dumps(dict(part=title, blank_thickness_mm=round(t, 2), bends=len(bends), preview="preview.html", preview_bytes=size,
                          step=step, notes=notes, plates=[keep(p) for p in rows]), indent=1))


if __name__ == "__main__":
    main()
