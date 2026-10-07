#!/usr/bin/env python3
"""Stage preview: a numbered multi-view sheet, optional interactive HTML, and optional draft pictures
(clean shaded views and one framed snapshot per element) covering every spec element."""
import argparse
import base64
import gzip
import json
import mimetypes
import re
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
# Draft pictures: same component colour order as the 3D viewer, so a part looks the same in both.
DRAFT_COLORS = [(189, 189, 189), (227, 24, 55), (119, 119, 119), (238, 238, 238), (51, 51, 51), (155, 16, 40)]
DRAFT_BG = (250, 250, 250)
# Camera directions (model towards camera) tried for an element snapshot; the whole-part views use the first five.
DRAFT_DIRS = {'iso': [1, -1, 1], 'front': [0, -1, 0], 'rear': [0, 1, 0], 'right': [1, 0, 0], 'top': [0, 0, 1],
              'iso-left': [-1, -1, 1], 'left': [-1, 0, 0], 'rear-iso': [-1, 1, 1], 'rear-iso-right': [1, 1, 1],
              'under': [0, 0, -1], 'under-front': [1, -1, -1], 'under-front-left': [-1, -1, -1],
              'under-rear': [-1, 1, -1], 'under-rear-right': [1, 1, -1]}
DRAFT_VIEWS = ('iso', 'front', 'rear', 'right', 'top')


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
    if not model.is_file(): raise Blocked(f'model not found: {model}')
    if model.suffix.lower() == '.stl':
        return [(model.stem, read_stl(model))], 0.0
    import build123d as b
    shape = b.import_step(str(model))
    solids = shape.solids() or [shape]
    skipped = []
    components, used = [], set()
    for i, s in enumerate(solids):
        # STEP labels can repeat; every consumer keys components by name, so make them unique.
        name = base = getattr(s, 'label', '') or f'solid_{i + 1}'; k = 2
        while name in used: name = f'{base}_{k}'; k += 1
        used.add(name); components.append((name, triangles(s, skipped)))
    return components,(sum(skipped) / sum(s.area for s in solids) if skipped else 0.0)


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
        # Same rule as board.py; the id also names the snapshot file.
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', str(eid)): problems.append(f'{eid}: id must be HTML-safe (letter, then letters, digits, _ or -)')
        if not e.get('name'): problems.append(f'{eid}: missing name')
        if stage == 'detail' and e.get('approval') not in ('agreed', 'assumed'):
            problems.append(f'{eid}: not approved by the user (approval is {e.get("approval") or "open"})')
        if e.get('status') == 'pending':
            if stage == 'detail': problems.append(f'{eid}: still pending at detail stage')
            continue
        a = e.get('anchor')
        if not (isinstance(a, list) and len(a) == 3):
            problems.append(f'{eid}: missing anchor [x, y, z]'); continue
        try: point = np.array(a, dtype=float)
        except (TypeError, ValueError): point = np.full(3, np.nan)
        if not np.all(np.isfinite(point)):
            problems.append(f'{eid}: anchor {a} must be three finite numbers'); continue
        if np.any(point < lo - pad) or np.any(point > hi + pad):
            problems.append(f'{eid}: anchor {a} outside model bounds')
    if problems: raise Blocked('; '.join(problems))
    return elements


def surface_at(components, point):
    """Distance from `point` to the nearest mesh triangle, that triangle's outward unit normal, and the nearest point."""
    t = np.concatenate([tris for _, tris in components]); a, b, c = t[:, 0], t[:, 1], t[:, 2]
    n = np.cross(b - a, c - a); length = np.linalg.norm(n, axis=1); ok = length > 1e-12
    a, b, c, n = a[ok], b[ok], c[ok], n[ok] / length[ok, None]
    p = np.asarray(point, dtype=float); off = np.einsum('ij,ij->i', p - a, n); q = p - off[:, None] * n
    inside = np.ones(len(a), dtype=bool); edge = np.full(len(a), np.inf); near = q.copy()
    for u, v in ((a, b), (b, c), (c, a)):
        e = v - u; inside &= np.einsum('ij,ij->i', np.cross(e, q - u), n) >= 0
        k = np.clip(np.einsum('ij,ij->i', p - u, e) / np.maximum(np.einsum('ij,ij->i', e, e), 1e-12), 0, 1)
        w = u + k[:, None] * e; dist = np.linalg.norm(p - w, axis=1); closer = dist < edge
        edge = np.where(closer, dist, edge); near[closer] = w[closer]
    d = np.where(inside, np.abs(off), edge); i = int(np.argmin(d))
    return float(d[i]), n[i], (q[i] if inside[i] else near[i])


