"""Conservative single-skin unfolding of constant-thickness planar sheet flanges.
Bend strips may be cylindrical or imported spline surfaces. Their neutral widths
are estimated from paired skin areas and tangent-edge lengths (K=0.5).
"""
import math
import numpy as np
import geometry as g
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.TopAbs import TopAbs_IN
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder

V=lambda p:np.asarray(p,dtype=float)
def unit(v):
    length=np.linalg.norm(v)
    if length<1e-9: raise ValueError('Degenerate bend direction.')
    return v/length

def polygon(points):
    p=g.BRepBuilderAPI_MakePolygon()
    for x,y in points: p.Add(g.gp_Pnt(float(x),float(y),0))
    p.Close()
    return g.BRepBuilderAPI_MakeFace(p.Wire()).Face()

def rigid_map(mapper, face):
    zero=mapper([0,0,0])
    cols=[mapper(p)-zero for p in ([1,0,0],[0,1,0],[0,0,1])]
    x=V([c[0] for c in cols]); y=V([c[1] for c in cols]); n=np.cross(x,y)
    T=g.gp_Trsf()
    T.SetValues(*map(float,[*x,zero[0],*y,zero[1],*n,-np.dot(n,V(g.centroid(face)))]))
    return T

def shared(a,b):
    es=[e for e in g.edges(a) if any(e.IsSame(x) for x in g.edges(b))]
    if len(es)!=1:raise ValueError('A bend must meet each flange at one tangent edge.')
    return es[0]

def straight_endpoints(edge):
    points=g.pts(edge)
    if len(points)!=2 or math.dist(*points)<1e-6:raise ValueError('Cannot identify straight bend tangent.')
    a,z=map(V,points);d=unit(z-a)
    c=g.BRepAdaptor_Curve(edge)
    for t in np.linspace(c.FirstParameter(),c.LastParameter(),9):
        q=c.Value(float(t));v=V([q.X(),q.Y(),q.Z()])-a
        if np.linalg.norm(v-d*np.dot(v,d))>.005:raise ValueError('Curved bend tangent: estimated unfolding is unsupported.')
    return a,z

def strip_width(face,e1,e2):
    a,z=straight_endpoints(e1);c,d=straight_endpoints(e2)
    return g.area(face)/((np.linalg.norm(z-a)+np.linalg.norm(d-c))/2)

def interior_direction(face,edge):
    """Find material beside the tangent, including edges inside concave notches."""
    a,z=straight_endpoints(edge);mid=(a+z)/2
    direction=unit(np.cross(V(g.outward(face)),unit(z-a)))
    for distance in (.001,.01,.1):
        inside=[sign for sign in (1,-1) if BRepClass_FaceClassifier(
            face,g.gp_Pnt(*map(float,mid+sign*distance*direction)),1e-7).State()==TopAbs_IN]
        if len(inside)==1:return inside[0]*direction
    raise ValueError('Cannot identify material beside a bend tangent.')

def cross2(a,b):return a[0]*b[1]-a[1]*b[0]

