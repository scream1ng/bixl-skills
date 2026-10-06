#!/usr/bin/env python3
"""Stage preview: a numbered multi-view sheet (and optional interactive HTML) covering every spec element."""
import argparse
import base64
import gzip
import json
import mimetypes
import struct
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
INLINE_HTML_LIMIT = 1_000_000
STAGES = ('blockout', 'structure', 'detail')
# Orthographic view directions (from model towards camera) and screen-up vectors.
VIEWS = {'Iso': ([1, -1, 1], [0, 0, 1]), 'Front': ([0, -1, 0], [0, 0, 1]),
         'Right': ([1, 0, 0], [0, 0, 1]), 'Top': ([0, 0, 1], [0, 1, 0])}
# Rotations taking the product's front axis to -Y (the sheet's Front view), keeping Z up for horizontal fronts.
FRONTS = {'-Y': [[1, 0, 0], [0, 1, 0], [0, 0, 1]], '+Y': [[-1, 0, 0], [0, -1, 0], [0, 0, 1]],
          '+X': [[0, 1, 0], [-1, 0, 0], [0, 0, 1]], '-X': [[0, -1, 0], [1, 0, 0], [0, 0, 1]],
          '+Z': [[1, 0, 0], [0, 0, -1], [0, 1, 0]], '-Z': [[1, 0, 0], [0, 0, 1], [0, -1, 0]]}
SKIPPED_AREA_LIMIT = 0.005  # untessellatable faces may total at most 0.5 % of the surface
PALETTE = [(70, 130, 160), (205, 150, 70), (120, 160, 95), (165, 105, 150), (110, 120, 135), (190, 95, 85)]


class Blocked(Exception):
    pass


def triangles(shape, skipped):
    """Tessellate a build123d shape into an (n, 3, 3) triangle array.

    A face the mesher cannot triangulate (e.g. a sliver B-spline) is retried finer, then skipped and
    recorded in `skipped` as (area, total area) so the caller can judge whether the gap matters."""
    try:
        parts = [shape.tessellate(.35, .3)]
    except AttributeError:
        parts = []
        for face in shape.faces():
            for tol in (.35, .05, .01):
                try: parts.append(face.tessellate(tol, .2)); break
                except AttributeError: pass
            else: skipped.append(face.area)
    tris = [np.array([tuple(v) for v in verts], dtype=float)[np.array(faces)] for verts, faces in parts if faces]
    if not tris: raise ValueError('STEP shape could not be tessellated')
    return np.concatenate(tris)


def read_stl(path):
    data = Path(path).read_bytes()
    if len(data) >= 84 and len(data) == 84 + 50 * struct.unpack('<I', data[80:84])[0]:
        rows = np.frombuffer(data[84:], dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]))
        return rows['v'].astype(float)
    verts = [list(map(float, line.split()[1:4])) for line in data.decode(errors='ignore').splitlines()
             if line.strip().startswith('vertex')]
    if not verts or len(verts) % 3: raise ValueError('Unreadable STL: ' + str(path))
    return np.array(verts).reshape(-1, 3, 3)


def load_components(model):
    """Return ([(name, triangles)], skipped face area fraction): one per STEP solid (labelled when named) or one STL mesh."""
    model = Path(model)
    if model.suffix.lower() == '.stl':
        return [(model.stem, read_stl(model))], 0.0
    import build123d as b
    shape = b.import_step(str(model))
    solids = shape.solids() or [shape]
    skipped = []
    components = [(getattr(s, 'label', '') or f'solid_{i + 1}', triangles(s, skipped)) for i, s in enumerate(solids)]
    return components, (sum(skipped) / sum(s.area for s in solids) if skipped else 0.0)