def on_top(depth, ix, iy, z, slack):
    """Whether depth `z` (pixels) is on the nearest surface around pixel (ix, iy), within `slack` pixels.

    A 3 x 3 neighbourhood keeps a rim or sloped face visible; a wall in front of the point still hides it."""
    d = depth[max(iy - 1, 0):iy + 2, max(ix - 1, 0):ix + 2]; d = d[np.isfinite(d)]
    return d.size > 0 and bool((z >= d - slack).any())


def hidden_evidence(element, base):
    """A hidden element needs a "hidden" description and an existing section/detail image the user can see."""
    image = element.get('image')
    # A filled draft snapshot is replaced or cleared on this run; it is not a section the user can rely on.
    if not (element.get('hidden') and image) or element.get('image_auto'): return False
    p = Path(image) if Path(image).is_absolute() else base / image
    return p.is_file() and (mimetypes.guess_type(p.name)[0] or '').startswith('image/')


def view_frame(name):
    d, up = (np.array(v, dtype=float) for v in VIEWS[name])
    d /= np.linalg.norm(d); right = np.cross(up, d); right /= np.linalg.norm(right)
    return np.array([right, np.cross(d, right), d]).T  # columns: screen x, screen y, depth toward camera


def raster(canvas, depth, tris, color, light, shades=None):
    """Flat shading by default; `shades` (n, 3) gives one brightness per corner and is interpolated across the triangle."""
    h, w = canvas.shape[:2]
    for index, tri in enumerate(tris):
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
        if shades is None:
            n = np.cross(b - a, c - a); n[1] = -n[1]; length = np.linalg.norm(n)
            shade = .45 + .55 * abs(n @ light / length) if length else 1
            canvas[y0:y1 + 1, x0:x1 + 1][mask] = np.clip(np.array(color) * shade, 0, 255).astype(np.uint8)
        else:
            sa, sb, sc = shades[index]; shade = (wa * sa + wb * sb + wc * sc)[mask]
            canvas[y0:y1 + 1, x0:x1 + 1][mask] = np.clip(np.array(color) * shade[:, None], 0, 255).astype(np.uint8)
        region[mask] = z[mask]


def sheet(components, elements, lo, hi, out, title):
    """2x2 orthographic views with numbered element callouts and a legend; returns per-element visibility."""
    from PIL import Image, ImageDraw, ImageFont
    tile, legend_w = 620, 560
    # CAD labels contain diameter, multiplication and dash glyphs absent from Pillow's default font.
    for family in ('DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                   'Arial.ttf', '/System/Library/Fonts/Supplemental/Arial.ttf', 'C:/Windows/Fonts/arial.ttf'):
        try:
            font, big = ImageFont.truetype(family, 14), ImageFont.truetype(family, 23)
            break
        except OSError:
            continue
    else:
        # Pillow's built-in font still works; only some glyphs (Ø, ×, –) may show as boxes.
        print('warning: DejaVu Sans/Arial not found; using Pillow default font', file=sys.stderr)
        font, big = ImageFont.load_default(14), ImageFont.load_default(23)
    centre = (lo + hi) / 2; tol = max(0.5, 0.005 * float((hi - lo).max()))
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
            shown = on_top(depth, ix, iy, pz, tol * scale + 1.5)
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
                                                 else 'hidden: ' + str(e.get('hidden', 'not in these views')))
        draw.text((x0, y), f"{numbers[e['id']]}. {e['id']} {e['name']}", font=font, fill='#182a35')
        draw.text((x0 + 24, y + 19), f"{e.get('value', '')}  [{e.get('source', '?')}]"[:40] + f"  · {views}"[:60], font=font, fill='#52626e')
        y += 46
    draw.text((20, im.height - 26), 'Review preview · millimetres · not verification evidence', font=font, fill='#52626e')
    im.save(out / 'sheet.png')
    return visible


