"""Conservative single-skin unfolding of constant-thickness planar sheet flanges.
Bend strips may be cylindrical or imported spline surfaces. Their neutral widths
are estimated from paired skin areas and tangent-edge lengths (K=0.5).
"""
import math
import numpy as np
import geometry as g

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
            if np.dot(mp(g.centroid(fs[parent]))-q0,N)>0:N=-N
            lowe1=shared(fs[pairs[parent]],fs[lower]);lowe2=shared(fs[pairs[child]],fs[lower])
            ba=(strip_width(fs[strip],ep,ec)+strip_width(fs[lower],lowe1,lowe2))/2
            cn=V(g.outward(fs[child]));out=unit(np.cross(cn,d))
            if np.dot(V(g.centroid(fs[child]))-c0,out)<0:out=-out
            cq=q0+D*np.dot(c0-p0,d)+N*ba
            def mapping(p,c0=c0.copy(),cq=cq.copy(),d=d.copy(),out=out.copy(),D=D.copy(),N=N.copy()):
                return cq+D*np.dot(V(p)-c0,d)+N*np.dot(V(p)-c0,out)
            maps[child]=mapping;transforms[child]=rigid_map(mapping,fs[child])
            flatfaces[child]=g.TopoDS.Face_s(g.moved(fs[child],transforms[child]))
            a0,a1=mp(p0),mp(p1);z0,z1=mapping(c0),mapping(c1)
            stripface=polygon([a0,a1,z1,z0]);flatfaces[strip]=stripface
            mid=(a0+a1+z0+z1)/4
            bends.append(dict(face=stripface,p=tuple(np.r_[mid,0.]),d=tuple(np.r_[D,0.]),n=(0.,0.,1.),half=ba/2,
                              estimated_allowance_mm=ba,angle_deg=math.degrees(math.acos(np.clip(np.dot(V(g.outward(fs[parent])),cn),-1,1)))))
            queue.append(child)
    if not bends:raise ValueError('No supported bend strips were found in the formed part.')
    if set(pairs)-set(maps)-{pairs[i] for i in maps}:raise ValueError('Not all paired flanges belong to one supported unfoldable skin.')
    sew=g.BRepBuilderAPI_Sewing(.001)
    for f in flatfaces.values():sew.Add(f)
    sew.Perform();blank=g.one_face(sew.SewedShape())
    if blank is None or not g.BRepCheck_Analyzer(blank).IsValid():raise ValueError('Unfolded faces did not form a single valid non-overlapping blank.')
    # Connectivity alone does not exclude overlaps. Compare union area with all pieces.
    if abs(g.area(blank)-sum(g.area(f) for f in flatfaces.values()))>.05:raise ValueError('Unfolded faces overlap or leave gaps.')
    carriers=[dict(flat=flatfaces[i],to_formed=transforms[i].Inverted(),original=fs[i]) for i in maps]
    bends.sort(key=lambda v:v['p'][1],reverse=True)
    return blank,bends,t,carriers
