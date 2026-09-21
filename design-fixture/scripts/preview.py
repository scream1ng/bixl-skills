#!/usr/bin/env python3
"""Non-authoritative compact meshes from evaluated exact specification geometry."""
import argparse
import base64
import copy
import gzip
import json
from pathlib import Path
import numpy as np
from workflow import resource, digest

INLINE_HTML_TARGET = 250_000
INLINE_HTML_LIMIT = 1_000_000


def evaluate(spec_path, kind, construction, out):
    from fixture_common import validate_spec, spec_path as resolve
    from export_step import export, read_step, write_step
    spec_path = Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text()); spec['_dir'] = str(spec_path.parent)
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    target = out / 'concept.step'
    if construction == 'laser_rib':
        if kind == 'checking':
            from checking_offsets import generate
            generate(spec)
            if 'checking_ribs' in spec:
                spec['checking_rib_definitions'] = spec.pop('checking_ribs')
        validate_spec(spec)
        from cap_joints import design as cap_design
        from tabs_slots import design
        from clamp_mount import mount
        import audit_width
        import cross_support
        import mount_compactness
        caps = cap_design(spec, lambda *args: None)
        tabs = design(spec, lambda *args: None); mount(spec)
        audit = {'cap_joints': caps, 'material_width': audit_width.audit(spec, tabs['tabs']), 'cross_support': cross_support.audit(spec),
                 'mount_compactness': mount_compactness.audit(spec)}
        export(spec, target)
    else:
        audit = {}
        from printed_body import build_shapes
        from hardware_geometry import definition, asset_path, rigid
        body_spec = copy.deepcopy(spec)
        if construction == 'block': body_spec['printed_bodies'] = spec.get('block_bodies', [])
        bodies, _ = build_shapes(body_spec)
        if not bodies: raise ValueError('Explicit exact fixture bodies required for solid construction')
        shapes = read_step(resolve(spec, spec['workpiece']['placed_step']))
        if set(shapes) & set(bodies): raise ValueError('Duplicate component IDs')
        shapes.update(bodies)
        for clamp in spec.get('clamps', []):
            hardware = definition(clamp['hardware'])
            transform = np.array(clamp['mount_transform']) @ np.array(hardware['asset']['source_to_canonical'])
            for name, shape in read_step(asset_path(clamp['hardware'])).items():
                key = 'HW_' + clamp['tag'] + '_' + name
                if key in shapes: raise ValueError('Duplicate hardware ID')
                shapes[key] = rigid(shape, transform)
        write_step(target, shapes)
    evaluated = {k: v for k, v in spec.items() if k != '_dir'}
    (out / 'evaluated-spec.json').write_text(json.dumps(evaluated, indent=2))
    shapes = read_step(target)
    from unload_path import audit as unload
    audit['unload'] = unload(spec, shapes)
    if construction == 'laser_rib':
        from pin_clearance import audit as pin_clearance
        audit['pin_clearance'] = pin_clearance(spec, shapes)
    (out / 'audit.json').write_text(json.dumps(audit, indent=2))
    return spec, shapes, target, digest(evaluated), audit


CHECKS = ('cap_joints', 'material_width', 'cross_support', 'mount_compactness', 'unload', 'pin_clearance')


def failing_items(name, report):
    """Short names of what failed, so the blocker list reads without opening audit.json."""
    if name == 'cap_joints': return [r['cap'] for r in report['caps'] if r['status'] == 'fail']
    if name == 'cross_support': return [r['plate'] for r in report['plates'] if r['status'] == 'fail'] + [f"{j['a']}x{j['b']}" for j in report['bad_joints']]
    if name == 'mount_compactness': return [r['mount_plate'] for r in report['mounts'] if r['status'] == 'fail']
    if name == 'unload': return [c['obstacle'] for c in report['collisions']]
    if name == 'pin_clearance': return [f"{v['pin']}~{v['plate']} {v['gap_mm']}mm" for v in report['violations']] + report.get('unseated', [])
    if name == 'material_width': return [k for k, c in report['categories'].items() if c['failed']] + [f['plate'] if isinstance(f, dict) and 'plate' in f else str(f) for f in report['edge_pair']['failures']]
    return []


def blockers(audit):
    """Basic-practice failures a concept must not be shown with; unknown stays reviewable."""
    rows = []
    for name in CHECKS:
        r = audit.get(name)
        if r and r['status'] == 'fail':
            action = r.get('next_action') or next((x.get('next_action') for x in r.get('mounts', []) if x.get('next_action')), None)
            rows.append({'check': name, 'items': failing_items(name, r), 'next_action': action})
    return rows


