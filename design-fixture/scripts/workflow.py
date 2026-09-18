#!/usr/bin/env python3
"""Versioned, source-bound concept/revision/finalization entrypoint."""
import argparse
import hashlib
import json
from pathlib import Path

VERSION = 'fixture-project-1'
MODES = {'weld': {'laser_rib', 'block'}, 'checking': {'laser_rib', 'printed_solid'}}
ROOT = Path(__file__).resolve().parent.parent


def resource(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError('Missing or unsafe bundled resource: ' + relative)
    return path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def route(kind=None, construction=None, concept_exception=None):
    if kind is None:
        return {'question': 'Weld fixture or Check fixture?', 'choices': ['weld', 'checking']}
    kind = 'checking' if kind == 'check' else kind
    construction = construction or 'laser_rib'
    if kind not in MODES or construction not in {'laser_rib', 'block', 'printed_solid'}:
        raise ValueError('Unknown fixture kind or construction')
    supported = construction in MODES[kind]
    if not supported and not (isinstance(concept_exception, str) and concept_exception.strip()):
        raise ValueError('Unsupported mode; requires an explicit concept-only exception reason')
    return {'fixture_kind': kind, 'construction': construction, 'concept_only': not supported,
            'exception_reason': concept_exception if not supported else None}


def snapshot(spec_path):
    spec_path = Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text())
    if spec.get('units') != 'mm' or not spec.get('project_id') or not spec.get('revision'):
        raise ValueError('Spec requires project_id, revision and mm units')
    from survey_step import rigid_transform
    frame = spec.get('workpiece', {}).get('source_to_fixture')
    if frame is None:
        raise ValueError('Survey and record the coordinate frame first')
    rigid_transform(frame)
    wp = spec['workpiece']
    sources = []
    if not wp.get('source_files') or not wp.get('placed_step'):
        raise ValueError('Original source and placed CAD are required')
    paths = [('original', x) for x in wp['source_files']] + [('placed', wp['placed_step'])]
    for field in ('printed_bodies', 'block_bodies'):
        paths += [('finished_body', x['finished_step']) for x in spec.get(field, []) if x.get('finished_step')]
    for role, name in paths:
        path = Path(name)
        path = path if path.is_absolute() else spec_path.parent / path
        sources.append({'role': role, 'path': str(path.resolve()), 'sha256': file_hash(path)})
    ids = []
    for field in ('plates', 'printed_bodies', 'block_bodies'):
        ids += [x['name'] for x in spec.get(field, [])]
    ids += [x['plate']['name'] for x in spec.get('checking_ribs', [])]
    ids += list(wp.get('parts', {}).values())
    ids += ['CLAMP:' + x['tag'] for x in spec.get('clamps', [])]
    ids += ['CONTACT:' + x['name'] for x in spec.get('contacts', [])]
    # Contact/clamp namespaces keep identity distinct from manufactured solid names.
    geometry = {k: v for k, v in spec.items() if k not in ('engineering_checks', 'checking_evidence')}
    identity = {'spec': spec, 'sources': sources}
    return spec, {'project_id': spec['project_id'], 'revision': spec['revision'], 'units': 'mm',
        'coordinate_frame': {'name': 'fixture', 'source_to_fixture': frame}, 'sources': sources,
        'geometry_digest': digest({'spec': geometry, 'sources': sources}), 'input_digest': digest(identity),
        'component_ids': sorted(set(ids)), 'decisions': spec.get('decisions', []),
        'open_items': spec.get('open_items', []),
        'evidence': [{k: row[k] for k in ('name', 'status', 'geometry_fingerprint', 'evidence', 'next_action') if k in row}
            for row in spec.get('engineering_checks', []) + spec.get('checking_evidence', [])]}


def read_record(path):
    record = json.loads(Path(path).read_text())
    if record.get('schema_version') != VERSION:
        raise ValueError('Unsupported project version; explicitly migrate or rebuild')
    return record


def save(path, record):
    Path(path).write_text(json.dumps(record, indent=2, allow_nan=False) + '\n')


def initialize(spec_path, kind, construction=None, concept_exception=None, complete_request=None):
    mode = route(kind, construction, concept_exception)
    if 'question' in mode:
        return mode
    spec, snap = snapshot(spec_path)
    if mode['fixture_kind'] == 'checking' and spec.get('inspection', {}).get('construction') != mode['construction']:
        raise ValueError('Inspection construction must match selected mode')
    if mode['fixture_kind'] == 'weld' and spec.get('inspection'):
        raise ValueError('Weld spec must not retain a checking plan')
    record = {'schema_version': VERSION, **snap, **mode, 'stage': 'concept', 'retired_ids': [],
        'authorization': None, 'history': [], 'readiness': {k: False for k in
            ('cad_verified', 'fabrication_ready', 'fixture_calibrated', 'inspection_validated')}}
    if complete_request:
        authorize(record, complete_request, initial=True)
    return record


