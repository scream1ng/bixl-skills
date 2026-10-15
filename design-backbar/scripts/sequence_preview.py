"""Compact bend-sequence review generated from the same geometry as the exports."""
import html
import math
from pathlib import Path
import geometry as g
from unfold import straight_endpoints
import physical_changes as changes_ui


def display_frame(blank, bends):
    frame = bends[0]['T']
    bounds = g.bbox(g.moved(blank, frame))
    if bounds[4] - bounds[1] > bounds[3] - bounds[0]:
        turn = g.gp_Trsf()
        from OCP.gp import gp_Ax1
        turn.SetRotation(gp_Ax1(g.gp_Pnt(), g.gp_Dir(0, 0, 1)), math.pi / 2)
        frame = turn.Multiplied(frame)
    return frame


def step_svg(blank, bends, rows, selected, frame, members=None, changes=None):
    """One view per operation; plate and gauge line exist only for assisted bends."""
    members=members or [selected]
    points, layers, refs = [], [], []
    def polygon(face, transform, css):
        face = g.TopoDS.Face_s(g.moved(face, transform))
        outer = g.BRepTools.OuterWire_s(face)
        contours = [g.loop(outer)] + [g.loop(w) for w in g.sub(face, g.TopAbs_WIRE, g.TopoDS.Wire_s) if not w.IsSame(outer)]
        data = []
        for contour in contours:
            points.extend(contour)
            data.append('M' + ' L'.join(f'{x:.3f},{-y:.3f}' for x, y in contour) + ' Z')
        return f'<path class="{css}" fill-rule="evenodd" d="{" ".join(data)}"/>'
    def line(a, b, transform, css):
        a, b = [g.gp_Pnt(*v).Transformed(transform) for v in (a, b)]
        points.extend([(a.X(), a.Y()), (b.X(), b.Y())])
        return g.line_svg(css, a.X(), a.Y(), b.X(), b.Y())
    p = rows[selected - 1]
    if 'plate' in p:
        transform = g.g_to(frame, p['T'])
        layers.append(polygon(p['plate'], transform, 'plate'))
        refs.append(line((p['cx']-g.PLATE_W/2, p['tip'], 0),
                         (p['cx']+g.PLATE_W/2, p['tip'], 0), transform, 'gauge'))
    layers.append(polygon(blank, frame, 'blank'))
    owner = p.get('tab', {}).get('same_tab_as', selected)
    for q in rows:
        if 'piece' in q.get('tab', {}):
            layers.append(polygon(q['tab']['piece'], g.g_to(frame, q['T']),
                                  'tab active-tab' if q['bend'] == owner else 'tab'))
    for k, bend in enumerate(bends, 1):
        local = g.moved(bend['face'], bend['T'])
        bounds = g.bbox(local)
        layers.append(line((bounds[0], 0, 0), (bounds[3], 0, 0),
                           g.g_to(frame, bend['T']), 'bend selected' if k in members else 'bend'))
        c = g.gp_Pnt((bounds[0]+bounds[3])/2, 0, 0).Transformed(g.g_to(frame, bend['T']))
        layers.append(f'<text x="{c.X():.3f}" y="{-c.Y()-3:.3f}">B{k}</text>')
    if p.get('gauging', {}).get('direct') or p.get('gauging',{}).get('contact_mm',0)>0:
        for edge in g.edges(p['loc']):
            try:
                a, b = straight_endpoints(edge)
            except ValueError:
                continue
            if abs(a[1]-p['tip']) < .001 and abs(b[1]-p['tip']) < .001:
                layers.append(line(a, b, g.g_to(frame, p['T']), 'contact' if p.get('gauging',{}).get('direct') else 'cad-edge'))
    layers.extend(refs)
    if changes:layers.append(changes_ui.overlay(changes,frame))
    xs, ys = [x for x, y in points], [-y for x, y in points]
    view = f'{min(xs)-12:.3f} {min(ys)-12:.3f} {max(xs)-min(xs)+24:.3f} {max(ys)-min(ys)+24:.3f}'
    if changes:
        xs.extend([min(xs)-4,max(xs)+4]);ys.extend([min(ys)-4,max(ys)+4])
        view=f'{min(xs)-12:.3f} {min(ys)-12:.3f} {max(xs)-min(xs)+24:.3f} {max(ys)-min(ys)+24:.3f}'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}" role="img" aria-label="Bend {selected} gauging">{"".join(layers)}</svg>'


