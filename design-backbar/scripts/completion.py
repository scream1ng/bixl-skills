"""Bind completed-change claims and matching deliverables to exported CAD bytes."""
import hashlib
import math
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_common_step(path, groups, bend_map=None, expected_centers=None, line_tolerance=.001):
    """Reopen actual STEP, identify bend surfaces and measure; never edit or relax limits."""
    if not math.isfinite(line_tolerance) or not 0<line_tolerance<=.001:raise ValueError('Completion tolerance may only tighten the 0.001 mm limit.')
    import geometry as g
    from unfold import unfold
    from operations import validate_common_groups
    reader=g.STEPControl_Reader()
    if reader.ReadFile(str(path))!=1:raise ValueError('Cannot reopen exported STEP.')
    reader.TransferRoots();shape=reader.OneShape()
    if len(g.sub(shape,g.TopAbs_SOLID,g.TopoDS.Solid_s))!=1 or not g.BRepCheck_Analyzer(shape).IsValid():
        raise ValueError('Exported CAD is not one valid solid.')
    _,bends,_,_=unfold(shape)
    if expected_centers is not None:
        indexes=[]
        for center in expected_centers:
            if center is None:raise ValueError('Common-bend identity needs formed-surface references; supplied-flat numbering cannot be assumed to match.')
            distances=[math.dist(center,b['formed_center']) for b in bends]
            matches=[i for i,distance in enumerate(distances) if distance<.001]
            if len(matches)!=1:raise ValueError('Cannot uniquely match a bend to exported CAD.')
            indexes.append(matches[0])
        if len(set(indexes))!=len(indexes) or len(indexes)!=len(bends):raise ValueError('Exported bend identities changed.')
        bends=[bends[i] for i in indexes]
    elif bend_map is not None:
        if sorted(bend_map)!=list(range(1,len(bends)+1)):raise ValueError('Invalid exported bend mapping.')
        bends=[bends[i-1] for i in bend_map]
    checks=validate_common_groups(groups,bends,line_tolerance)
    for check in checks:
        a=bends[check['master']-1];b=bends[check['member']-1]
        required=('formed_axis_p','formed_axis_d','inner_radius_mm','fold_sense')
        if not all(k in v for v in (a,b) for k in required):
            raise ValueError('Analytic bend evidence unavailable; provide a measured custom readback verification, not a commonised claim.')
        d=a['formed_axis_d'];e=b['formed_axis_d'];cosine=max(-1.,min(1.,sum(x*y for x,y in zip(d,e))))
        angle=math.degrees(math.acos(abs(cosine)))
        offsets=[]
        for point in (b['formed_axis_p'],b['formed_center']):
            # Project the surface centre onto its own axis before comparing axes.
            along=sum((x-y)*z for x,y,z in zip(point,b['formed_axis_p'],e))
            point=[x+along*y for x,y in zip(b['formed_axis_p'],e)]
            delta=[x-y for x,y in zip(point,a['formed_axis_p'])];dot=sum(x*y for x,y in zip(delta,d))
            offsets.append(math.sqrt(sum((x-dot*y)**2 for x,y in zip(delta,d))))
        radius=abs(a['inner_radius_mm']-b['inner_radius_mm'])
        if max(offsets)>line_tolerance or angle>.001 or radius>.001 or a['fold_sense']!=b['fold_sense']:
            raise ValueError('Exported common bends fail formed-axis, radius or fold-sense checks; CAD correction remains unresolved.')
        check.update(formed_axis_offset_mm=max(offsets),formed_axis_angle_deg=angle,radius_difference_mm=radius,
                     fold_sense='matched',status='geometry_verified_in_export')
        check.pop('fold_sense_and_tooling',None)
        check['tooling']='unverified'
    return {'step_sha256':digest(path),'checks':checks}


