#!/usr/bin/env python3
"""One STEP -> necessary backbar DXFs, formed STEP with tabs, commentable preview."""
import argparse,json,math,os,re,sys
from pathlib import Path
import geometry as g
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from unfold import unfold,straight_endpoints

def gauge_check(o):
    """Require an actual straight contact edge, not only two isolated extreme points."""
    contact=0.;near=[]
    for e in g.edges(o['loc']):
        try:a,z=straight_endpoints(e)
        except ValueError:continue
        length=math.dist(a,z)
        if length<10:continue
        dy=abs(float(z[1]-a[1]));dx=abs(float(z[0]-a[0]))
        if min(a[1],z[1])>=o['tip']-2:
            near.append(dict(length_mm=round(length,3),angle_deg=round(math.degrees(math.atan2(dy,dx)),5)))
        if dy<.001 and abs(o['tip']-max(a[1],z[1]))<.001:contact=max(contact,length)
    return dict(direct=contact>=10,contact_mm=round(contact,3),near_edges=near)

def select(blank,bends,i,sides):
    if i in sides:o=g.choose_end(blank,bends,i,sides[i])
    else:
        # Prefer an unobstructed end; otherwise prefer direct gauging, then distance.
        o=g.choose_end(blank,bends,i,None)
        if o is None:o=min([g.choose_end(blank,bends,i,s) for s in [1,-1]],key=lambda v:(not gauge_check(v)['direct'],v['tip']))
    bends[i]['T']=o['T'];return o

def gauge_order(ends):
    """Order only the requirements that intervening regions stay flat."""
    remaining={i+1:set(o['between']) for i,o in enumerate(ends)};order=[]
    while remaining:
        ready=[i for i in remaining if not any(i in deps for deps in remaining.values())]
        if not ready:raise ValueError('Conflicting gauge dependencies for bend(s) '+', '.join(map(str,remaining))+'; choose another gauging end with --side.')
        i=min(ready);order.append(i);del remaining[i]
    return order

def join_tab(o,tab,carriers,formed,t):
    pc=g.moved(tab['piece'],o['T'].Inverted());touch=[]
    for c in carriers:
        d=g.BRepExtrema_DistShapeShape(c['flat'],pc);d.Perform()
        if d.Value()<.002:touch.append(c)
    if len(touch)!=1 or touch[0]['to_formed'] is None:raise ValueError('Tab cannot be mapped unambiguously to one formed flange.')
    solid=g.BRepPrimAPI_MakePrism(pc,g.gp_Vec(0,0,-t)).Shape();solid=g.moved(solid,touch[0]['to_formed'])
    joined=g.BRepAlgoAPI_Fuse(formed,solid).Shape()
    if not g.BRepCheck_Analyzer(joined).IsValid() or len(g.sub(joined,g.TopAbs_SOLID,g.TopoDS.Solid_s))!=1:
        raise ValueError('Tab did not join the formed part as one valid solid.')
    return joined,solid,pc