STYLE = """
*{box-sizing:border-box}body{font:15px system-ui,sans-serif;color:#202631;background:#f5f6f8;margin:24px auto;padding:0 20px;max-width:1300px}
h1{font-size:24px;margin-bottom:6px}p{line-height:1.5}.muted{color:#66717e;font-size:13px}
.layout{display:grid;grid-template-columns:250px minmax(0,1fr);gap:18px;margin-top:20px}
nav button{display:block;width:100%;text-align:left;border:1px solid #dce0e6;border-radius:10px;padding:16px;background:white;margin-bottom:9px;cursor:pointer;color:inherit}
nav button[aria-pressed=true]{border:2px solid #354c73;background:#edf2fa}nav small{display:block;margin-top:6px;font-size:12px}
.panel{background:white;border:1px solid #dce0e6;border-radius:14px;padding:18px;min-width:0}.panel[hidden]{display:none}.panel h2{font-size:18px;margin:0 0 5px}
.fig svg{display:block;width:100%;height:440px}.blank{fill:#dce4eb;stroke:#526579;stroke-width:.45}.plate{fill:#c5bce0;stroke:#6e578f;stroke-width:.5}
.tab{fill:#f7bc72;stroke:#c87916;stroke-width:.35}.active-tab{fill:#fa9c28;stroke-width:.7}.bend{stroke:#c78181;stroke-width:.4;stroke-dasharray:2 1}.selected{stroke:#cb242b;stroke-width:1.1}
.gauge{stroke:#d52f32;stroke-width:.6;stroke-dasharray:3 2}.contact{stroke:#23945d;stroke-width:1.4}svg text{font:4px system-ui;fill:#983035;paint-order:stroke;stroke:white;stroke-width:.7}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:#53606e}.legend span:before{content:'';display:inline-block;width:14px;height:8px;margin-right:5px;background:var(--c)}
.legend .dash:before{height:0;border-top:2px dashed #d52f32;background:none;width:22px}.wire{fill:none;stroke:#344054;stroke-width:.3}.wtab{fill:none;stroke:#ef9425;stroke-width:.8}
details{margin-top:18px;font-size:13px}summary{cursor:pointer}.checks li{margin:8px 0}footer{margin-top:16px}
@media(max-width:700px){.layout{grid-template-columns:1fr}nav{display:flex;gap:6px;overflow:auto}nav button{min-width:145px}.fig svg{height:340px}}
"""


