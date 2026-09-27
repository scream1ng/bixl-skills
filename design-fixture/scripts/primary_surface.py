#!/usr/bin/env python3
"""Every primary (A) datum point of a part sits on one trimmed face, never split across a bend or straights."""
import numpy as np

PLANE_TOL_MM = 0.01


def joined(target, indices, normal, offset):
    """True when the faces (explorer indices) connect through a chain of coplanar faces sharing edges:
    one surface the export happened to split, not two flanges either side of a bend."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopExp import TopExp, TopExp_Explorer
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape
    from OCP.TopoDS import TopoDS
    faces, exp = [], TopExp_Explorer(target, TopAbs_FACE)
    while exp.More(): faces.append(TopoDS.Face_s(exp.Current())); exp.Next()
    def on_plane(face):
        surf = BRepAdaptor_Surface(face, True)
        if surf.GetType() != GeomAbs_Plane: return False
        pl = surf.Plane(); n = np.array(pl.Axis().Direction().Coord())
        return abs(abs(n @ normal) - 1) < 1e-4 and abs(np.array(pl.Location().Coord()) @ normal - offset) < PLANE_TOL_MM
    plane = {i + 1 for i, f in enumerate(faces) if on_plane(f)}
    index = {i + 1: f for i, f in enumerate(faces)}
    edges = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(target, TopAbs_EDGE, TopAbs_FACE, edges)
    neighbours = {i: set() for i in plane}
    for k in range(1, edges.Extent() + 1):
        owners = [i for i in plane for f in edges.FindFromIndex(k) if f.IsSame(index[i])]
        for i in owners: neighbours[i].update(set(owners) - {i})
    start = next(iter(indices)); seen, todo = {start}, [start]
    while todo:
        for j in neighbours.get(todo.pop(), ()):
            if j not in seen: seen.add(j); todo.append(j)
    return set(indices) <= seen


def audit(spec, shapes):
    from verify import face_contact, resolve_part
    from assembly_locating import fixed
    parts = {k: s for k, s in shapes.items() if k.split('/')[-1].startswith(('Part_', 'REF_source_'))}
    mapping = spec.get('workpiece', {}).get('parts', {})
    waived = {w['part']: w['reason'] for w in spec.get('primary_surface_waivers', [])}
    groups = {}
    for c in spec.get('contacts', []):
        if c.get('role') == 'Primary' and fixed(c): groups.setdefault(c.get('part'), []).append(c)
    rows = []
    for part, contacts in groups.items():
        _, target = resolve_part(parts, mapping.get(part, part))
        row = {'part': part, 'contacts': [c['name'] for c in contacts], 'faces': {}}
        if part in waived:
            row.update(status='exception', reason=waived[part]); rows.append(row); continue
        if target is None:
            row.update(status='unknown', reason='part not found in the placed CAD'); rows.append(row); continue
        planes = {}
        for c in contacts:
            fc = face_contact(c, target)
            row['faces'][c['name']] = fc.get('face_index_in_export')
            if 'face_index_in_export' in fc:
                n = np.array(fc['outward_normal']); planes[fc['face_index_in_export']] = (n, float(np.array(c['contact']) @ n))
        faces = set(row['faces'].values())
        if None in faces:
            row.update(status='unknown', reason='a primary point is not on one resolvable planar face')
        elif len(faces) == 1:
            row.update(status='pass', reason='all primary points on one face')
        elif joined(target, faces, *next(iter(planes.values()))):
            row.update(status='pass', reason='one surface split into coplanar faces that share edges')
        else:
            row.update(status='fail', reason='primary points split across separate surfaces')
        rows.append(row)
    failed = [r for r in rows if r['status'] == 'fail']
    status = 'fail' if failed else 'not_applicable' if not rows else \
        'pass' if all(r['status'] == 'pass' for r in rows) else 'unknown' if any(r['status'] == 'unknown' for r in rows) else 'exception'
    out = {'status': status, 'parts': rows}
    if failed:
        out['next_action'] = '; '.join(
            f"{r['part']}: move primary points {', '.join(r['contacts'])} onto one face (spread along it) "
            f"or record a user-quoted primary_surface_waivers entry" for r in failed)
    return out
