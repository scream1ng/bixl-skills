#!/usr/bin/env python3
"""Non-authoritative compact meshes from evaluated exact specification geometry."""
import argparse
import copy
import json
from pathlib import Path
import numpy as np
from workflow import resource, digest


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
        caps = cap_design(spec, lambda *args: None)
        tabs = design(spec, lambda *args: None); mount(spec)
        audit = {'cap_joints': caps, 'material_width': audit_width.audit(spec, tabs['tabs'])}
        export(spec, target)
    else:
        audit = None
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
    if audit is not None:
        (out / 'audit.json').write_text(json.dumps(audit, indent=2))
    return spec, read_step(target), target, digest(evaluated), audit


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


def generate(spec_path, out, kind='weld', construction='laser_rib', render=True):
    from render_review import triangles, render as render_png
    spec, shapes, step, evaluated_hash, audit = evaluate(spec_path, kind, construction, out)
    out = Path(out)
    components = []
    for name, shape in shapes.items():
        leaf = name.split('/')[-1]
        group = 'workpiece' if leaf.startswith(('Part_', 'REF_source_')) else 'hardware' if leaf.startswith('HW_') else 'fixture'
        components.append({'id': name, 'group': group, **compact_mesh(triangles(shape), 1800 if group == 'workpiece' else 900)})
    scene = {'schema_version': 'fixture-preview-1', 'project_id': spec['project_id'], 'revision': spec['revision'],
        'units': 'mm', 'fixture_kind': kind, 'construction': construction, 'evaluated_spec_sha256': evaluated_hash,
        'authoritative': False, 'components': components}
    payload = json.dumps(scene, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')
    (out / 'scene.json').write_text(payload)
    html = resource('assets/preview.html').read_text().replace('__SCENE_JSON__', payload)
    (out / 'preview.html').write_text(html)
    if render: render_png(step, out, spec['revision'])
    return {'html': str((out / 'preview.html').resolve()), 'scene': str((out / 'scene.json').resolve()),
        'evaluated_spec_sha256': evaluated_hash, 'bytes': len(html.encode()), 'inline_eligible': len(html.encode()) < 1_000_000,
        'component_ids': [c['id'] for c in components], 'authoritative': False,
        'material_width': audit['material_width']['status'] if audit else 'unknown',
        'cap_joints': audit['cap_joints']['status'] if audit else 'unknown',
        'fallback_pngs': [str((out / n).resolve()) for n in ('assembled.png', 'empty-fixture.png')] if render else []}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('spec'); p.add_argument('out')
    p.add_argument('--kind', choices=['weld', 'checking'], default='weld')
    p.add_argument('--construction', choices=['laser_rib', 'printed_solid', 'block'], default='laser_rib')
    a = p.parse_args(); print(json.dumps(generate(a.spec, a.out, a.kind, a.construction), indent=2))