def resume(spec_path, record):
    _, current = snapshot(spec_path)
    if record.get('schema_version') != VERSION:
        raise ValueError('Unsupported project version')
    if current['input_digest'] != record['input_digest']:
        raise ValueError('Source/spec changed; re-survey if necessary and checkpoint before reuse')
    return current


def checkpoint(spec_path, record, resurveyed=False):
    spec, snap = snapshot(spec_path)
    if snap['project_id'] != record['project_id']:
        raise ValueError('Cannot change project identity')
    old_sources = [(x['role'], x['sha256']) for x in record['sources']]
    new_sources = [(x['role'], x['sha256']) for x in snap['sources']]
    if (old_sources != new_sources or snap['coordinate_frame'] != record['coordinate_frame']) and not resurveyed:
        raise ValueError('Source/frame changed; fresh survey required (--resurveyed only after surveying)')
    if snap['input_digest'] == record['input_digest']:
        return record
    if snap['revision'] == record['revision']:
        raise ValueError('Changed spec requires a new revision')
    if set(snap['component_ids']) & set(record['retired_ids']):
        raise ValueError('Do not recycle retired component IDs')
    fresh = initialize(spec_path, record['fixture_kind'], record['construction'], record.get('exception_reason'))
    fresh['retired_ids'] = sorted(set(record['retired_ids']) | (set(record['component_ids']) - set(snap['component_ids'])))
    fresh['history'] = record['history'] + [{'revision': record['revision'], 'input_digest': record['input_digest'], 'stage': record['stage']}]
    return fresh


def authorize(record, request, initial=False):
    if record['concept_only']:
        raise ValueError('Concept-only exception cannot be finalized')
    if not isinstance(request, str) or not request.strip():
        raise ValueError('Record the actual explicit user request')
    if not initial and record['stage'] not in ('preview', 'finalized', 'finalization_needs_review'):
        raise ValueError('Generate/review concept before requesting finalization')
    record['authorization'] = {'user_request': request.strip(), 'input_digest': record['input_digest'],
        'scope': 'package generation only; not engineering approval', 'initial_complete_request': initial}
    return record


def finalization_allowed(spec_path, record):
    resume(spec_path, record)
    auth = record.get('authorization')
    if record['concept_only'] or not auth or auth['input_digest'] != record['input_digest']:
        raise ValueError('Explicit current user package authorization required')
    if record['stage'] not in ('preview', 'finalized', 'finalization_needs_review'):
        raise ValueError('Concept preview must be generated before finalization')


def finalize(spec_path, record, out):
    finalization_allowed(spec_path, record)
    if record['construction'] == 'block':
        return {'status': 'manual_block_finalization_required', 'reference': 'references/finalization.md'}
    if record['fixture_kind'] == 'checking':
        from build_check import build
    else:
        from build import build
    result = build(spec_path, out)
    ver = json.loads((Path(result['delivery']) / 'JSON/verification.json').read_text())
    record['readiness'] = {k: ver.get(k, ver.get('geometry_status') == 'pass' if k == 'cad_verified' else False)
        for k in record['readiness']}
    record['stage'] = 'finalized' if result['exit_code'] == 0 else 'finalization_needs_review'
    record['open_items'] = ver.get('open_items', [])
    return {k: v for k, v in result.items() if k not in ('cad', 'plates')}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['route', 'init', 'resume', 'checkpoint', 'concept', 'authorize', 'finalize'])
    p.add_argument('spec', nargs='?'); p.add_argument('record', nargs='?'); p.add_argument('out', nargs='?')
    p.add_argument('--kind', choices=['weld', 'checking', 'check']); p.add_argument('--construction')
    p.add_argument('--concept-exception'); p.add_argument('--complete-package-request'); p.add_argument('--request')
    p.add_argument('--resurveyed', action='store_true')
    a = p.parse_args()
    if a.action == 'route':
        result = route(a.kind, a.construction, a.concept_exception)
    elif a.action == 'init':
        result = initialize(a.spec, a.kind, a.construction, a.concept_exception, a.complete_package_request)
        if 'question' not in result:
            if Path(a.record).exists():
                raise ValueError('Project exists; resume or checkpoint instead of overwriting')
            save(a.record, result)
    else:
        record = read_record(a.record)
        if a.action == 'checkpoint':
            record = checkpoint(a.spec, record, a.resurveyed); result = record
        else:
            resume(a.spec, record)
            if a.action == 'resume': result = record
            elif a.action == 'authorize': result = authorize(record, a.request)
            elif a.action == 'concept':
                from preview import generate
                result = generate(a.spec, a.out, record['fixture_kind'], record['construction'])
                record['stage'] = 'preview'; record['preview'] = result
            else: result = finalize(a.spec, record, a.out)
        if a.action != 'resume': save(a.record, record)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try: main()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise SystemExit('WORKFLOW STOPPED: ' + str(exc))