def read_input(path,flat_index):
    r=g.STEPControl_Reader()
    if r.ReadFile(str(path))!=1:raise ValueError('Cannot read the STEP file.')
    r.TransferRoots();solids=g.sub(r.OneShape(),g.TopAbs_SOLID,g.TopoDS.Solid_s)
    info={i:g.flat_info(s) for i,s in enumerate(solids)}
    flats=[i for i,x in info.items() if x];formed=[s for i,s in enumerate(solids) if not info[i]]
    if flat_index is not None:flats=[flat_index-1] if info.get(flat_index-1) else []
    if not formed:raise ValueError('The STEP must contain a formed solid; no formed part was found.')
    if flats:
        if len(flats)>1:flats=[i for i in flats if any(abs(g.volume(solids[i])-g.volume(s))<.1*g.volume(s) for s in formed)]
        if len(flats)!=1:raise ValueError('Multiple flat bodies match: specify --flat with the intended solid number.')
        flat=solids[flats[0]];n,top,t=info[flats[0]];part=min(formed,key=lambda s:abs(g.volume(s)-g.volume(flat)))
        bends=g.find_bends(flat,top)
        if not bends:raise ValueError('The supplied flat has merged bend faces. Export it with Merge faces unticked, or supply only the formed solid for estimated unfolding.')
        for bend in bends:bend['n']=n
        sew=g.BRepBuilderAPI_Sewing()
        for f in top:sew.Add(f)
        sew.Perform();blank=g.one_face(sew.SewedShape())
        if blank is None:raise ValueError('Cannot merge supplied flat faces into one outline.')
        # Normalise supplied flat to Z=0 for consistent tab solids and trimming.
        T=g.gp_Trsf();T.SetTransformation(g.gp_Ax3(g.gp_Pnt(*g.centroid(top[0])),g.gp_Dir(*n)))
        carriers=[]
        for f in top:
            if any(f.IsSame(b['face']) for b in bends):continue
            moves=g.carry(f,bends,part)
            mapping=None
            if len(moves)==1:mapping=moves[0].Multiplied(T.Inverted())
            carriers.append(dict(flat=g.TopoDS.Face_s(g.moved(f,T)),to_formed=mapping,original=None))
        blank=g.TopoDS.Face_s(g.moved(blank,T))
        for bend in bends:
            pt=g.gp_Pnt(*bend['p']).Transformed(T);d=g.gp_Vec(*bend['d']).Transformed(T)
            bend.update(face=g.moved(bend['face'],T),p=(pt.X(),pt.Y(),pt.Z()),d=(d.X(),d.Y(),d.Z()),n=(0.,0.,1.))
        return part,blank,bends,t,carriers,False
    if len(formed)!=1:raise ValueError('Multiple formed solids and no flat: provide a STEP containing only the intended part.')
    blank,bends,t,carriers=unfold(formed[0]);return formed[0],blank,bends,t,carriers,True

def apply_trim(blank,part,bends,carriers,index,sides):
    """Explicit user option only; never called by near-parallel detection."""
    o=select(blank,bends,index,sides);candidates=[]
    for e in g.edges(o['loc']):
        try:a,z=straight_endpoints(e)
        except ValueError:continue
        length=math.dist(a,z)
        if length>=10 and min(a[1],z[1])>=o['tip']-2 and abs(a[1]-z[1])<=2:
            candidates.append((length,min(a[1],z[1])))
    if not candidates:raise ValueError('Requested trim has no straight end edge within 2 mm of the tip. A larger or different trim needs explicit geometry instructions.')
    height=max(candidates)[1];depth=o['tip']-height
    if depth<.001:return blank,part,dict(bend=index+1,max_trim_mm=0)
    mask=g.moved(g.rect(-1e4,height,1e4,1e4),o['T'].Inverted())
    revised=g.one_face(g.BRepAlgoAPI_Cut(blank,mask).Shape())
    if revised is None:raise ValueError('Requested trim would split or invalidate the blank.')
    for carrier in carriers:
        cut=g.BRepAlgoAPI_Common(carrier['flat'],mask).Shape()
        if g.area(cut)<1e-7:continue
        if carrier['to_formed'] is None:raise ValueError('Trim cannot be mapped unambiguously onto a folded flange.')
        for face in g.faces(cut):
            tool=g.BRepPrimAPI_MakePrism(face,g.gp_Vec(0,0,-T_THICKNESS)).Shape()
            part=g.BRepAlgoAPI_Cut(part,g.moved(tool,carrier['to_formed'])).Shape()
        carrier['flat']=g.one_face(g.BRepAlgoAPI_Cut(carrier['flat'],mask).Shape())
        if carrier['flat'] is None:raise ValueError('Trim removes or splits a flange.')
    if not g.BRepCheck_Analyzer(part).IsValid():raise ValueError('Trim made the folded part invalid.')
    if not gauge_check(select(revised,bends,index,sides))['direct']:raise ValueError('Trim did not establish a usable parallel gauge edge.')
    return revised,part,dict(bend=index+1,max_trim_mm=round(depth,4),removed_area_mm2=round(g.area(blank)-g.area(revised),4))

