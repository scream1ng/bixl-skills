"""Shared display policy. Keep measured values and stable CAD check keys intact."""
import copy
import math


def nominal_value(check):
    value=check['nominal']
    return f'{value:.1f}' if check.get('unit')=='deg' else format(value,'.12g')


def measurement(check,key=None):
    """Resolve one measured characteristic without inventing a second checkpoint."""
    items=check.get('measurements')
    if items is None:
        if key is not None:raise ValueError('Measurement key requires a compound checkpoint.')
        return check
    matches=[item for item in items if item['key']==key]
    if len(matches)!=1:raise ValueError('Dimension needs a valid named measurement from its checkpoint.')
    return {**check,'nominal':matches[0]['nominal']}


def validate_measurements(check):
    items=check.get('measurements')
    if items is None:return
    if not isinstance(items,list) or len(items)<2 or check.get('unit','mm')!='mm':raise ValueError('Compound checks need at least two linear measurements in mm.')
    if check.get('nominal') is not None or 'size_checks'in check:raise ValueError('Compound checks use measurements instead of nominal/size_checks.')
    keys=set()
    for item in items:
        if not isinstance(item,dict) or not isinstance(item.get('key'),str) or not item['key'] or item['key']in keys:raise ValueError('Measurement keys must be unique nonempty strings.')
        value=item.get('nominal')
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('Measurement nominal must be finite.')
        if set(item)-{'key','nominal'}:raise ValueError('Compound measurements share the checkpoint criteria; separate checks for different methods or limits.')
        keys.add(item['key'])


def normalize(spec,layout=None):
    spec=copy.deepcopy(spec)
    profile=(layout or {}).get('profile',{})
    if profile.get('reference_sample_check',True):
        sample={'key':'reference_sample','description':'Check part to Reference sample','limits':'Reference Sample','gauge':'Visual',
                'group':'hourly'if spec['process']=='laser'else'main',
                'source':'Company inspection requirement: designated physical reference sample; identity/revision must be confirmed.',
                'method':'Compare the part at this operation with the designated physical reference sample. Confirm sample identity/revision before use; CAD review does not validate the sample.'}
        matching=[c for c in spec['checks']if c['key']==sample['key']or c.get('description')==sample['description']]
        if len(matching)>1:raise ValueError('Duplicate reference-sample checks; retain one evidence-linked row.')
        for check in matching:
            if check.get('nominal')is not None or check.get('tolerance')is not None or 'measurements'in check or any(check.get(k, 'main'if k=='group'else None)!=sample[k]for k in ['description','limits','gauge','group']):
                raise ValueError('Reference-sample check criteria were altered; change the job-local profile explicitly.')
        if not matching:
            insert=next((i for i,c in enumerate(spec['checks'])if c.get('group','main')==sample['group']),len(spec['checks']))
            spec['checks'].insert(insert,sample)
    spec.setdefault('presentation',{}).setdefault('balloon_scale',profile.get('balloon_scale',1))
    quality=profile.get('final_visual_check')
    if quality:
        matching=[c for c in spec['checks'] if c['key']==quality['key'] or all(c.get(k)==quality.get(k)for k in ['description','limits','gauge'])]
        if len(matching)>1:raise ValueError('Duplicate configured final visual checks; retain one evidence-linked check.')
        for check in matching:
            if check.get('nominal') is not None or check.get('tolerance') is not None or 'measurements'in check or any(check.get(k)!=quality.get(k) for k in ['description','limits','gauge','group']):
                raise ValueError('Configured final visual check was altered; change the job-local company profile explicitly.')
        if not matching:matching=[copy.deepcopy(quality)]
        matched={c['key']for c in matching}
        spec['checks']=[c for c in spec['checks'] if c['key']not in matched]+matching
    prefix={'laser':'L','bending':'B','welding':'W'}[spec['process']]
    order={group:i for i,group in enumerate((layout or {}).get('groups',{}))}
    ranks=[order.get(c.get('group','main'),-1)for c in spec['checks']]
    if order and ranks!=sorted(ranks):raise ValueError('Checks must follow mapped inspection group order (setup before hourly).')
    for index,check in enumerate(spec['checks'],1):check['id']=f'{prefix}{index}'
    available=spec.get('available_gauges',profile.get('available_gauges'))
    if available is not None:
        if not isinstance(available,list) or not available:raise ValueError('available_gauges must be a nonempty list.')
        for check in spec['checks']:
            if check.get('gauge')!='Visual'and check.get('gauge') not in available:
                raise ValueError(f"Gauge {check.get('gauge')!r} is not available for {check['id']}; choose an available gauge and verify its contacts/access.")
            if check.get('unit')=='deg'and check.get('gauge')=='Vernier':raise ValueError('Angle checks require Protractor or an explicitly available angular tool with verified contacts.')
    return spec