def clean_wire(wire, tol=2e-4):
    """Rebuild a planar wire from exact lines and circular arcs where the imported
    spline edges are such (checked span by span); otherwise keep the original edge.
    Imported degree-1/rational degree-2 B-splines break planar offsets and face fitting."""
    from OCP.BRepTools import BRepTools_WireExplorer
    from OCP.GC import GC_MakeArcOfCircle, GC_MakeSegment
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GeomAbs import GeomAbs_BSplineCurve
    P=lambda q:g.gp_Pnt(float(q[0]),float(q[1]),0.)
    out=[];ex=BRepTools_WireExplorer(wire)
    while ex.More():
        e=ex.Current();c=BRepAdaptor_Curve(e);a,b=c.FirstParameter(),c.LastParameter()
        cuts=[a,b]
        if c.GetType()==GeomAbs_BSplineCurve:
            bs=c.BSpline();cuts=sorted({a,b,*[bs.Knot(i) for i in range(1,bs.NbKnots()+1) if a<bs.Knot(i)<b]})
        rev=e.Orientation()==1
        segs=[]
        for u0,u1 in zip(cuts,cuts[1:]):
            us=np.linspace(u0,u1,7);Q=[V([c.Value(float(x)).X(),c.Value(float(x)).Y()]) for x in us]
            d=Q[-1]-Q[0];L=np.linalg.norm(d)
            if L<1e-7:segs=None;break
            n=V([-d[1],d[0]])/L
            if max(abs(np.dot(q-Q[0],n)) for q in Q)<tol:segs.append(('L',Q[0],Q[-1]));continue
            # circle through first, middle, last
            A,B,C=Q[0],Q[3],Q[-1];M=np.array([[2*(B-A)[0],2*(B-A)[1]],[2*(C-A)[0],2*(C-A)[1]]])
            rhs=V([B@B-A@A,C@C-A@A])
            try:ctr=np.linalg.solve(M,rhs)
            except np.linalg.LinAlgError:segs=None;break
            r=np.linalg.norm(A-ctr)
            if max(abs(np.linalg.norm(q-ctr)-r) for q in Q)>tol:segs=None;break
            segs.append(('A',Q[0],Q[3],Q[-1]))
        if segs is None:out.append(('E',e));ex.Next();continue
        if rev:segs=[(s0[0],*s0[1:][::-1]) for s0 in segs[::-1]]
        out.extend(segs);ex.Next()
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeWire,BRepBuilderAPI_MakeEdge
    if any(item[0]=='E' for item in out):return wire
    # Join collinear line pieces (flange/bend-strip junctions): the near-zero kinks
    # make outward planar offsets fail. Only joints straight within 1e-6 mm are joined.
    merged=[]
    for item in out:
        if merged and item[0]=='L' and merged[-1][0]=='L':
            a0,a1=merged[-1][1],item[2];d=a1-a0;L=np.linalg.norm(d)
            if L>1e-6 and abs(cross2(d/L,merged[-1][2]-a0))<1e-6:merged[-1]=('L',a0,a1);continue
        merged.append(item)
    if len(merged)>2 and merged[0][0]=='L' and merged[-1][0]=='L':
        a0,a1=merged[-1][1],merged[0][2];d=a1-a0;L=np.linalg.norm(d)
        if abs(cross2(d/L,merged[0][1]-a0))<1e-6:merged=[('L',a0,a1)]+merged[1:-1]
    out=merged
    mk=BRepBuilderAPI_MakeWire();last=None;first=out[0][1]
    for k,item in enumerate(out):
        start=item[1] if last is None else last
        end=first if k==len(out)-1 else item[-1]
        if item[0]=='L':edge=BRepBuilderAPI_MakeEdge(GC_MakeSegment(P(start),P(end)).Value()).Edge()
        else:edge=BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(P(start),P(item[2]),P(end)).Value()).Edge()
        last=end;mk.Add(edge)
    if not mk.IsDone():raise ValueError('Could not rebuild the blank outline from lines and arcs.')
    return mk.Wire()

def clean_blank(face):
    from OCP.BRepTools import BRepTools
    from OCP.TopAbs import TopAbs_WIRE
    from OCP.ShapeFix import ShapeFix_Face
    from OCP.gp import gp_Pln, gp_Dir
    outer=BRepTools.OuterWire_s(face)
    mk=g.BRepBuilderAPI_MakeFace(gp_Pln(g.gp_Pnt(0,0,0),gp_Dir(0,0,1)),clean_wire(outer),True)
    for w in g.sub(face,TopAbs_WIRE,g.TopoDS.Wire_s):
        if not w.IsSame(outer):
            mk.Add(clean_wire(w))
    f=mk.Face();fx=ShapeFix_Face(f);fx.FixOrientation();fx.Perform();f=fx.Face()
    if g.area(f)<0:f=g.TopoDS.Face_s(f.Reversed())
    if not g.BRepCheck_Analyzer(f).IsValid():raise ValueError('Rebuilt blank outline is invalid.')
    # Every original boundary point must lie on the rebuilt boundary.
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    newb=g.TopoDS.Wire_s(BRepTools.OuterWire_s(f));worst=0.
    edges_new=[x for x in g.edges(f)]
    from OCP.TopoDS import TopoDS_Compound
    from OCP.BRep import BRep_Builder
    comp=TopoDS_Compound();bb=BRep_Builder();bb.MakeCompound(comp)
    for x in edges_new:bb.Add(comp,x)
    for e in g.edges(face):
        c=BRepAdaptor_Curve(e)
        for u in np.linspace(c.FirstParameter(),c.LastParameter(),5):
            d=BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(c.Value(float(u))).Vertex(),comp);d.Perform();worst=max(worst,d.Value())
    if worst>.002 or abs(boundary_area(f)-boundary_area(face))>.05:raise ValueError(f'Rebuilt blank outline deviates {worst:.4f} mm from the unfolded outline.')
    clean_blank.deviation_mm=worst
    return f