def draft_frame(direction):
    d = np.array(direction, dtype=float); d /= np.linalg.norm(d)
    up = np.array([0., 1., 0.]) if abs(d[2]) > .95 else np.array([0., 0., 1.])
    right = np.cross(up, d); right /= np.linalg.norm(right)
    return np.array([right, np.cross(d, right), d]).T


def corner_normals(tris, crease_deg=35.0):
    """Unit normal per triangle corner: averaged over the vertex on smooth surfaces, the face normal across a crease."""
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]); area = np.linalg.norm(n, axis=1, keepdims=True)
    face = n / np.maximum(area, 1e-12)
    _, index = np.unique(np.round(tris.reshape(-1, 3), 4), axis=0, return_inverse=True); index = index.ravel()
    total = np.zeros((index.max() + 1, 3)); np.add.at(total, index, np.repeat(n, 3, axis=0))      # area-weighted
    vertex = (total / np.maximum(np.linalg.norm(total, axis=1, keepdims=True), 1e-12))[index].reshape(-1, 3, 3)
    smooth = np.einsum('tcj,tj->tc', vertex, face) > np.cos(np.radians(crease_deg))
    return np.where(smooth[..., None], vertex, face[:, None, :])


def draft_render(components, frame, centre, mid, half_width, size, supersample=2):
    """One clean shaded orthographic picture: a window `2 * half_width` model units wide centred on screen point `mid`.

    Returns (image array at `size`, depth buffer, pixels per model unit) with the buffers at the supersampled size."""
    w, h = size[0] * supersample, size[1] * supersample; scale = w / (2 * half_width)
    canvas = np.full((h, w, 3), DRAFT_BG, dtype=np.uint8); depth = np.full((h, w), -np.inf)
    light = np.array([-.3, .6, 1.]); light /= np.linalg.norm(light)
    for i, (name, tris) in enumerate(components):
        if name not in _NORMALS: _NORMALS[name] = corner_normals(tris)
        q = (tris - centre) @ frame; p = np.empty_like(q)
        p[..., 0] = (q[..., 0] - mid[0]) * scale + w / 2; p[..., 1] = h / 2 - (q[..., 1] - mid[1]) * scale; p[..., 2] = q[..., 2] * scale
        inside = (p[..., 0].max(1) >= 0) & (p[..., 0].min(1) <= w) & (p[..., 1].max(1) >= 0) & (p[..., 1].min(1) <= h)
        shades = .45 + .55 * np.abs((_NORMALS[name][inside] @ frame) @ light)
        raster(canvas, depth, p[inside], DRAFT_COLORS[i % len(DRAFT_COLORS)], light, shades)
    # Outline silhouettes and steps: flat shading alone merges parallel faces at different depths.
    d = np.where(np.isfinite(depth), depth, -1e9); edge = np.zeros(d.shape, dtype=bool); jump = 3.0 * supersample
    edge[:, 1:] |= np.abs(d[:, 1:] - d[:, :-1]) > jump; edge[1:, :] |= np.abs(d[1:, :] - d[:-1, :]) > jump
    canvas[edge] = (canvas[edge] * .35).astype(np.uint8)
    return canvas, depth, scale


_NORMALS = {}