def merge_step_faces(shape):
    """Remove coplanar tab/flange divisions without relaxing geometry tolerances."""
    before=g.volume(shape);count=len(g.faces(shape))
    merge=ShapeUpgrade_UnifySameDomain(shape,True,True,False)
    merge.SetLinearTolerance(1e-7);merge.SetAngularTolerance(1e-7);merge.Build()
    result=merge.Shape();delta=abs(g.volume(result)-before);limit=max(.1,.001*abs(before))
    if not g.BRepCheck_Analyzer(result).IsValid() or len(g.sub(result,g.TopAbs_SOLID,g.TopoDS.Solid_s))!=1 or delta>min(.5,limit):
        raise ValueError('Coplanar face merging did not preserve one valid solid and its volume.')
    if max(abs(a-b) for a,b in zip(g.bbox(shape),g.bbox(result)))>.001:
        raise ValueError('Coplanar face merging changed the part bounds.')
    return result,dict(faces_before_merge=count,faces_after_merge=len(g.faces(result)),merge_volume_difference_mm3=round(delta,6))


def checked_step(shape,path,tabs=()):
    """Documented engineering tolerance, unchanged by task results."""
    valid=g.BRepCheck_Analyzer(shape).IsValid();solids=g.sub(shape,g.TopAbs_SOLID,g.TopoDS.Solid_s)
    if not valid or len(solids)!=1:raise ValueError('Programming STEP is not one valid solid.')
    g.write_step(shape,str(path))
    r=g.STEPControl_Reader()
    if r.ReadFile(str(path))!=1 or not r.TransferRoots():raise ValueError('Cannot read back the exported STEP.')
    back=r.OneShape();delta=abs(g.volume(back)-g.volume(shape));limit=max(.5,1e-5*abs(g.volume(shape)))
    if len(g.sub(back,g.TopAbs_SOLID,g.TopoDS.Solid_s))!=1 or not g.BRepCheck_Analyzer(back).IsValid() or delta>limit:
        path.unlink(missing_ok=True);raise ValueError('STEP readback did not preserve valid geometry within the documented volume tolerance.')
    for tab in tabs:
        retained=g.BRepAlgoAPI_Common(back,tab).Shape();volume=g.volume(tab)
        if abs(g.volume(retained)-volume)>max(.1,.001*volume):
            path.unlink(missing_ok=True);raise ValueError('STEP readback did not preserve a programming tab.')
    return dict(volume_difference_mm3=round(delta,6),volume_tolerance_mm3=round(limit,6),
                strict_geometry_valid=g.BRepCheck_Analyzer(back,True,False,True).IsValid(),tabs_verified=len(tabs))