def boundary_area(face):
    from OCP.BRepTools import BRepTools
    from OCP.TopAbs import TopAbs_WIRE
    outer=BRepTools.OuterWire_s(face);t=0.
    for w in g.sub(face,TopAbs_WIRE,g.TopoDS.Wire_s):
        P=np.array(g.loop(w,0.0005));x,y=P[:,0],P[:,1]
        a=0.5*abs(np.dot(x,np.roll(y,1))-np.dot(y,np.roll(x,1)));t+=a if w.IsSame(outer) else -a
    return t

def rebuild_flat(face):
    """Rebuild a flattened piece on the exact XY plane with fresh pcurves and +Z orientation.
    Imported (e.g. Rhino) trims can carry pcurves that disagree slightly with their 3D edges,
    which corrupts area integration and validity of the merged blank."""
    from OCP.BRepTools import BRepTools
    from OCP.ShapeFix import ShapeFix_Face
    from OCP.gp import gp_Pln, gp_Pnt as P, gp_Dir as D
    outer=BRepTools.OuterWire_s(face)
    mk=g.BRepBuilderAPI_MakeFace(gp_Pln(P(0,0,0),D(0,0,1)),outer,True)
    from OCP.TopAbs import TopAbs_WIRE
    for w in g.sub(face,TopAbs_WIRE,g.TopoDS.Wire_s):
        if not w.IsSame(outer): mk.Add(w)
    f=mk.Face();fx=ShapeFix_Face(f);fx.Perform();f=fx.Face()
    if g.area(f)<0: f=g.TopoDS.Face_s(f.Reversed())
    return f