def change_failures(requirements, step_hash):
    """Evaluate explicit numerical readback criteria for all agreed physical edits."""
    failures=[]
    if not isinstance(requirements,dict) or requirements.get('reviewed') is not True:
        return ['Agreed-change inventory has not been reviewed against the conversation.']
    changes=requirements.get('changes')
    if not isinstance(changes,list):return ['Missing agreed-change list.']
    ids=set()
    for change in changes:
        ident=change.get('id')
        if not ident or ident in ids:failures.append('Missing or duplicate change ID.');continue
        ids.add(ident)
        if not change.get('description'):failures.append(f'{ident}: missing agreed change description.')
        if change.get('kind')=='common_bend':
            if not isinstance(change.get('bends'),list) or len(change['bends'])<2:failures.append(f'{ident}: missing common bend IDs.')
            continue # Common geometry is remeasured independently below.
        checks=change.get('checks',[])
        if change.get('step_sha256')!=step_hash or not checks:
            failures.append(f'{ident}: missing current exported-STEP measurements.');continue
        for check in checks:
            value=check.get('measured');low=check.get('min');high=check.get('max')
            valid=lambda v:isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
            if not check.get('name') or not check.get('unit') or not all(valid(v) for v in (value,low,high)) or low>high or not low<=value<=high:
                failures.append(f'{ident}: failed or missing criterion {check.get("name","unnamed")}.')
    return failures


def seal_delivery(directory, report, requirements, expected_centers=None):
    """After generation/visual review, bind the agreed-change inventory and all current files."""
    directory=Path(directory);step=directory/report['step'];sha=digest(step)
    failures=change_failures(requirements,sha)
    groups=[g for g in report.get('operations',[]) if len(g)>1]
    ledger_groups=[c['bends'] for c in requirements.get('changes',[]) if c.get('kind')=='common_bend' and isinstance(c.get('bends'),list)] if isinstance(requirements,dict) else []
    for group in groups:
        if not any(set(group)==set(c) for c in ledger_groups):failures.append('Common operation missing from agreed-change inventory: '+str(group))
    if any(not any(set(c)==set(g) for g in groups) for c in ledger_groups):failures.append('Requested common bend missing from operation sequence.')
    verification={}
    if groups:
        try:verification=verify_common_step(step,groups,report.get('export_bend_map'),expected_centers,line_tolerance=report.get('common_line_tolerance_mm',.001))
        except (ValueError,RuntimeError) as error:failures.append(str(error))
    if not report.get('verification'):failures.append('Missing STEP validation.')
    report['completion']={'requirements':requirements,'step_sha256':sha,'common_readback':verification,
                          'expected_centers':expected_centers,'unresolved':failures,'status':'incomplete' if failures else 'cad_changes_verified',
                          'files':{name:digest(directory/name) for name in report['deliverables']}}
    return report['completion']


def require_complete(directory, report):
    """Fail closed before ZIP creation, including stale files or overwritten CAD."""
    directory=Path(directory);record=report.get('completion',{})
    if record.get('status')!='cad_changes_verified' or record.get('unresolved'):
        raise ValueError('Incomplete CAD changes: '+('; '.join(record.get('unresolved',[])) or 'no exported-CAD completion record'))
    names=report['deliverables']
    if set(record.get('files',{}))!=set(names):raise ValueError('Delivery manifest changed after verification.')
    for name in names:
        if digest(directory/name)!=record['files'][name]:raise ValueError('Deliverable changed after verification: '+name)
    if digest(directory/report['step'])!=record.get('step_sha256'):raise ValueError('STEP changed after verification.')
    failures=change_failures(record.get('requirements'),record['step_sha256'])
    if failures:raise ValueError('Incomplete CAD changes: '+'; '.join(failures))
    # Re-evaluate ledger coverage and independently remeasure grouped bends at packaging.
    refreshed=dict(report)
    result=seal_delivery(directory,refreshed,record['requirements'],record.get('expected_centers'))
    if result['unresolved']:raise ValueError('Incomplete CAD changes: '+'; '.join(result['unresolved']))
    return result