def snapshots(components, elements, lo, hi, out, normals=None, keep=()):
    """Draft pictures for the board, seconds each: whole-part views and one framed snapshot per element.

    An element is shown from the first direction, nearest the outward normal at its anchor (else its side of the
    part), in which its anchor is on the visible surface. Paths in `keep` (the user's own images) are never touched. Its window is `frame` model units wide when the element sets one, otherwise half of the part.
    Returns ({view: path}, {element id: (path, direction)}, [ids no direction can show])."""
    from PIL import Image
    centre = (lo + hi) / 2; extent = max(float((hi - lo).max()), 1e-6); tol = max(0.5, 0.005 * extent); _NORMALS.clear()
    keep = {Path(k).resolve() for k in keep}
    for sub in ('views', 'elements'): (out / sub).mkdir(parents=True, exist_ok=True)
    # Remove only this run's own outputs; other images kept in these folders stay.
    for old in [out / 'views' / f'{v}.jpg' for v in DRAFT_VIEWS] + [out / 'elements' / f"{e['id']}.jpg" for e in elements]:
        if old.resolve() not in keep: old.unlink(missing_ok=True)
    corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])

    def fit(frame, aspect):
        q = (corners - centre) @ frame; a, b = q.min(0), q.max(0)
        return (a[:2] + b[:2]) / 2, max((b[0] - a[0]) / 2, (b[1] - a[1]) / 2 * aspect) * 1.06

    def save(canvas, size, path):
        Image.fromarray(canvas).resize(size, Image.LANCZOS).save(path, quality=80, optimize=True)   # small enough for a 1 MB board

    views = {}
    for name in DRAFT_VIEWS:
        size = (1000, 760); frame = draft_frame(DRAFT_DIRS[name]); mid, half = fit(frame, size[0] / size[1])
        save(draft_render(components, frame, centre, mid, half, size)[0], size, out / 'views' / f'{name}.jpg')
        views[name] = str((out / 'views' / f'{name}.jpg').resolve())
    probes = {}

    def shown(name, anchor):
        if name not in probes:
            frame = draft_frame(DRAFT_DIRS[name]); mid, half = fit(frame, 1.0)
            probes[name] = (frame, mid, *draft_render(components, frame, centre, mid, half, (420, 420), 1)[1:])
        frame, mid, depth, scale = probes[name]; q = (anchor - centre) @ frame
        ix, iy = int(round((q[0] - mid[0]) * scale + 210)), int(round(210 - (q[1] - mid[1]) * scale))
        return 0 <= ix < 420 and 0 <= iy < 420 and on_top(depth, ix, iy, q[2] * scale, tol * scale + 1.5)

    made, missing = {}, []
    for e in elements:
        if e.get('status') == 'pending' or not (isinstance(e.get('anchor'), list) and len(e['anchor']) == 3): continue
        anchor = np.array(e['anchor'], dtype=float)
        side = (normals or {}).get(e['id'], anchor - centre); length = np.linalg.norm(side)
        # Facing the element's surface; an oblique view shows more form than a square-on one.
        def score(k):
            v = np.array(DRAFT_DIRS[k], dtype=float)
            return (float(v @ side) / (np.linalg.norm(v) * length) if length > 1e-9 else 0.) + (.45 if np.count_nonzero(v) == 3 else 0.)
        order = sorted(DRAFT_DIRS, key=lambda k: -score(k))
        name = next((k for k in order if shown(k, anchor)), None)
        if name is None:
            missing.append(e['id']); continue
        size = (640, 480); frame = draft_frame(DRAFT_DIRS[name]); width = float(e.get('frame') or 0.5 * extent)
        path = out / 'elements' / f"{e['id']}.jpg"
        if path.resolve() in keep: continue   # the user's own picture already has this name
        # A window as wide as the part shows the whole part: centre on the part and widen to fit its projection.
        if width >= extent:
            mid, half = fit(frame, size[0] / size[1]); half = max(half, width / 2)
        else:
            mid, half = ((anchor - centre) @ frame)[:2], width / 2
        save(draft_render(components, frame, centre, mid, half, size)[0], size, path)
        made[e['id']] = (str(path.resolve()), name)
    return views, made, missing


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


def byte_planes(values, width):
    """Little-endian integers as `width` separate byte planes; gzip compresses planes far better than packed ints."""
    return np.asarray(values, dtype='<u4').view(np.uint8).reshape(-1, 4)[:, :width].T.tobytes()