def main():
    global T_THICKNESS
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('step');ap.add_argument('out')
    ap.add_argument('--flat',type=int);ap.add_argument('--side',action='append',default=[]);ap.add_argument('--at',action='append',default=[])
    ap.add_argument('--wrap',type=float,default=20);ap.add_argument('--die-clear',type=float,default=8);ap.add_argument('--tab-width',type=float,default=5)
    ap.add_argument('--trim-for',type=int,action='append',default=[],help='ONLY when the user requests trimming: trim the gauged free edge parallel to bend N.')
    a=ap.parse_args();sides={};at={}
    for v in a.side:
        k,sep,s=v.partition('=')
        if not sep or not k.isdigit() or s not in ('+','-'):raise ValueError('--side must be N=+ or N=-.')
        sides[int(k)-1]=1 if s=='+' else -1
    for v in a.at:
        k,sep,x=v.partition('=')
        if not sep or not k.isdigit() or not math.isfinite(float(x)):raise ValueError('--at must be N=X with a finite coordinate.')
        at[int(k)-1]=float(x)
    if not 10<=a.wrap<=20 or not 2<=a.tab_width<=20 or a.die_clear<0:raise ValueError('Use wrap 10–20 mm, tab width 2–20 mm and non-negative die clearance.')
    part,blank,bends,t,carriers,estimated=read_input(a.step,a.flat);T_THICKNESS=t
    source_strict=g.BRepCheck_Analyzer(part,True,False,True).IsValid()
    if any(i<0 or i>=len(bends) for i in [*sides,*at,*[j-1 for j in a.trim_for]]):raise ValueError('An option names a bend that is not present.')
    trims=[]
    for i in a.trim_for:
        blank,part,change=apply_trim(blank,part,bends,carriers,i-1,sides);trims.append(change)
    order=gauge_order([select(blank,bends,i,sides) for i in range(len(bends))])
    outdir=Path(a.out);outdir.mkdir(parents=True,exist_ok=True)
    title=re.sub(r'[^A-Za-z0-9_.-]+','_',Path(a.step).stem).strip('_');rows=[];tabbed=blank;prisms=[];formed=part;expected=0.;notes=[]
    if estimated:notes.append('ESTIMATED unfolding from formed geometry; K=0.50 neutral-axis assumption. Bend-transition edges are approximated. Verify the jig against a production blank.')
    else:notes.append('Flat pattern supplied in the STEP; original bend regions are used.')
    notes.append('Gauge-dependency order: '+', '.join(f'B{i}' for i in order)+'. This orders flat-region requirements only; tooling collisions and backgauge travel are unverified.')
    if not source_strict:
        notes.append('The source formed STEP already has strict surface/edge warnings. Assess source and output warnings separately; software import remains unconfirmed.')
    for change in trims:notes.append(f"User-requested trim for B{change['bend']}: maximum {change['max_trim_mm']:.4f} mm. Applied to the real blank, jig pockets and programming STEP.")
    for i,bend in enumerate(bends):
        o=select(blank,bends,i,sides);check=gauge_check(o)
        p=dict(bend=i+1,side='+' if o['s']>0 else '-',T=o['T'],loc=o['loc'],tip=o['tip'],program_gauge_mm=round(o['tip'],2),warnings=[],gauging=check)
        if o['between']:p['warnings'].append('Gauge this bend before bend(s) '+', '.join(map(str,o['between']))+' are formed; the intervening region must remain flat.')
        if check['direct']:
            p['bend_to_finger_tip_mm']=p['program_gauge_mm'];p['tab']=dict(skipped=f"Direct backgauge on {check['contact_mm']:.2f} mm parallel edge; no jig or tab.")
        else:
            p.update(g.build_plate(o,a.wrap,a.die_clear,p['warnings']))
            if 'plate_error' in p:raise ValueError(f"B{i+1}: {p['plate_error']}")
            if not g.BRepCheck_Analyzer(p['plate']).IsValid() or any('separate pieces' in w for w in p['warnings']):raise ValueError(f'B{i+1}: pocket splits or invalidates the plate.')
            if p['clearance_mm']!=.1:raise ValueError(f'B{i+1}: pocket clearance failed.')
            p['tab']=g.build_tab(o,bend['half']+.01,blank,at.get(i),a.tab_width,[])
            if 'error' in p['tab']:raise ValueError(f"B{i+1}: {p['tab']['error']}")
            if 'warning' in p['tab']:p['warnings'].append(p['tab'].pop('warning'))
            if 'piece' in p['tab']:
                candidate=g.moved(p['tab']['piece'],o['T'].Inverted())
                for previous in rows:
                    if 'piece' not in previous.get('tab',{}):continue
                    existing=g.moved(previous['tab']['piece'],previous['T'].Inverted())
                    if abs(g.area(existing)-g.area(candidate))<.001 and abs(g.area(g.BRepAlgoAPI_Common(existing,candidate).Shape())-g.area(candidate))<.001:
                        p['tab']=dict(skipped=f"Uses the programming tab already added for B{previous['bend']}.")
                        break
            if 'piece' in p['tab']:
                try:joined,solid,pc=join_tab(o,p['tab'],carriers,formed,t)
                except ValueError as error:
                    if i in at:raise ValueError(f'B{i+1}: {error} Explicit tab position was not moved.')
                    distance=p['tab']['x_out']-p['tab']['t0'];sign=1 if distance>0 else -1
                    distance=abs(distance)-a.tab_width/2
                    while distance>=a.tab_width+.5:
                        retry=g.build_tab(o,bend['half']+.01,blank,sign*distance,a.tab_width,[])
                        distance-=a.tab_width/2
                        if 'piece' not in retry or max(retry['heights_mm'])>g.TAB_H_MAX:continue
                        try:joined,solid,pc=join_tab(o,retry,carriers,formed,t)
                        except ValueError:continue
                        retry['placed']='join retry';p['tab']=retry
                        p['warnings'].append('Automatic tab moved toward the blank tip to join one valid formed solid.')
                        break
                    else:raise ValueError(f'B{i+1}: {error} No valid automatic tab position was found.')
                formed=joined;prisms.append(solid);expected+=g.area(pc)*t
                tabbed=g.one_face(g.BRepAlgoAPI_Fuse(tabbed,pc).Shape())
                if tabbed is None:raise ValueError('Tab did not join the flat outline.')
                expected=(g.area(tabbed)-g.area(blank))*t
                p['tab']['edge_off_tip_line_mm']=round(abs(g.bbox(p['tab']['piece'])[4]-o['tip']),4)
                if p['tab']['edge_off_tip_line_mm']>.001:raise ValueError('Tab edge does not align with its gauge line.')
            # Share plates only when their position and shape agree in the blank frame.
            for q in rows:
                if 'plate' in q and abs(g.area(p['plate'])-g.area(q['plate']))<.01:
                    same=g.moved(p['plate'],g.g_to(q['T'],p['T']))
                    common=g.BRepAlgoAPI_Common(same,q['plate']).Shape()
                    if abs(g.area(common)-g.area(q['plate']))<.01:p['same_plate_as']=q['bend'];p['dxf']=q['dxf'];break
            else:p['dxf']=f'{title}_backbar_B{i+1}.dxf'
        rows.append(p)
    for p in rows:
        for q in rows:
            if p is q or 'piece' not in q.get('tab',{}):continue
            pc=g.moved(q['tab']['piece'],g.g_to(p['T'],q['T']))
            if g.bbox(pc)[4]>p['tip']+.001:
                p['warnings'].append(f"The programming tab for B{q['bend']} projects beyond this bend's gauge line; select the intended B{p['bend']} gauge edge in CADMAN-B.")
    if abs(g.volume(formed)-g.volume(part)-expected)>max(.1,.001*expected):raise ValueError('Added tab volume does not agree with tab area × thickness.')
    formed,merge=merge_step_faces(formed)
    step=f'{title}_with_tabs.step';verification=checked_step(formed,outdir/step,prisms);verification.update(merge)
    if not verification['strict_geometry_valid']:notes.append('Strict surface/edge analysis reports residual geometry warnings. Basic solid and tab-retention checks passed; SolidWorks/CADMAN-B compatibility is not confirmed by these checks.')
    for p in rows:
        if 'plate' in p and 'same_plate_as' not in p:
            g.write_dxf(p['plate'],str(outdir/p['dxf']))
            if g.ezdxf.readfile(outdir/p['dxf']).audit().errors:raise ValueError('DXF audit failed.')
    if not prisms:notes.append('No tabs required; the output STEP contains the unchanged formed part, except for any explicitly requested trim.')
    notes += ['Real blanks are manufactured without the programming tabs. Pocket geometry follows the real blank.',
              'Jig plates: 100 mm wide × 6 mm thick, 50.2 × 20 mm finger slot, 20 mm nominal wrap and 0.1 mm contour clearance.',
              'For jig-assisted bends only, finger tip sits 50 mm behind the programmed gauge line. Direct-gauge bends have no jig offset.',
              f'Check each plate-front distance against the actual die. The {a.die_clear:g} mm minimum is an assumption. Tooling collisions, backgauge travel, finger height and complete bend sequence have not been simulated.',
              f"STEP readback: one valid solid; volume difference {verification['volume_difference_mm3']:.6f} mm³ (limit {verification['volume_tolerance_mm3']:.6f} mm³)."]
    iso=g.iso_svg(formed,prisms,g.gp_Trsf())
    preview=f'{title}_preview.html';g.preview(str(outdir/preview),title,blank,tabbed,bends,rows,t,notes,iso,step)
    hide={'plate','T','loc','cx','x0','x1','front','tip','piece','x_out','x_in','t0','tlo','thi'}
    def clean(d):return {k:clean(v) if isinstance(v,dict) else v for k,v in d.items() if k not in hide}
    report=dict(part=title,estimated_unfold=estimated,blank_thickness_mm=round(t,4),bends=len(bends),trims=trims,step=step,preview=preview,notes=notes,verification=verification,plates=[clean(p) for p in rows])
    # Internal report; only DXF, STEP and the review preview are user deliverables.
    (outdir/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError) as exc:sys.exit('ERROR: '+str(exc))
