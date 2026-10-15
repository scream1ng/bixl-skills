"""Geometry-derived physical change overlays; CAD-only tabs are excluded."""
import geometry as g
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex

STYLE='''
.physical-changes{background:#fffdf7;border:2px solid #d9ab61;border-radius:12px;padding:18px;margin:20px 0}.physical-changes h2{margin:0 0 8px;font-size:21px}.change-grid{display:grid;grid-template-columns:1.3fr 1fr;gap:20px}.change-detail{padding:12px;background:white;border:1px solid #dde2e6;border-radius:9px;margin-bottom:12px}.change-detail h3{font-size:16px;margin:0}.change-detail .fig svg{height:150px;overflow:hidden}.original-outline{fill:none;stroke:#6b7780;stroke-width:.22;stroke-dasharray:1 .65}.material-added{fill:#249bdf;stroke:#0876b8;stroke-width:.15}.material-removed{fill:#ef6857;stroke:#be362c;stroke-width:.15}.change-leader{stroke:#344b59;stroke-width:.3}.change-pin{fill:white;stroke:#344b59;stroke-width:.3}.change-label{font:3px sans-serif;fill:#263d4a;stroke:none;text-anchor:middle;dominant-baseline:middle}.fig svg{overflow:hidden}@media(max-width:750px){.change-grid{grid-template-columns:1fr}}
'''


def compare_blanks(original,revised):
    """Return separate connected add/remove regions with sampled offset measures."""
    if original is None:return []
    changes=[]
    for kind,a,b in [('added',revised,original),('removed',original,revised)]:
        difference=g.BRepAlgoAPI_Cut(a,b).Shape()
        faces=sorted((f for f in g.faces(difference) if g.area(f)>1e-6),key=g.bbox)
        boundaries=g.sub(b,g.TopAbs_WIRE,g.TopoDS.Wire_s)
        for face in faces:
            contour=g.outline(face,.01);stride=max(1,len(contour)//250);maximum=0.
            for x,y in contour[::stride]:
                point=BRepBuilderAPI_MakeVertex(g.gp_Pnt(x,y,0)).Vertex()
                distances=[]
                for boundary in boundaries:
                    distance=g.BRepExtrema_DistShapeShape(point,boundary);distance.Perform()
                    if not distance.IsDone():raise ValueError('Cannot measure physical change region.')
                    distances.append(distance.Value())
                maximum=max(maximum,min(distances))
            changes.append(dict(id='C'+str(len(changes)+1),kind=kind,face=face,area_mm2=g.area(face),sampled_max_offset_mm=maximum))
    return changes


def polygon(face,frame,css):
    face=g.TopoDS.Face_s(g.moved(face,frame));outer=g.BRepTools.OuterWire_s(face)
    contours=[g.loop(outer)]+[g.loop(w) for w in g.sub(face,g.TopAbs_WIRE,g.TopoDS.Wire_s) if not w.IsSame(outer)]
    paths=['M'+' L'.join(f'{x:.4f},{-y:.4f}' for x,y in points)+' Z' for points in contours]
    return f'<path class="{css}" fill-rule="evenodd" d="{" ".join(paths)}"/>'


def overlay(changes,frame,pins=True):
    result=''
    for change in changes:
        result+=polygon(change['face'],frame,'material-'+change['kind'])
        if not pins:continue
        box=g.bbox(g.moved(change['face'],frame));x=(box[0]+box[3])/2;y=(box[1]+box[4])/2
        dx,dy=(8,0) if box[4]-box[1]>box[3]-box[0] else (0,8)
        result+=g.line_svg('change-leader',x,y,x+dx,y+dy)
        result+=f'<circle class="change-pin" cx="{x+dx}" cy="{-y-dy}" r="3.5"/><text class="change-label" x="{x+dx}" y="{-y-dy}">{change["id"]}</text>'
    return result


def section(original,revised,changes,frame):
    if not changes:return ''
    content=polygon(revised,frame,'blank')+polygon(original,frame,'original-outline')+overlay(changes,frame)
    box=g.bbox(g.moved(original,frame));new=g.bbox(g.moved(revised,frame))
    xmin=min(box[0],new[0])-18;xmax=max(box[3],new[3])+18;ymin=min(box[1],new[1])-18;ymax=max(box[4],new[4])+18
    view=f'{xmin} {-ymax} {xmax-xmin} {ymax-ymin}'
    details=[]
    for change in changes:
        box=g.bbox(g.moved(change['face'],frame));width=box[3]-box[0];height=box[4]-box[1];pad=max(3,.15*max(width,height))
        zoom=f'{box[0]-pad} {-box[4]-pad} {width+2*pad} {height+2*pad}'
        heading=change['id']+' · Material '+change['kind']
        details.append(f'<article class="change-detail"><h3>{heading}</h3><p>Approx. maximum local offset: {change["sampled_max_offset_mm"]:.3f} mm</p><div class="fig" data-name="{heading} (display coordinates)"><svg xmlns="http://www.w3.org/2000/svg" viewBox="{zoom}">{content}</svg></div></article>')
    return f'''<section class="physical-changes"><h2>Physical part changes · {len(changes)} location(s)</h2>
<p><b>These changes affect the real blank and the formed CAD.</b> CAD-only programming tabs are shown separately in orange.</p>
<div class="change-grid"><div><div class="fig" data-name="Physical changes (display coordinates)"><svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}">{content}</svg></div><p class="muted">Blue = material added · Red = material removed · Dashed grey = original outline. Close-ups overlay both contours at the same scale; offsets are sampled geometric estimates.</p></div><div>{''.join(details)}</div></div></section>'''