def unfold(formed):
    fs=g.faces(formed)
    planar={i:f for i,f in enumerate(fs) if g.plane_of(f) is not None}
    root=max(planar,key=lambda i:g.area(fs[i]))
    def mates(i,thickness=None):
        n=V(g.outward(fs[i]));c=V(g.centroid(fs[i]));out=[]
        for j,f in planar.items():
            if i==j or np.dot(n,V(g.outward(f)))>-.9999:continue
            if abs(g.area(f)-g.area(fs[i]))>max(.05,.002*g.area(fs[i])):continue
            delta=V(g.centroid(f))-c;dist=abs(np.dot(delta,n))
            if np.linalg.norm(delta-n*np.dot(delta,n))>.05:continue
            if thickness is None and not .3<=dist<=20:continue
            if thickness is not None and abs(dist-thickness)>.02:continue
            out.append((dist,j))
        return sorted(out)
    opposite=mates(root)
    if not opposite:raise ValueError('Cannot infer uniform sheet thickness from paired planar faces.')
    t,other=opposite[0]
    n=V(g.outward(fs[root]));major=int(np.argmax(np.abs(n)))
    if n[major]<0:root=other
    pairs={}
    for i in planar:
        m=mates(i,t)
        if len(m)==1:pairs[i]=m[0][1]
    # A valid curved strip must link a pair of paired flange faces on each skin.
    adjacency={i:[] for i in pairs};links={}
    for k,f in enumerate(fs):
        if k in planar:continue
        near=[i for i in pairs if any(e.IsSame(x) for e in g.edges(f) for x in g.edges(fs[i]))]
        if len(near)==2 and pairs[near[0]]!=near[1]:links[k]=near
    for k,(a,c) in links.items():
        low=[j for j,ends in links.items() if set(ends)=={pairs[a],pairs[c]}]
        if len(low)==1:
            adjacency[a].append((c,k,low[0]));adjacency[c].append((a,k,low[0]))
    n=V(g.outward(fs[root]));ref=V([0,1,0]) if abs(n[1])<.9 else V([1,0,0])
    ex=unit(np.cross(ref,n));ey=np.cross(n,ex);origin=V(g.centroid(fs[root]))
    maps={root:lambda p:V([np.dot(V(p)-origin,ex),np.dot(V(p)-origin,ey)])}
    transforms={root:rigid_map(maps[root],fs[root])}
    flatfaces={root:g.TopoDS.Face_s(g.moved(fs[root],transforms[root]))}
    bends=[];queue=[root];visited_strips=set()
    while queue:
        parent=queue.pop(0)
        for child,strip,lower in adjacency[parent]:
            if strip in visited_strips:continue
            if child in maps:raise ValueError('Cyclic sheet topology cannot be unfolded reliably.')
            visited_strips.add(strip)
            ep=shared(fs[parent],fs[strip]);ec=shared(fs[child],fs[strip])
            p0,p1=straight_endpoints(ep);c0,c1=straight_endpoints(ec);d=unit(p1-p0)
            if abs(np.dot(unit(c1-c0),d))<.99999:raise ValueError('Nonparallel bend tangents are unsupported.')
            if np.dot(c1-c0,d)<0:c0,c1=c1,c0
            mp=maps[parent];q0,q1=mp(p0),mp(p1);D=unit(q1-q0);N=V([-D[1],D[0]])
            inside=interior_direction(fs[parent],ep)
            if np.dot(mp((p0+p1)/2+inside)-mp((p0+p1)/2),N)>0:N=-N
            lowe1=shared(fs[pairs[parent]],fs[lower]);lowe2=shared(fs[pairs[child]],fs[lower])
            ba=(strip_width(fs[strip],ep,ec)+strip_width(fs[lower],lowe1,lowe2))/2
            cn=V(g.outward(fs[child]));out=interior_direction(fs[child],ec)
            cq=q0+D*np.dot(c0-p0,d)+N*ba
            def mapping(p,c0=c0.copy(),cq=cq.copy(),d=d.copy(),out=out.copy(),D=D.copy(),N=N.copy()):
                return cq+D*np.dot(V(p)-c0,d)+N*np.dot(V(p)-c0,out)
            maps[child]=mapping;transforms[child]=rigid_map(mapping,fs[child])
            flatfaces[child]=g.TopoDS.Face_s(g.moved(fs[child],transforms[child]))
            a0,a1=mp(p0),mp(p1);z0,z1=mapping(c0),mapping(c1)
            stripface=polygon([a0,a1,z1,z0]);flatfaces[strip]=stripface
            mid=(a0+a1+z0+z1)/4
            # Preserve formed-surface evidence for independent exported-STEP checks.
            surface=BRepAdaptor_Surface(fs[strip]);lower_surface=BRepAdaptor_Surface(fs[lower])
            physical={"formed_center":tuple(map(float,g.centroid(fs[strip])))}
            if surface.GetType()==GeomAbs_Cylinder and lower_surface.GetType()==GeomAbs_Cylinder:
                cylinder=surface.Cylinder();axis=cylinder.Axis();ad=axis.Direction();ap=axis.Location()
                direction=V([ad.X(),ad.Y(),ad.Z()])
                if direction[np.argmax(np.abs(direction))]<0:direction=-direction
                physical.update(formed_axis_p=(ap.X(),ap.Y(),ap.Z()),formed_axis_d=tuple(map(float,direction)),
                                inner_radius_mm=min(cylinder.Radius(),lower_surface.Cylinder().Radius()),
                                fold_sense=1 if np.dot(np.cross(V(g.outward(fs[parent])),cn),direction)>0 else -1)
            bends.append(dict(**physical,face=stripface,p=tuple(np.r_[mid,0.]),d=tuple(np.r_[D,0.]),n=(0.,0.,1.),half=ba/2,
                              estimated_allowance_mm=ba,angle_deg=math.degrees(math.acos(np.clip(np.dot(V(g.outward(fs[parent])),cn),-1,1)))))
            queue.append(child)
    if not bends:raise ValueError('No supported bend strips were found in the formed part.')
    if set(pairs)-set(maps)-{pairs[i] for i in maps}:raise ValueError('Not all paired flanges belong to one supported unfoldable skin.')
    flatfaces={k:rebuild_flat(f) for k,f in flatfaces.items()}
    sew=g.BRepBuilderAPI_Sewing(.001)
    for f in flatfaces.values():sew.Add(f)
    sew.Perform();blank=g.one_face(sew.SewedShape())
    if blank is None or not g.BRepCheck_Analyzer(blank).IsValid():raise ValueError('Unfolded faces did not form a single valid non-overlapping blank.')
    # Connectivity alone does not exclude overlaps. Compare union area with all pieces.
    # Connectivity alone does not exclude overlaps. Compare union area with all pieces, using
    # areas from the discretised 3D boundaries (what is actually cut); imported trims can make
    # integrated surface areas disagree by tenths of mm2 on otherwise coincident geometry.
    if abs(boundary_area(blank)-sum(boundary_area(f) for f in flatfaces.values()))>.05:raise ValueError('Unfolded faces overlap or leave gaps.')
    blank=clean_blank(blank)
    carriers=[dict(flat=flatfaces[i],to_formed=transforms[i].Inverted(),original=fs[i]) for i in maps]
    bends.sort(key=lambda v:v['p'][1],reverse=True)
    return blank,bends,t,carriers
