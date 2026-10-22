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


def edge_samples(edge):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GeomAbs import GeomAbs_Line, GeomAbs_Circle
    c = BRepAdaptor_Curve(edge); a, b = c.FirstParameter(), c.LastParameter()
    n = 2 if c.GetType() == GeomAbs_Line else 16
    pts = [c.Value(a + (b - a) * k / (n - 1)) for k in range(n)]
    kind = 'line' if c.GetType() == GeomAbs_Line else ('arc R%.2f' % c.Circle().Radius() if c.GetType() == GeomAbs_Circle else 'curve')
    length = sum(pts[k].Distance(pts[k + 1]) for k in range(n - 1)) if kind != 'line' else pts[0].Distance(pts[1])
    return pts, kind, length


def edge_status(edge, changes):
    """'trimmed' when the edge borders a physical change region, else 'existing'."""
    for change in changes or []:
        d = g.BRepExtrema_DistShapeShape(edge, change['face']); d.Perform()
        if d.Value() < .005: return 'trimmed' if change['kind'] == 'removed' else 'extended'
    return 'existing'


def edge_in_blank(blank, p, edge):
    k = [x.IsSame(edge) for x in g.edges(p['loc'])].index(True)
    return g.edges(blank)[k]


def visual_layer(p, frame, number, changes, rows):
    """Pictures instead of sentences: finger, gauge dimension, clear zone, trial and plate badges."""
    T = g.g_to(frame, p['T']); out = []
    def P(x, y):
        q = g.gp_Pnt(x, y, 0).Transformed(T); return q.X(), -q.Y()
    def poly(pts, css):
        return '<polygon class="%s" points="%s"/>' % (css, ' '.join('%.2f,%.2f' % P(x, y) for x, y in pts))
    def text(x, y, s, css='vlabel', size=3.8, dx=0.):
        X, Y = P(x, y); X += dx; w = .58 * size * len(s) + 2
        return (f'<g class="lbl {css}"><rect x="{X-w/2:.2f}" y="{Y-size*.8-1:.2f}" width="{w:.2f}" height="{size+1.6:.2f}" rx="1.2"/>'
                f'<text x="{X:.2f}" y="{Y:.2f}" style="font-size:{size}px">{html.escape(s)}</text></g>')
    tip = p['tip']; direct = p.get('gauging', {}).get('direct')
    if direct:
        xs = [x for e in g.edges(p['loc']) if _on_tip(e, tip) for x, _, _ in g.pts(e)]
        cx = (min(xs) + max(xs)) / 2 if xs else 0
        if p.get('gauging', {}).get('trial_authorized'):
            out.append(text(cx, tip+5, f"TRIAL · {p['gauging'].get('contact_mm',0):.0f} mm contact", 'trial', 3.6))
        beyond = g.BRepAlgoAPI_Common(p['loc'], g.rect(-1e4, tip+.01, 1e4, 1e4)).Shape()
        for f in g.faces(beyond):
            if g.area(f) < 1: continue
            out.append(changes_ui.polygon(f, T, 'clearzone'))
            b = g.bbox(f); out.append(text((b[0]+b[3])/2, b[4]-6, 'keep fingers clear', 'warnlabel', 3.8))
    else:
        cx = p['cx']; f0 = tip + g.TIP_TO_FINGER
        shared = [q['bend'] for q in rows if q.get('same_plate_as') == p.get('same_plate_as', p['bend']) or q['bend'] == p.get('same_plate_as', p['bend'])]
        out.append(text(cx, tip+g.TIP_TO_FINGER/2, 'PLATE ' + '/'.join(f'B{n}' for n in sorted(shared)), 'platelabel', 5))
    # gauge dimension from bend line to gauge line
    dx = cx + (9 if direct else 30)
    (x0, y0), (x1, y1) = P(dx, 0), P(dx, tip)
    out.append(f'<line class="gdim" x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" marker-start="url(#arr)" marker-end="url(#arr)"/>')
    out.append(text(dx, tip/2, f'{tip:.2f} mm', 'dimlabel', 4.4))
    return ''.join(out)


