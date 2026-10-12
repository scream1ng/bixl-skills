"""Shared display policy. Keep measured values and stable CAD check keys intact."""
import copy
import math


def nominal_value(check):
    value=check['nominal']
    return f'{value:.1f}' if check.get('unit')=='deg' else format(value,'.12g')


def normalize(spec,layout=None):
    spec=copy.deepcopy(spec)
    profile=(layout or {}).get('profile',{})
    quality=profile.get('final_visual_check')
    if quality:
        matching=[c for c in spec['checks'] if c['key']==quality['key'] or all(c.get(k)==quality.get(k)for k in ['description','limits','gauge'])]
        if len(matching)>1:raise ValueError('Duplicate configured final visual checks; retain one evidence-linked check.')
        for check in matching:
            if check.get('nominal') is not None or check.get('tolerance') is not None or any(check.get(k)!=quality.get(k) for k in ['description','limits','gauge','group']):
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
            if check.get('gauge') not in available:
                raise ValueError(f"Gauge {check.get('gauge')!r} is not available for {check['id']}; choose an available gauge and verify its contacts/access.")
            if check.get('unit')=='deg'and check.get('gauge')=='Vernier':raise ValueError('Angle checks require Protractor or an explicitly available angular tool with verified contacts.')
    return spec


def caption(check,checks):
    """Numeric captions reference current check values, never copied dimensions."""
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
        for field in ['target','badge_xy']:balloon[field]=point(balloon[field],transforms[key])
        balloon['elbows']=[point(p,transforms[key])for p in balloon.get('elbows',[])]
    return result,ET.tostring(root)