def check_elements(spec, lo, hi, stage):
    """Every element needs an anchor inside the (padded) model bounds; at detail nothing may be pending or unapproved."""
    elements = spec.get('elements') or []
    if not elements: raise Blocked('elements.json has no elements')
    pad = 0.05 * max(float((hi - lo).max()), 1.0)
    problems, seen = [], set()
    for e in elements:
        eid = e.get('id')
        if not eid or eid in seen: problems.append(f'{eid or "?"}: missing or duplicate id'); continue
        seen.add(eid)
        if not e.get('name'): problems.append(f'{eid}: missing name')
        if stage == 'detail' and e.get('approval') not in ('agreed', 'assumed'):
            problems.append(f'{eid}: not approved by the user (approval is {e.get("approval") or "open"})')
        if e.get('status') == 'pending':
            if stage == 'detail': problems.append(f'{eid}: still pending at detail stage')
            continue
        a = e.get('anchor')
        if not (isinstance(a, list) and len(a) == 3):
            problems.append(f'{eid}: missing anchor [x, y, z]'); continue
        if np.any(np.array(a) < lo - pad) or np.any(np.array(a) > hi + pad):
            problems.append(f'{eid}: anchor {a} outside model bounds')
    if problems: raise Blocked('; '.join(problems))
    return elements


def hidden_evidence(element, base):
    """A hidden element needs a "hidden" description and an existing section/detail image the user can see."""
    image = element.get('image')
    if not (element.get('hidden') and image): return False
    p = Path(image) if Path(image).is_absolute() else base / image
    return p.is_file() and (mimetypes.guess_type(p.name)[0] or '').startswith('image/')


def view_frame(name):
    d, up = (np.array(v, dtype=float) for v in VIEWS[name])
    d /= np.linalg.norm(d); right = np.cross(up, d); right /= np.linalg.norm(right)
    return np.array([right, np.cross(d, right), d]).T  # columns: screen x, screen y, depth toward camera


def raster(canvas, depth, tris, color, light):
    h, w = canvas.shape[:2]
    for tri in tris:
        x0 = max(0, int(np.floor(tri[:, 0].min()))); x1 = min(w - 1, int(np.ceil(tri[:, 0].max())))
        y0 = max(0, int(np.floor(tri[:, 1].min()))); y1 = min(h - 1, int(np.ceil(tri[:, 1].max())))
        if x1 < x0 or y1 < y0: continue
        a, b, c = tri; den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-9: continue
        xx, yy = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
        wa = ((b[1] - c[1]) * (xx - c[0]) + (c[0] - b[0]) * (yy - c[1])) / den
        wb = ((c[1] - a[1]) * (xx - c[0]) + (a[0] - c[0]) * (yy - c[1])) / den; wc = 1 - wa - wb
        z = wa * a[2] + wb * b[2] + wc * c[2]; region = depth[y0:y1 + 1, x0:x1 + 1]
        mask = (wa >= -1e-8) & (wb >= -1e-8) & (wc >= -1e-8) & (z > region)
        n = np.cross(b - a, c - a); n[1] = -n[1]; length = np.linalg.norm(n)
        shade = .45 + .55 * abs(n @ light / length) if length else 1
        canvas[y0:y1 + 1, x0:x1 + 1][mask] = np.clip(np.array(color) * shade, 0, 255).astype(np.uint8)
        region[mask] = z[mask]