def pick_layer(blank, p, frame, bend_no, changes):
    """Invisible wide strokes so a comment pin records which real edge was clicked."""
    to_disp = g.g_to(frame, p['T']); out = []
    loc_edges = g.edges(p['loc'])
    for k, (e0, e) in enumerate(zip(g.edges(blank), loc_edges), 1):
        pts, kind, length = edge_samples(e)
        disp = [q.Transformed(to_disp) for q in pts]
        d = 'M' + ' L'.join(f'{q.X():.3f},{-q.Y():.3f}' for q in disp)
        attrs = f'data-edge="E{k}" data-kind="{kind}" data-len="{length:.2f}" data-status="{edge_status(e0, changes)}"'
        if kind == 'line':
            dx, dy = pts[1].X() - pts[0].X(), pts[1].Y() - pts[0].Y()
            ang = abs(math.degrees(math.atan2(dy, dx))) % 180; ang = min(ang, 180 - ang)
            attrs += f' data-angle="{ang:.3f}" data-bend="B{bend_no}"'
            if ang < 5: attrs += f' data-dist="{(pts[0].Y() + pts[1].Y()) / 2:.2f}"'
        out.append(f'<path class="pick" {attrs} d="{d}"/>')
    return '<g class="picks">' + ''.join(out) + '</g>'