def caption(check,checks):
    """Numeric captions reference current check values, never copied dimensions."""
    if check.get('measurements') is not None:
        validate_measurements(check)
        value=' × '.join(nominal_value(measurement(check,item['key']))for item in check['measurements'])
        return f"Check {check.get('feature','size')} {value} mm"
    if check.get('nominal') is None:return check['description']
    feature=check.get('feature','angle' if check.get('unit')=='deg' else 'distance')
    keys=check.get('size_checks',[check['key']])
    if not isinstance(keys,list) or not keys or check['key'] not in keys:
        raise ValueError('size_checks must include the current stable check key.')
    linked=[checks[key] for key in keys]
    unit=check.get('unit','mm')
    if any(c.get('nominal') is None or c.get('unit','mm')!=unit for c in linked):
        raise ValueError('Caption size checks require measured values with matching units.')
    value=' × '.join(nominal_value(c) for c in linked)
    if check.get('diameter'):value='Ø'+value
    return f'Check {feature} {value}'+('°' if unit=='deg' else ' '+unit)


def pack_views(spec,geometry):
    """Map grouped CAD views and all their annotations with the same transform."""
    import xml.etree.ElementTree as ET
    ns='http://www.w3.org/2000/svg';q=lambda t:'{'+ns+'}'+t
    drawing=spec['drawing'];views=drawing.get('views')
    if not views:return spec,geometry
    shape=ET.fromstring(geometry);expected=f"0 0 {drawing.get('source_width',drawing['width'])} {drawing.get('source_height',drawing['height'])}"
    if shape.get('viewBox')!=expected:raise ValueError('Grouped geometry viewBox must match source dimensions.')
    result=copy.deepcopy(spec);out=result['drawing'];out.pop('views',None)
    root=ET.Element(q('svg'),viewBox=f"0 0 {out['width']} {out['height']}")
    transforms={};targets=[]
    for view in views:
        key=view['key'];source=view['source_box'];target=view['box']
        if key in transforms:raise ValueError('Drawing view keys must be unique.')
        if len(source)!=4 or len(target)!=4 or not all(isinstance(n,(int,float)) and math.isfinite(n) for n in source+target):raise ValueError('View boxes need four finite coordinates.')
        sx,sy,sw,sh=source;x,y,w,h=target
        if min(sw,sh,w,h)<=0 or min(x,y)<0 or x+w>out['width'] or y+h>out['height']:raise ValueError('Drawing views must fit the output canvas.')
        if any(x<a+aw and a<x+w and y<b+bh and b<y+h for a,b,aw,bh in targets):raise ValueError('Drawing view boxes overlap.')
        targets.append(target);scale=min(w/sw,h/sh);tx=x+(w-sw*scale)/2-sx*scale;ty=y+(h-sh*scale)/2-sy*scale
        transforms[key]=(scale,tx,ty,source)
    for child in shape:
        key=child.get('data-view')
        if key not in transforms:raise ValueError('Every geometry view group requires a declared data-view key.')
        scale,tx,ty,_=transforms[key]
        wrapper=ET.SubElement(root,q('g'),transform=f'translate({tx} {ty}) scale({scale})')
        inherited=ET.SubElement(wrapper,q('g'),{k:v for k,v in shape.attrib.items()if k not in ['viewBox','width','height','x','y']})
        clone=copy.deepcopy(child);clone.attrib.pop('data-view',None);inherited.append(clone)
        for e in clone.iter():
            if e.tag!=q('g'):e.set('vector-effect','non-scaling-stroke')
    def point(p,transform):
        scale,tx,ty,box=transform;sx,sy,w,h=box
        if len(p)!=2 or not all(isinstance(n,(int,float)) and math.isfinite(n) for n in p):raise ValueError('View annotation needs finite point coordinates.')
        if not(sx<=p[0]<=sx+w and sy<=p[1]<=sy+h):raise ValueError('View annotation lies outside its source box.')
        return [p[0]*scale+tx,p[1]*scale+ty]
    for dimension in out['dimensions']:
        key=dimension.pop('view',None)
        if key not in transforms:raise ValueError('Every dimension requires a declared view key.')
        transform=transforms[key];scale,tx,ty,_=transform
        for field in ['a','b','centre','value_xy','badge_xy']:
            if field in dimension:dimension[field]=point(dimension[field],transform)
        if dimension['kind'] in ['horizontal','vertical']:
            dimension['offset']=dimension['offset']*scale+(ty if dimension['kind']=='horizontal' else tx)
        else:
            dimension['radius']*=scale
            if 'contact_segments'in dimension:dimension['contact_segments']=[[point(p,transform)for p in segment]for segment in dimension['contact_segments']]
    for balloon in out.get('balloons',[]):
        key=balloon.pop('view',None)
        if key not in transforms:raise ValueError('Every balloon requires a declared view key.')
        balloon['badge_xy']=point(balloon['badge_xy'],transforms[key])
        if 'value_xy'in balloon:balloon['value_xy']=point(balloon['value_xy'],transforms[key])
        branches=balloon.get('targets',[balloon])
        for branch in branches:
            branch['target']=point(branch['target'],transforms[key])
            branch['elbows']=[point(p,transforms[key])for p in branch.get('elbows',[])]
    return result,ET.tostring(root)