def sheet(components, elements, lo, hi, out, title):
    """2x2 orthographic views with numbered element callouts and a legend; returns per-element visibility."""
    from PIL import Image, ImageDraw, ImageFont
    tile, legend_w = 620, 560
    font, big = ImageFont.load_default(16), ImageFont.load_default(24)
    centre = (lo + hi) / 2; tol = 0.02 * max(float((hi - lo).max()), 1.0)
    light = np.array([-.3, .6, 1.]); light /= np.linalg.norm(light)
    im = Image.new('RGB', (2 * tile + legend_w, max(2 * tile + 100, 140 + 46 * len(elements))), (243, 245, 247))
    draw = ImageDraw.Draw(im); draw.text((20, 14), title, font=big, fill='#182a35')
    visible = {e['id']: [] for e in elements}
    numbers = {e['id']: i + 1 for i, e in enumerate(elements)}
    for k, name in enumerate(VIEWS):
        frame = view_frame(name)
        proj = {n: (t - centre) @ frame for n, t in components}
        pts = np.concatenate([p.reshape(-1, 3) for p in proj.values()]); plo, phi = pts.min(0), pts.max(0)
        scale = min((tile - 120) / max(phi[0] - plo[0], 1e-6), (tile - 120) / max(phi[1] - plo[1], 1e-6))
        mid = (plo + phi) / 2

        def pixel(p):
            q = np.array(p, dtype=float); q[..., 0] = (q[..., 0] - mid[0]) * scale + tile / 2
            q[..., 1] = tile / 2 + 10 - (q[..., 1] - mid[1]) * scale; q[..., 2] = q[..., 2] * scale
            return q
        canvas = np.full((tile, tile, 3), (243, 245, 247), dtype=np.uint8); depth = np.full((tile, tile), -np.inf)
        for i, (n, _) in enumerate(components):
            raster(canvas, depth, pixel(proj[n]), PALETTE[i % len(PALETTE)], light)
        t = Image.fromarray(canvas); td = ImageDraw.Draw(t); td.text((14, 10), name, font=big, fill='#203746')
        for e in elements:
            if e.get('status') == 'pending': continue
            px, py, pz = pixel((np.array(e['anchor'], dtype=float) - centre) @ frame)
            ix, iy = int(np.clip(px, 0, tile - 1)), int(np.clip(py, 0, tile - 1))
            # Visible only when the anchor lies on the nearest surface; background or edge-on is hidden.
            shown = np.isfinite(depth[iy, ix]) and pz >= depth[iy, ix] - tol * scale
            if shown: visible[e['id']].append(name)
            r = 12; fill = '#c0392b' if shown else None
            td.ellipse((px - r, py - r, px + r, py + r), fill=fill, outline='#c0392b', width=2)
            label = str(numbers[e['id']]); w = td.textlength(label, font=font)
            td.text((px - w / 2, py - 9), label, font=font, fill='white' if shown else '#c0392b')
        im.paste(t, ((k % 2) * tile, 60 + (k // 2) * tile))
    x0, y = 2 * tile + 20, 70
    draw.text((x0, y - 4), 'Elements  (filled = visible, ring = hidden in that view)', font=font, fill='#203746'); y += 30
    for e in elements:
        views = ', '.join(visible[e['id']]) or ('pending' if e.get('status') == 'pending'
                                                 else 'hidden: ' + str(e.get('hidden', 'in all views')))
        draw.text((x0, y), f"{numbers[e['id']]}. {e['id']} {e['name']}", font=font, fill='#182a35')
        draw.text((x0 + 24, y + 19), f"{e.get('value', '')}  [{e.get('source', '?')}]  · {views}"[:70], font=font, fill='#52626e')
        y += 46
    draw.text((20, im.height - 26), 'Review preview · millimetres · not verification evidence', font=font, fill='#52626e')
    im.save(out / 'sheet.png')
    return visible


def compact_mesh(tris, target):
    """Vertex clustering, preserving connected triangles; never stride/drop arbitrary facets."""
    raw = np.asarray(tris, dtype=float).reshape(-1, 3, 3); points = raw.reshape(-1, 3)
    vertices, inverse = np.unique(np.round(points, 4), axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3); cell = max(float(np.ptp(points, axis=0).max()), 1e-6) / 700
    for _ in range(24):
        if len(faces) <= target: break
        keys = np.floor((vertices - points.min(axis=0)) / cell).astype(np.int64)
        _, mapping = np.unique(keys, axis=0, return_inverse=True); mapping = mapping.ravel()
        count = np.bincount(mapping)
        clustered = np.column_stack([np.bincount(mapping, weights=vertices[:, i]) / count for i in range(3)])
        remapped = mapping[faces]
        valid = (remapped[:, 0] != remapped[:, 1]) & (remapped[:, 1] != remapped[:, 2]) & (remapped[:, 0] != remapped[:, 2])
        candidate = remapped[valid]
        if len(candidate):
            _, keep = np.unique(np.sort(candidate, axis=1), axis=0, return_index=True)
            vertices, faces = clustered, candidate[np.sort(keep)]
        cell *= 1.6
    used, mapping = np.unique(faces, return_inverse=True)
    return {'positions': np.round(vertices[used], 3).ravel().tolist(), 'indices': mapping.ravel().tolist()}


def html(components, elements, spec, stage, out):
    """Write the most detailed mesh that keeps the page under INLINE_HTML_LIMIT; returns (bytes, faces)."""
    template = (ROOT / 'assets/preview.html').read_text(); total = sum(len(t) for _, t in components)
    for budget in (120_000, 80_000, 50_000, 30_000, 15_000, 6_000, 2_000):
        meshes = [{'id': n, **compact_mesh(t, max(200, budget * len(t) // total))} for n, t in components]
        scene = {'project': spec.get('project', ''), 'revision': spec.get('revision', ''), 'stage': stage, 'units': 'mm',
                 'components': meshes,
                 'elements': [{k: e.get(k) for k in ('id', 'name', 'value', 'source', 'approval', 'status', 'anchor', 'hidden')} for e in elements]}
        payload = json.dumps(scene, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c').encode()
        encoded = base64.b64encode(gzip.compress(payload, compresslevel=9, mtime=0)).decode('ascii')
        page = template.replace('__SCENE_GZIP_BASE64__', encoded); size = len(page.encode())
        if size < INLINE_HTML_LIMIT: break
    else:
        raise Blocked(f'Inline preview is {size} bytes; must be strictly below {INLINE_HTML_LIMIT}')
    (out / 'preview.html').write_text(page)
    return size, sum(len(m['indices']) // 3 for m in meshes)


def generate(model, elements_path, out, stage='blockout', with_html=False):
    if stage not in STAGES: raise ValueError('stage must be one of ' + ', '.join(STAGES))
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    for stale in ('sheet.png', 'preview.html'): (out / stale).unlink(missing_ok=True)
    spec = json.loads(Path(elements_path).read_text())
    front = spec.get('front', '-Y')
    if front not in FRONTS: raise Blocked(f'front must be one of {", ".join(FRONTS)}, not {front!r}')
    components, skipped = load_components(model)
    if skipped > SKIPPED_AREA_LIMIT:
        raise Blocked(f'{skipped:.1%} of the surface could not be tessellated; repair the model or export STL')
    # Turn the product so its front faces the Front view; anchors are turned with it.
    turn = np.array(FRONTS[front], dtype=float).T
    components = [(n, t @ turn) for n, t in components]
    spec = {**spec, 'elements': [{**e, 'anchor': (np.array(e['anchor'], dtype=float) @ turn).tolist()}
                                 if isinstance(e.get('anchor'), list) and len(e['anchor']) == 3 else e
                                 for e in spec.get('elements') or []]}
    pts = np.concatenate([t.reshape(-1, 3) for _, t in components]); lo, hi = pts.min(0), pts.max(0)
    elements = check_elements(spec, lo, hi, stage)
    title = f"{spec.get('project', Path(model).stem)} · {spec.get('revision', '')} · {stage} · front {front}"
    visible = sheet(components, elements, lo, hi, out, title)
    hidden = [e['id'] for e in elements if not visible[e['id']] and e.get('status') != 'pending']
    unexplained = [k for k in hidden if not hidden_evidence(next(e for e in elements if e['id'] == k), Path(elements_path).parent)]
    if unexplained:
        (out / 'sheet.png').unlink(missing_ok=True)
        raise Blocked(f'hidden in all views without section/detail evidence: {", ".join(unexplained)}; move the anchor '
                      'onto a visible face, or set "image" to an existing section/detail image and describe it in "hidden"')
    result = {'sheet': str((out / 'sheet.png').resolve()), 'elements': len(elements), 'components': len(components),
              'hidden_in_all_views': hidden, 'pending': [e['id'] for e in elements if e.get('status') == 'pending'],
              'skipped_surface': round(skipped, 5)}
    if with_html:
        size, faces = html(components, elements, spec, stage, out)
        result.update(html=str((out / 'preview.html').resolve()), bytes=size, faces=faces)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('model', help='STEP or STL'); p.add_argument('elements', help='elements.json'); p.add_argument('out')
    p.add_argument('--stage', choices=STAGES, default='blockout'); p.add_argument('--html', action='store_true')
    a = p.parse_args()
    try:
        print(json.dumps(generate(a.model, a.elements, a.out, a.stage, a.html), indent=2))
    except Blocked as error:
        print(json.dumps({'blocked': str(error)}, indent=2)); sys.exit(2)
