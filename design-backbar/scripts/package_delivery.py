"""Package only explicitly listed outputs from one completed run."""
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from completion import require_complete


def package_run(directory,destination,interim=False):
    directory=Path(directory).resolve();destination=Path(destination)
    report=json.loads((directory/'report.json').read_text())
    names=report['deliverables'];files=[]
    for name in names:
        path=(directory/name).resolve()
        if path.parent!=directory or path.suffix.lower() not in ('.step','.stp','.dxf','.html','.png') or not path.is_file():
            raise ValueError('Missing or invalid current deliverable: '+name)
        files.append(path)
    if interim:
        if 'INCOMPLETE' not in destination.stem:raise ValueError('An explicitly requested interim ZIP must include INCOMPLETE in its filename.')
    else:require_complete(directory,report)
    statuses=report.get('gauging_status',[])
    readme=('INCOMPLETE REVIEW — AGREED CAD CHANGES NOT VERIFIED' if interim else 'CAD CHANGES VERIFIED — SHOP TRIAL CHECKS REMAIN')+'\n\n'+report.get('part','Part')+'\n\n'
    if interim:readme+='Unresolved: '+'; '.join(report.get('completion',{}).get('unresolved',[]) or ['No complete verification of agreed changes.'])+'\n\n'
    readme+='\n'.join('+'.join('B'+str(n) for n in status['bends'])+' — '+status['method'] for status in statuses)
    readme+='\n\n'+('Physical edge changes affect the real blank as well as the CAD. See highlighted changes in the HTML.\n' if report.get('physical_blank_changed') else 'No physical blank changes in this run.\n')
    readme+='CAD-only programming tabs, if present, are excluded from the physical laser blank.\n'
    readme+='\nOpen checks: confirm tooling clearance, backgauge reach, staged folded-part fit and STEP import. Common-stroke and short-contact trials remain job-specific. This is not a manufacturing-verified release.\n'
    if report.get('estimated_unfold'):readme+='Estimated unfolding uses K=0.50; verify against a production blank.\n'
    with ZipFile(destination,'w',ZIP_DEFLATED) as archive:
        for path in files:archive.write(path,path.name)
        archive.writestr('README.txt',readme)
    with ZipFile(destination) as archive:
        if archive.testzip():raise ValueError('Package integrity check failed.')
    return destination