def pack_meshes(meshes):
    """Binary viewer meshes, about half the size of JSON at the same detail (decoded in assets/preview.html).

    Positions are 16-bit steps across the model box (box/65535, far below a viewer pixel). Vertices are renumbered by
    first use, so each index is stored as its distance back from the newest vertex (0 = next new vertex)."""
    pts = np.concatenate([np.asarray(m['positions'], dtype=float).reshape(-1, 3) for m in meshes])
    origin = pts.min(0); span = pts.max(0) - origin; step = np.where(span > 0, span / 65535, 1.0)
    info, blob = [], b''
    for m in meshes:
        p = np.asarray(m['positions'], dtype=float).reshape(-1, 3); faces = np.asarray(m['indices'], dtype=np.int64)
        _, first = np.unique(faces, return_index=True); used = faces[np.sort(first)]
        renumber = np.empty(len(p), dtype=np.int64); renumber[used] = np.arange(len(used)); index = renumber[faces]
        newest = np.maximum.accumulate(np.concatenate([[-1], index[:-1]]))
        back = newest + 1 - index
        if back.max(initial=0) >= 1 << 24: raise Blocked('viewer mesh too large to pack')
        q = np.round((p[used] - origin) / step).astype(np.int64)
        blob += byte_planes(q.T.ravel(), 2) + byte_planes(back, 3)
        info.append({'id': m['id'], 'vertices': len(used), 'faces': len(faces) // 3})
    return info, origin.round(6).tolist(), step.tolist(), blob


def html(components, elements, spec, stage, out, unturn=np.eye(3), limit=INLINE_HTML_LIMIT):
    """Write the most detailed mesh that keeps the page under `limit` bytes; returns (bytes, faces).

    `unturn` maps viewer coordinates back to the model's own frame for exported comment positions."""
    template = (ROOT / 'assets/preview.html').read_text(); total = sum(len(t) for _, t in components)
    for budget in (120_000, 80_000, 50_000, 30_000, 15_000, 6_000, 2_000):
        info, origin, step, blob = pack_meshes([{'id': n, **compact_mesh(t, max(200, budget * len(t) // total))} for n, t in components])
        scene = {'project': spec.get('project', ''), 'revision': spec.get('revision', ''), 'stage': stage, 'units': 'mm',
                 'components': info, 'origin': origin, 'step': step, 'unturn': np.asarray(unturn).tolist(),
                 'elements': [{k: e.get(k) for k in ('id', 'name', 'value', 'source', 'approval', 'status', 'anchor', 'hidden')} for e in elements]}
        header = json.dumps(scene, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c').encode()
        payload = struct.pack('<I', len(header)) + header + blob
        encoded = base64.b64encode(gzip.compress(payload, compresslevel=9, mtime=0)).decode('ascii')
        page = template.replace('__SCENE_GZIP_BASE64__', encoded); size = len(page.encode())
        if size < limit: break
    else:
        raise Blocked(f'Inline preview is {size} bytes; must be strictly below {limit}')
    (out / 'preview.html').write_text(page)
    return size, sum(c['faces'] for c in info)


def generate(model, elements_path, out, stage='blockout', with_html=False, with_snapshots=False, fill_images=False,
             viewer_bytes=INLINE_HTML_LIMIT):
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
    # A marker must sit on the element itself: an anchor in empty space would pass the depth test from some side.
    tol = max(0.5, 0.005 * float((hi - lo).max())); normals, off = {}, []
    for e in elements:
        if e.get('status') == 'pending': continue
        d, normals[e['id']], near = surface_at(components, e['anchor'])
        # An internal element shown by its own section image may be anchored inside the material.
        if d > tol and not hidden_evidence(e, Path(elements_path).parent):
            near = ', '.join(f'{v:.2f}' for v in near @ turn.T)   # back in the model's own frame
            off.append(f"{e['id']}: anchor is {d:.1f} mm from the model surface (nearest surface point [{near}])")
    if off: raise Blocked('; '.join(off) + '; put each anchor on its element\'s surface (a hole: a point on its rim)')
    title = f"{spec.get('project', Path(model).stem)} · {spec.get('revision', '')} · {stage} · front {front}"
    visible = sheet(components, elements, lo, hi, out, title)
    hidden = [e['id'] for e in elements if not visible[e['id']] and e.get('status') != 'pending']
    base = Path(elements_path).resolve().parent
    own = [Path(e['image']) if Path(e['image']).is_absolute() else base / e['image']
           for e in elements if e.get('image') and not e.get('image_auto')]
    views, made, missing = snapshots(components, elements, lo, hi, out, normals, own) if (with_snapshots or fill_images) else ({}, {}, [])
    # A draft snapshot from the rear or underside is evidence too: the user can see the element in it.
    unexplained = [k for k in hidden if k not in made
                   and not hidden_evidence(next(e for e in elements if e['id'] == k), Path(elements_path).parent)]
    if unexplained:
        (out / 'sheet.png').unlink(missing_ok=True)
        raise Blocked(f'hidden in all views without section/detail evidence: {", ".join(unexplained)}; move the anchor '
                      'onto a visible face, run with --snapshots (rear and underside views), or set "image" to an '
                      'existing section/detail image and describe it in "hidden"')
    result = {'sheet': str((out / 'sheet.png').resolve()), 'elements': len(elements), 'components': len(components),
              'hidden_in_all_views': hidden, 'pending': [e['id'] for e in elements if e.get('status') == 'pending'],
              'skipped_surface': round(skipped, 5)}
    if with_snapshots or fill_images:
        result.update(views=views, snapshots={k: v[0] for k, v in made.items()}, snapshot_missing=missing)
    if fill_images:
        # Point each element at its draft snapshot unless it already carries its own picture (a section, a photo).
        # `image_auto` marks a filled snapshot, so a later run (any OUT folder) replaces or clears it.
        raw = json.loads(Path(elements_path).read_text()); filled_ids = []
        for e in raw.get('elements') or []:
            filled = e.get('image_auto')
            if e.get('image') and not filled: continue
            if e.get('id') in made:
                e['image'] = Path(made[e['id']][0]).relative_to(base).as_posix() if Path(made[e['id']][0]).is_relative_to(base) else made[e['id']][0]
                e['image_basis'] = 'final' if stage == 'detail' else 'cad'
                e['image_caption'] = f"{e.get('name', e['id'])} · draft view from {made[e['id']][1]}"
                e['image_auto'] = True; filled_ids.append(e['id'])
            elif filled:
                for k in ('image', 'image_basis', 'image_caption', 'image_auto'): e.pop(k, None)
        Path(elements_path).write_text(json.dumps(raw, indent=1, ensure_ascii=False))
        result['filled'] = sorted(filled_ids)
    if with_html:
        size, faces = html(components, elements, spec, stage, out, turn.T, min(viewer_bytes, INLINE_HTML_LIMIT))
        result.update(html=str((out / 'preview.html').resolve()), bytes=size, faces=faces)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('model', help='STEP or STL'); p.add_argument('elements', help='elements.json'); p.add_argument('out')
    p.add_argument('--stage', choices=STAGES, default='blockout'); p.add_argument('--html', action='store_true')
    p.add_argument('--snapshots', action='store_true', help='also write draft views (OUT/views) and one snapshot per element (OUT/elements)')
    p.add_argument('--fill-images', action='store_true', help='with snapshots: set image/image_basis in elements.json for elements without their own picture')
    p.add_argument('--viewer-bytes', type=int, default=INLINE_HTML_LIMIT,
                   help='with --html: byte budget for preview.html (lower it to leave room for board images)')
    a = p.parse_args()
    try:
        print(json.dumps(generate(a.model, a.elements, a.out, a.stage, a.html, a.snapshots, a.fill_images, a.viewer_bytes), indent=2))
    except Blocked as error:
        print(json.dumps({'blocked': str(error)}, indent=2)); sys.exit(2)