def preview(path, title, blank, tabbed, bends, rows, thickness, notes, iso, step, order=None, operations=None, original_blank=None):
    order = order or list(range(1, len(bends)+1))
    operations=operations or [[n] for n in order]
    frame = display_frame(blank, bends)
    changes=changes_ui.compare_blanks(original_blank,blank)
    buttons, panels = [], []
    for position, members_in_operation in enumerate(operations, 1):
        number=members_in_operation[0]
        label=" + ".join("B"+str(n) for n in members_in_operation)
        heading=f"Bend {number}" if len(members_in_operation)==1 else label
        p = rows[number-1]
        direct = p.get('gauging', {}).get('direct', 'plate' not in p)
        method = ('DIRECT EDGE TRIAL' if p.get('gauging',{}).get('trial_authorized') else 'DIRECT EDGE') if direct else ('BACKBAR OPTION' if p.get('gauging',{}).get('short_contact_candidate') else 'BACKBAR')
        buttons.append(f'<button type="button" data-step="{number}" aria-controls="step-{number}" aria-pressed="{str(position==1).lower()}">{position}. {heading}<small>{method}</small></button>')
        root = p.get('same_plate_as', number)
        members = [q['bend'] for q in rows if q['bend']==root or q.get('same_plate_as')==root]
        contact = 'Use the highlighted part edge.' if direct else 'Use backbar ' + ' / '.join(f'B{i}' for i in members) + '.'
        if len(members_in_operation)>1:contact+=' Common-stroke proposal; form these bend segments together.'
        warnings = ''.join(f'<li>{html.escape(w)}</li>' for w in p.get('warnings', []))
        checks = f'<details class="checks"><summary>Step checks</summary><ul>{warnings}</ul></details>' if warnings else ''
        panels.append(f'<section class="panel" id="step-{number}"{ " hidden" if position>1 else ""}><h2>Step {position} · {heading} · {method}</h2><p class="muted">{contact}</p><div class="fig" data-name="{label} sequence view (display coordinates)">{step_svg(blank,bends,rows,number,frame,members_in_operation,changes)}</div>{checks}</section>')
    checks = []
    if any('ESTIMATED' in n for n in notes):
        checks.append('Estimated flat pattern (K=0.50): verify backbar fit on a real blank.')
    checks.append('Proposed sequence: confirm tooling clearance, backgauge reach and finger engagement.')
    if any('strict' in n.lower() and 'warning' in n.lower() for n in notes):
        checks.append('Source/output surface or edge warnings remain; confirm STEP import in CADMAN-B or SolidWorks.')
    if any(len(group)>1 for group in operations):checks.append('Common operations require compatible fold sense and tooling. Axis/angle checks do not prove a simultaneous stroke.')
    if any(p.get('gauging',{}).get('short_contact_candidate') for p in rows):checks.append('Short contacts are trial candidates. Keep job-specific trial authorization separate from proven finger engagement.')
    safe_title = html.escape(title)
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{safe_title} bend sequence</title><style>{STYLE}{changes_ui.STYLE}.cad-edge{{stroke:#c87916;stroke-width:1.2}}</style></head><body>
<h1>{safe_title} · Bend sequence</h1><p class="muted">{' → '.join('+'.join(f'B{i}' for i in group) for group in operations)} · Blank {thickness:g} mm · Backbar {g.PLATE_T:g} mm</p>
{changes_ui.section(original_blank,blank,changes,frame)}
<div class="layout"><nav aria-label="Bend sequence">{''.join(buttons)}</nav><main>{''.join(panels)}</main></div>
<footer><div class="legend"><span style="--c:#f7bc72">CAD-only tabs</span><span style="--c:#23945d">Direct edge</span><span style="--c:#c5bce0">Backbar</span><span class="dash">Gauge line · {g.TIP_TO_FINGER:g} mm from slot shoulder</span></div>
<p class="muted">Flat layout reference, not a progressive folding simulation. Programming tabs appear in the STEP only; authorised physical changes shown above also apply to the real blank.</p>
<details class="checks"><summary>Trial checks</summary><ul>{''.join('<li>'+html.escape(c)+'</li>' for c in checks)}</ul></details>
<details><summary>Formed part{' with CAD-only programming tabs' if any('piece' in p.get('tab',{}) for p in rows) else ''}</summary>{iso}</details></footer>
<script>(()=>{{const buttons=[...document.querySelectorAll('[data-step]')];for(const button of buttons)button.addEventListener('click',()=>{{for(const b of buttons){{const active=b===button;b.setAttribute('aria-pressed',active);document.getElementById('step-'+b.dataset.step).hidden=!active;}}window.dispatchEvent(new Event('resize'));}});}})();</script>
{g.COMMENT_UI}</body></html>'''
    Path(path).write_text(page, encoding='utf-8')
    return len(page.encode('utf-8'))
