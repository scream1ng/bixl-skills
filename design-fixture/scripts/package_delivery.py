"""Zip one finalized delivery with the records and sources it was built from."""
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def package_run(spec_path, record_path, delivery, out):
    spec_path, record_path, delivery = Path(spec_path).resolve(), Path(record_path).resolve(), Path(delivery).resolve()
    spec = json.loads(spec_path.read_text())
    name = f"{spec['project_id']}-{spec['revision']}"
    if not (delivery / 'JSON/verification.json').is_file():
        raise ValueError('No finalized delivery to package: ' + str(delivery))
    files = [(p, f'{name}/DELIVERY/{p.relative_to(delivery).as_posix()}') for p in sorted(delivery.rglob('*')) if p.is_file()]
    files += [(spec_path, f'{name}/source/spec.json'), (record_path, f'{name}/source/project.json')]
    for src in spec['workpiece']['source_files']:
        path = Path(src) if Path(src).is_absolute() else spec_path.parent / src
        files.append((path.resolve(), f'{name}/source/{path.name}'))
    arcnames = [a for _, a in files]
    if len(set(arcnames)) != len(arcnames):
        raise ValueError('Two source files share one name; rename one before packaging')
    order = build_order_text(spec, delivery)
    destination = Path(out) / f'{name}.zip'
    with ZipFile(destination, 'w', ZIP_DEFLATED) as archive:
        for path, arcname in files:
            archive.write(path, arcname)
        if order:
            archive.writestr(f'{name}/BUILD-ORDER.txt', order)
    with ZipFile(destination) as archive:
        if archive.testzip() or any(archive.read(a) != p.read_bytes() for p, a in files):
            raise ValueError('Package integrity check failed')
    return destination


def build_order_text(spec, delivery):
    """Fit-up list matching the etched numbers; empty when the job etches part numbers instead."""
    verification = json.loads((delivery / 'JSON/verification.json').read_text())
    order = verification.get('measurements', {}).get('cutting_audit', {}).get('build_order')
    if not order:
        return ''
    roles = {p['name']: p.get('role', '') for p in spec.get('plates', [])}
    partners = {}
    for j in spec.get('joints', []):
        partners.setdefault(j['a'], []).append(j['b']); partners.setdefault(j['b'], []).append(j['a'])
    lines = [f"{spec['project_id']}-{spec['revision']} fit-up order (number etched on each plate and beside its slots)", '']
    for row in order:
        n = row['name']
        where = f"in {row['seat']}" if row.get('seat') else f"on {', '.join(partners[n])}" if partners.get(n) else ''
        lines.append(f"{row['number']:>3}  {n}  {row.get('part_number') or ''}  {roles.get(n, '')}  {where}".rstrip())
    return '\n'.join(lines) + '\n'