def hardware_proxies(shapes, clamps, triangles):
    """One coarse mesh per clamp: the full 14-part mechanism stays in concept.step, not the review HTML."""
    merged = {}
    for name, shape in shapes.items():
        leaf = name.split('/')[-1]
        tag = next((c['tag'] for c in clamps if leaf.startswith('HW_' + c['tag'] + '_')), None)
        if tag: merged.setdefault('HW_' + tag, []).append(triangles(shape))
    return {k: np.concatenate(v) for k, v in merged.items()}


def compact_mesh(triangles, target=1800):
    """Vertex clustering, preserving connected triangles; never stride/drop arbitrary facets."""
    raw = np.asarray(triangles, dtype=float).reshape(-1, 3, 3)
    points = raw.reshape(-1, 3)
    if not np.isfinite(points).all() or len(raw) == 0: raise ValueError('Invalid preview mesh')
    vertices, inverse = np.unique(np.round(points, 4), axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    span = max(float(np.ptp(points, axis=0).max()), 1e-6)
    cell = span / 700
    for _ in range(24):
        if len(faces) <= target: break
        keys = np.floor((vertices - points.min(axis=0)) / cell).astype(np.int64)
        _, mapping = np.unique(keys, axis=0, return_inverse=True)
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
    return {'positions': np.round(vertices[used], 3).ravel().tolist(), 'indices': mapping.ravel().tolist(),
            'source_triangles': len(raw), 'preview_triangles': len(faces), 'approximate': True}


def inline_html(scene):
    """Build the deterministic single-file viewer and enforce the inline size limit."""
    payload = json.dumps(scene, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c').encode()
    encoded = base64.b64encode(gzip.compress(payload, compresslevel=9, mtime=0)).decode('ascii')
    html = resource('assets/preview.html').read_text().replace('__SCENE_GZIP_BASE64__', encoded)
    if '__SCENE_GZIP_BASE64__' in html:
        raise ValueError('Preview scene placeholder was not replaced')
    size = len(html.encode())
    if size >= INLINE_HTML_LIMIT:
        raise ValueError(f'Inline preview is {size} bytes; must be strictly below {INLINE_HTML_LIMIT} bytes')
    return html, size


def generate(spec_path, out, kind='weld', construction='laser_rib', render=True):
    from render_review import triangles, render as render_png
    spec, shapes, step, evaluated_hash, audit = evaluate(spec_path, kind, construction, out)
    out = Path(out)
    checks = {name: audit[name]['status'] if name in audit else 'unknown' for name in CHECKS}
    blocking = blockers(audit)
    if blocking:  # no viewable concept exists while a basic check fails; audit.json and concept.step remain
        (out / 'preview.html').unlink(missing_ok=True)
        return {'html': None, 'evaluated_spec_sha256': evaluated_hash, 'checks': checks, 'blocking': blocking}
    components = []
    proxies = hardware_proxies(shapes, spec.get('clamps', []), triangles)
    for name, shape in shapes.items():
        leaf = name.split('/')[-1]
        group = 'workpiece' if leaf.startswith(('Part_', 'REF_source_')) else 'hardware' if leaf.startswith('HW_') else 'fixture'
        if group == 'hardware' and any(leaf.startswith(k + '_') for k in proxies): continue
        components.append({'id': name, 'group': group, **compact_mesh(triangles(shape), 1200 if group == 'workpiece' else 900)})
    for name, tris in proxies.items():
        components.append({'id': name, 'group': 'hardware', **compact_mesh(tris, 2000)})
    scene = {'schema_version': 'fixture-preview-1', 'project_id': spec['project_id'], 'revision': spec['revision'],
        'units': 'mm', 'fixture_kind': kind, 'construction': construction, 'evaluated_spec_sha256': evaluated_hash,
        'authoritative': False, 'components': components}
    payload = json.dumps(scene, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')
    (out / 'scene.json').write_text(payload)
    html, html_bytes = inline_html(scene)
    (out / 'preview.html').write_text(html)
    if render: render_png(step, out, spec['revision'])
    return {'html': str((out / 'preview.html').resolve()), 'evaluated_spec_sha256': evaluated_hash,
        'bytes': html_bytes, 'soft_target_met': html_bytes <= INLINE_HTML_TARGET, 'components': len(components),
        'checks': checks, 'blocking': [], 'private_dir': str(out.resolve())}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('spec'); p.add_argument('out')
    p.add_argument('--kind', choices=['weld', 'checking'], default='weld')
    p.add_argument('--construction', choices=['laser_rib', 'printed_solid', 'block'], default='laser_rib')
    a = p.parse_args(); print(json.dumps(generate(a.spec, a.out, a.kind, a.construction), indent=2))