def step_svg(blank, bends, rows, selected, frame, members=None, changes=None, done=(), picks=True):
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
        layers.append(polygon(p['plate'], transform, 'plate').replace('<path ', f'<path data-label="Backbar plate {p.get("dxf","")}" ',1))
        refs.append(line((p['cx']-g.PLATE_W/2, p['tip'], 0),
                         (p['cx']+g.PLATE_W/2, p['tip'], 0), transform, 'gauge'))
    layers.append(polygon(blank, frame, 'blank'))
    owner = p.get('tab', {}).get('same_tab_as', selected)
    for q in rows:
        if 'piece' in q.get('tab', {}):
            layers.append(polygon(q['tab']['piece'], g.g_to(frame, q['T']),
                                  'tab active-tab' if q['bend'] == owner else 'tab').replace('<path ', f'<path data-label="CAD-only programming tab for B{q["bend"]} (not on the real blank)" ',1))
    badges = []
    for k, bend in enumerate(bends, 1):
        local = g.moved(bend['face'], bend['T'])
        bounds = g.bbox(local)
        css = 'bend selected' if k in members else ('bend done' if k in done else 'bend')
        layers.append(line((bounds[0], 0, 0), (bounds[3], 0, 0), g.g_to(frame, bend['T']), css))
        c = g.gp_Pnt((bounds[0]+bounds[3])/2, 0, 0).Transformed(g.g_to(frame, bend['T']))
        ang = bend.get('angle_deg')
        txt = f'B{k}' + (f' {ang:.0f}°' if ang is not None else '') + (' ✓' if k in done else '')
        cls = 'badge now' if k in members else ('badge done' if k in done else 'badge')
        w = 2.6 * len(txt) + 3
        badges.append(f'<g class="{cls}"><rect x="{c.X()-w/2:.2f}" y="{-c.Y()-11:.2f}" width="{w:.2f}" height="7" rx="3.5"/><text x="{c.X():.2f}" y="{-c.Y()-6.2:.2f}">{html.escape(txt)}</text></g>')
    if p.get('gauging', {}).get('direct') or p.get('gauging',{}).get('contact_mm',0)>0:
        for edge in g.edges(p['loc']):
            try:
                a, b = straight_endpoints(edge)
            except ValueError:
                continue
            if abs(a[1]-p['tip']) < .001 and abs(b[1]-p['tip']) < .001:
                trimmed = edge_status(edge_in_blank(blank, p, edge), changes) != 'existing'
                layers.append(line(a, b, g.g_to(frame, p['T']), ('contact-trimmed' if trimmed else 'contact') if p.get('gauging',{}).get('direct') else 'cad-edge'))
    layers.extend(refs)
    if changes:layers.append(changes_ui.overlay(changes,frame))
    layers.append(visual_layer(p, frame, selected, changes, rows))
    layers.extend(badges)
    if picks:layers.append(pick_layer(blank, p, frame, selected, changes))
    xs, ys = [x for x, y in points], [-y for x, y in points]
    view = f'{min(xs)-12:.3f} {min(ys)-12:.3f} {max(xs)-min(xs)+24:.3f} {max(ys)-min(ys)+24:.3f}'
    if changes:
        xs.extend([min(xs)-4,max(xs)+4]);ys.extend([min(ys)-4,max(ys)+4])
        view=f'{min(xs)-12:.3f} {min(ys)-12:.3f} {max(xs)-min(xs)+24:.3f} {max(ys)-min(ys)+24:.3f}'
    defs = '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0L10,5L0,10z" fill="#1f3a5f"/></marker><pattern id="hatch" width="2.5" height="2.5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="2.5" height="2.5" fill="#fde3df"/><line x1="0" y1="0" x2="0" y2="2.5" stroke="#d6453a" stroke-width=".7"/></pattern></defs>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}" role="img" aria-label="Bend {selected} gauging">{defs}{"".join(layers)}</svg>'


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
.chip{display:inline-block;margin:6px 6px 0 0;padding:3px 9px;border-radius:99px;font-size:12px;border:1px solid}.chip.ok{background:#e7f6ee;border-color:#8fcca9;color:#17663f}.chip.warn{background:#fdecea;border-color:#e59a92;color:#9b2a20}.chip.plate{background:#f1eefa;border-color:#b9acdb;color:#4f3d7a}.chip.info{background:#f4f5f7;border-color:#cfd5dc;color:#4b5563}
.banner{border-radius:10px;padding:12px 16px;margin:14px 0;font-size:14px}.banner.ok{background:#e7f6ee;border:1px solid #8fcca9;color:#17532f}.banner.warn{background:#fdecea;border:1px solid #e59a92;color:#7d2219}
.contact-trimmed{stroke:#be362c;stroke-width:1.8}.bend.done{stroke:#5b6b7b;stroke-width:.9;stroke-dasharray:none}
.badge rect{fill:#fff;stroke:#9aa5b1;stroke-width:.3}.badge text{font:600 4.2px system-ui;fill:#334;text-anchor:middle;stroke:none}.badge.done rect{fill:#5b6b7b;stroke:#5b6b7b}.badge.done text{fill:#fff}.badge.now rect{fill:#cb242b;stroke:#cb242b}.badge.now text{fill:#fff}
.finger{fill:#1f3a5f}.gdim{stroke:#1f3a5f;stroke-width:.35}.lbl text{font-family:system-ui;font-weight:700;text-anchor:middle;stroke:none;fill:#1f3a5f}.lbl rect{fill:#fff;stroke:#c9d2dc;stroke-width:.25}
.lbl.fingertxt rect{fill:none;stroke:none}.lbl.fingertxt text{fill:#fff}.lbl.trial rect{fill:#fff4e5;stroke:#e3a24a}.lbl.trial text{fill:#9a4a05}.lbl.dimlabel rect{fill:#1f3a5f;stroke:none}.lbl.dimlabel text{fill:#fff}
.clearzone{fill:url(#hatch);stroke:#d6453a;stroke-width:.3}.lbl.warnlabel rect{fill:#fff;stroke:#d6453a}.lbl.warnlabel text{fill:#b3261e}.lbl.platelabel rect{fill:none;stroke:none}.lbl.platelabel text{fill:#4f3d7a}
nav .num{display:inline-grid;place-items:center;width:22px;height:22px;border-radius:50%;background:#354c73;color:#fff;font-size:12px;margin-right:4px}nav .thumb svg{display:block;width:100%;height:70px;margin-top:8px}nav .thumb text,nav .thumb .badge,nav .thumb .lbl,nav .thumb .gdim{display:none}
.m-direct{color:#17663f;font-weight:600}.m-trial{color:#b45309;font-weight:600}.m-plate{color:#4f3d7a;font-weight:600}.m-trim{color:#b3261e;font-weight:700}
.pick{fill:none;stroke:transparent;stroke-width:2.6;pointer-events:none}body.commenting .pick{pointer-events:stroke;cursor:pointer}body.commenting .pick:hover{stroke:#2f7de1;stroke-opacity:.55}
details{margin-top:18px;font-size:13px}summary{cursor:pointer}.checks li{margin:8px 0}footer{margin-top:16px}
@media(max-width:700px){.layout{grid-template-columns:1fr}nav{display:flex;gap:6px;overflow:auto}nav button{min-width:145px}.fig svg{height:340px}}
"""


def _on_tip(edge, tip):
    try:a, b = straight_endpoints(edge)
    except ValueError:return False
    return abs(a[1]-tip) < .001 and abs(b[1]-tip) < .001


def contact_status(blank, p, changes):
    """'existing', 'trimmed' or 'extended' for the edge a direct-gauged bend touches."""
    status = 'existing'
    for e in g.edges(p['loc']):
        if _on_tip(e, p['tip']):
            st = edge_status(edge_in_blank(blank, p, e), changes)
            if st != 'existing': status = st
    return status


def method_name(blank, p, changes):
    gauge = p.get('gauging', {})
    if gauge.get('direct', 'plate' not in p):
        base = 'DIRECT EDGE' if contact_status(blank, p, changes) == 'existing' else 'TRIM EDGE'
        return base + (' TRIAL' if gauge.get('trial_authorized') else '')
    return 'BACKBAR OPTION' if gauge.get('short_contact_candidate') else 'BACKBAR'


def banner(changes):
    if not changes:
        return '<div class="banner ok"><b>Physical blank: UNCHANGED.</b> No trims or extensions. Every gauge edge is an existing edge of the part as drawn; orange tabs exist only in the programming STEP.</div>'
    return f'<div class="banner warn"><b>Physical blank: {len(changes)} CHANGE(S).</b> The real laser blank differs from the original drawing — see “Physical part changes” below the bend sequence.</div>'


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
        method = method_name(blank, p, changes)
        done = {n for grp in operations[:position-1] for n in grp}
        angle = bends[number-1].get('angle_deg')
        mcls = 'm-trim' if 'TRIM' in method else 'm-trial' if 'TRIAL' in method else ('m-direct' if direct else 'm-plate')
        buttons.append(f'<button type="button" data-step="{number}" aria-controls="step-{number}" aria-pressed="{str(position==1).lower()}"><span class="num">{position}</span> {heading}{f" · {angle:.0f}°" if angle is not None else ""}<small class="{mcls}">{method}</small></button>')
        root = p.get('same_plate_as', number)
        members = [q['bend'] for q in rows if q['bend']==root or q.get('same_plate_as')==root]
        contact = 'Use the highlighted part edge.' if direct else 'Use backbar ' + ' / '.join(f'B{i}' for i in members) + '.'
        chips = []
        gauge = p.get('gauging', {})
        if direct:
            status = contact_status(blank, p, changes)
            if status == 'existing':
                chips.append(f'<span class="chip ok">Existing part edge · no trim · {gauge.get("contact_mm",0):.1f} mm contact · parallel</span>')
            else:
                chips.append(f'<span class="chip warn">{"Trimmed" if status=="trimmed" else "Extended"} edge · real blank changed · {gauge.get("contact_mm",0):.1f} mm contact · parallel</span>')
        else:
            chips.append('<span class="chip plate">Backbar pocket follows the real blank · no trim</span>' if not changes else '<span class="chip plate">Backbar pocket follows the revised blank</span>')
        for near in gauge.get('near_edges', []):
            if .01 <= near['angle_deg'] < 2 and near['length_mm'] >= 2:
                chips.append(f'<span class="chip info">Nearby edge {near["length_mm"]:.1f} mm is {near["angle_deg"]:.2f}° off parallel · not used · not trimmed</span>')
        contact += '<br>' + ' '.join(chips)
        if len(members_in_operation)>1:contact+=' Common-stroke proposal; form these bend segments together.'
        warnings = ''.join(f'<li>{html.escape(w)}</li>' for w in p.get('warnings', []))
        checks = f'<details class="checks"><summary>Step checks</summary><ul>{warnings}</ul></details>' if warnings else ''
        panels.append(f'<section class="panel" id="step-{number}"{ " hidden" if position>1 else ""}><h2>Step {position} · {heading} · {method}</h2><p class="muted">{contact}</p><div class="fig" data-name="{label} sequence view (display coordinates)">{step_svg(blank,bends,rows,number,frame,members_in_operation,changes,done)}</div>{checks}</section>')
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
{banner(changes)}
<div class="layout"><nav aria-label="Bend sequence">{''.join(buttons)}</nav><main>{''.join(panels)}</main></div>
{changes_ui.section(original_blank,blank,changes,frame)}
<footer><div class="legend"><span style="--c:#f7bc72">CAD-only tabs</span><span style="--c:#23945d">Direct edge (existing)</span><span style="--c:#be362c">Trimmed edge (real blank changed)</span><span style="--c:repeating-linear-gradient(45deg,#d6453a 0 2px,#fde3df 2px 5px)">Keep fingers clear</span><span style="--c:#5b6b7b">Already bent ✓</span><span style="--c:#c5bce0">Backbar</span><span class="dash">Gauge line · {g.TIP_TO_FINGER:g} mm from slot shoulder</span></div>
<p class="muted">Flat layout reference, not a progressive folding simulation. Programming tabs appear in the STEP only; authorised physical changes shown above also apply to the real blank.</p>
<details class="checks"><summary>Trial checks</summary><ul>{''.join('<li>'+html.escape(c)+'</li>' for c in checks)}</ul></details>
<details><summary>Formed part{' with CAD-only programming tabs' if any('piece' in p.get('tab',{}) for p in rows) else ''}</summary>{iso}</details></footer>
<script>(()=>{{const buttons=[...document.querySelectorAll('[data-step]')];for(const button of buttons)button.addEventListener('click',()=>{{for(const b of buttons){{const active=b===button;b.setAttribute('aria-pressed',active);document.getElementById('step-'+b.dataset.step).hidden=!active;}}window.dispatchEvent(new Event('resize'));}});}})();</script>
{g.COMMENT_UI}</body></html>'''
    Path(path).write_text(page, encoding='utf-8')
    return len(page.encode('utf-8'))
