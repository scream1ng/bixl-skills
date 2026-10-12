"""Portable ICL review, approval and template export. No CAD values are inferred here."""
import argparse
import base64
import hashlib
import html
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def relative(base, value):
    path = Path(value)
    if path.is_absolute():
        raise ValueError('Use portable relative paths in the spec/layout.')
    return (base / path).resolve()


def load(path):
    path = Path(path).resolve()
    spec = json.loads(path.read_text())
    if spec.get('version') != 1 or spec.get('process') not in ('laser', 'bending', 'welding'):
        raise ValueError('Expected version 1 and laser, bending or welding process.')
    if not isinstance(spec.get('revision'), int) or spec['revision'] < 1:
        raise ValueError('Revision must be a positive integer.')
    if not spec.get('checks') or not spec.get('sources'):
        raise ValueError('Checks and source evidence are required.')
    keys, ids = set(), set()
    for check in spec['checks']:
        for field in ('key', 'id', 'description', 'gauge', 'source', 'method'):
            if not check.get(field):
                raise ValueError(f'Check requires {field}.')
        if check['key'] in keys or check['id'] in ids:
            raise ValueError('Check keys and displayed IDs must be unique.')
        keys.add(check['key']); ids.add(check['id'])
        for field in ('nominal', 'tolerance'):
            value = check.get(field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise ValueError(f'{field} must be a finite number or null.')
        if check.get('tolerance') is not None and check['tolerance'] < 0:
            raise ValueError('Tolerance must be nonnegative.')
        if spec['process'] == 'laser' and check.get('group') not in ('setup', 'hourly'):
            raise ValueError(f"Laser check {check['key']} needs group setup or hourly.")
    geometry = relative(path.parent, spec['drawing']['geometry']).read_bytes()
    for source in spec['sources']:
        actual = digest(relative(path.parent, source['path']).read_bytes())
        if actual != source['sha256']:
            raise ValueError('Source changed: remeasure and update evidence before preview.')
    layout_path = relative(path.parent, spec['layout']) if spec.get('layout') else ROOT/'processes'/spec['process']/'layout.json'
    layout = json.loads(layout_path.read_text()) if layout_path.exists() else None
    template = None
    if layout:
        if layout['process'] != spec['process']:
            raise ValueError('Layout belongs to a different process.')
        template = relative(layout_path.parent, layout['template'])
        counts = {}
        for check in spec['checks']:
            group = check.get('group', 'main')
            counts[group] = counts.get(group, 0) + 1
        for group, count in counts.items():
            if group not in layout['groups'] or count > len(layout['groups'][group]):
                raise ValueError(f'No template capacity for {group}: {count} checks; revise the form mapping.')
    stamp = digest(json.dumps(spec, sort_keys=True).encode() + geometry +
                   (layout_path.read_bytes() + template.read_bytes() if layout else b''))
    return path, spec, geometry, layout, template, stamp


def number(value):
    return format(value, '.12g')


def nominal(check):
    if check.get('nominal') is None:
        return '—'
    unit = check.get('unit', 'mm')
    return number(check['nominal']) + ('°' if unit == 'deg' else ' ' + unit)


def limits(check):
    if check.get('tolerance') is not None:
        return '±' + number(check['tolerance']) + ('°' if check.get('unit') == 'deg' else ' ' + check.get('unit', 'mm'))
    return check.get('limits', 'TBC')


def render_svg(spec, geometry):
    drawing = spec['drawing']; width, height = drawing['width'], drawing['height']
    if not (0 < width <= 10000 and 0 < height <= 10000):
        raise ValueError('Drawing dimensions must be within 1..10000.')
    shape = ET.fromstring(geometry)
    allowed_tags = {'svg', 'g', 'path', 'polyline', 'polygon', 'line', 'circle', 'ellipse', 'rect'}
    allowed_attrs = {'viewBox', 'width', 'height', 'x', 'y', 'x1', 'x2', 'y1', 'y2', 'cx', 'cy', 'r', 'rx', 'ry', 'd', 'points', 'transform', 'fill', 'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin', 'opacity', 'fill-rule', 'vector-effect'}
    for element in shape.iter():
        if element.tag.split('}')[-1] not in allowed_tags:
            raise ValueError('Geometry must contain only vector shapes, no text/scripts/images.')
        for key, value in element.attrib.items():
            if key not in allowed_attrs or 'url(' in value.lower():
                raise ValueError('Unsupported SVG attribute or external resource.')
    if shape.get('viewBox') != f'0 0 {width} {height}':
        raise ValueError('Geometry viewBox must match drawing dimensions exactly.')
    root = ET.Element(f'{{{SVG}}}svg', {'viewBox': f'0 0 {width} {height}', 'width':str(width), 'height':str(height)})
    ET.SubElement(root, f'{{{SVG}}}rect', {'width':'100%', 'height':'100%', 'fill':'white'})
    root.extend(list(shape))
    checks = {c['key']:c for c in spec['checks']}
    def element(parent, tag, **attrs):
        return ET.SubElement(parent, f'{{{SVG}}}{tag}', {k.replace('_','-'):str(v) for k,v in attrs.items()})
    def line(parent, a, b, thin=False):
        element(parent, 'line', x1=a[0], y1=a[1], x2=b[0], y2=b[1], stroke='#365668', stroke_width=1 if thin else 2)
    for dimension in drawing['dimensions']:
        check = checks[dimension['check']]
        if check.get('nominal') is None:
            raise ValueError('A dimension needs a measured nominal.')
        group = element(root, 'g', data_check=check['key'])
        kind = dimension['kind']
        if kind in ('horizontal', 'vertical'):
            a,b=dimension['a'],dimension['b']; offset=dimension['offset']
            if kind=='horizontal':
                ends=[(a[0],offset),(b[0],offset)]; value_pos=((a[0]+b[0])/2,offset)
            else:
                ends=[(offset,a[1]),(offset,b[1])]; value_pos=(offset+25,(a[1]+b[1])/2)
            for point,end in zip((a,b),ends):
                line(group,point,end,True)
                line(group,(end[0]-4,end[1]+5),(end[0]+4,end[1]-5))
            line(group,*ends)
        elif kind=='angle':
            if check.get('unit')!='deg':raise ValueError('Angular dimensions require unit deg.')
            cx,cy=dimension['centre']; radius=dimension['radius']
            start,end=map(math.radians,(dimension['start_deg'],dimension['end_deg']))
            a=(cx+radius*math.cos(start),cy+radius*math.sin(start));b=(cx+radius*math.cos(end),cy+radius*math.sin(end))
            sweep=(dimension['end_deg']-dimension['start_deg'])%360
            element(group,'path',d=f'M {a[0]} {a[1]} A {radius} {radius} 0 {int(sweep>180)} 1 {b[0]} {b[1]}',fill='none',stroke='#365668',stroke_width=2)
            for point in (a,b):line(group,(cx,cy),point,True)
            value_pos=dimension['value_xy']
        else:raise ValueError('Dimension kind must be horizontal, vertical or angle.')
        x,y=dimension.get('value_xy',value_pos)
        value=number(check['nominal'])+('°' if check.get('unit')=='deg' else '')
        text_width=len(value)*15+12
        element(group,'rect',x=x-text_width/2,y=y-15,width=text_width,height=30,fill='white')
        text=element(group,'text',x=x,y=y+8,text_anchor='middle',font_family='Arial, sans-serif',font_size=24,fill='#365668')
        text.text=value
        x,y=dimension['badge_xy']
        element(group,'rect',x=x-30,y=y-19,width=60,height=38,rx=8,fill='#FFF0DF',stroke='#A4470B',stroke_width=2)
        text=element(group,'text',x=x,y=y+8,text_anchor='middle',font_family='Arial, sans-serif',font_size=23,fill='#A4470B');text.text=check['id']
    return ET.tostring(root, encoding='unicode')


def logo_data(layout, template):
    if not layout:return ''
    import posixpath
    with ZipFile(template) as archive:
        rels=ET.fromstring(archive.read(layout['drawing']['rels']))
        rel=next(r for r in rels if r.get('Id')==layout['drawing']['logo_rel'])
        name=posixpath.normpath(posixpath.join(posixpath.dirname(layout['drawing']['part']),rel.get('Target')))
        mime='image/png' if name.lower().endswith('.png') else 'image/jpeg'
        return f'data:{mime};base64,'+base64.b64encode(archive.read(name)).decode()


def preview(path):
    path,spec,geometry,layout,template,stamp=load(path)
    svg=render_svg(spec,geometry)
    esc=lambda value:html.escape(str(value),quote=True)
    rows=[]
    last_group=None
    for check in spec['checks']:
        group=check.get('group','main')
        if group!=last_group and group!='main':
            rows.append('<tr class="group"><td colspan="17">'+esc({'setup':'Start of run','hourly':'Hourly'}.get(group,group))+'</td></tr>')
        last_group=group
        values=[check['id'],check['description'],nominal(check),limits(check),check['gauge']]
        rows.append('<tr tabindex="0" data-check="'+esc(check['key'])+'">'+''.join('<td>'+esc(v)+'</td>' for v in values)+'<td></td>'*12+'</tr>')
    metadata={**spec['part'],'process':spec['process'],'revision':spec['revision'],'fingerprint':stamp,'check_labels':{c['key']:c['id'] for c in spec['checks']}}
    content=(ROOT/'scripts'/'preview.html').read_text()
    tokens={'TITLE':esc(spec['part']['name']), 'PART':esc(spec['part']['number']), 'PROCESS':esc(spec['process'].title()),'REVISION':str(spec['revision']),
            'ROWS':''.join(rows),'DRAWING':svg,'LOGO':logo_data(layout,template),'META':json.dumps(metadata).replace('<','\\u003c'),
            'SAMPLES':''.join('<th>'+str(i)+'</th>' for i in range(1,13)), 'EXPORT_NOTE':'' if layout else 'Welding Excel requires your company template and layout mapping.'}
    for key,value in tokens.items():content=content.replace('{{'+key+'}}',value)
    if len(content.encode())>=1000000:raise ValueError('HTML exceeds the 1,000,000-byte limit. Simplify geometry without dropping required content.')
    out=path.parent/f'preview-r{spec["revision"]}.html'
    if out.exists() and out.read_text()!=content:raise ValueError('This revision already exists with different content; increment revision.')
    out.write_text(content)
    (path.parent/f'drawing-r{spec["revision"]}.svg').write_text(svg)
    return out


def snapshot(path):
    path,spec,geometry,layout,template,stamp=load(path)
    html_path=path.parent/f'preview-r{spec["revision"]}.html'
    svg_path=path.parent/f'drawing-r{spec["revision"]}.svg'
    if not html_path.exists() or not svg_path.exists():raise ValueError('Generate and review this revision before approval/export.')
    if svg_path.read_text()!=render_svg(spec,geometry):raise ValueError('Drawing is stale; revise the preview.')
    if stamp not in html_path.read_text():raise ValueError('Preview is stale; increment revision and regenerate.')
    return {'process':spec['process'],'revision':spec['revision'],'fingerprint':stamp,'html_sha256':digest(html_path.read_bytes()),'svg_sha256':digest(svg_path.read_bytes())}


def approve(path,note):
    if not note.strip():raise ValueError('Record the actual approval wording.')
    record={**snapshot(path),'user_note':note}
    target=Path(path).resolve().parent/'approval.json'
    target.write_text(json.dumps(record,indent=2));return target


def export(path):
    path,spec,geometry,layout,template,stamp=load(path)
    record_path=path.parent/'approval.json'
    if not record_path.exists():raise ValueError('No approval for final Excel. Review the HTML first.')
    record=json.loads(record_path.read_text())
    if any(record.get(k)!=v for k,v in snapshot(path).items()):raise ValueError('Approval is stale; review the current revision.')
    if not layout:raise ValueError('Company template and layout required for this process.')
    from export_xlsx import build
    return build(path,spec,layout,template)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['preview','approve','export']);parser.add_argument('spec');parser.add_argument('--note',default='')
    args=parser.parse_args()
    try:
        result=approve(args.spec,args.note) if args.command=='approve' else globals()[args.command](args.spec)
        print(result)
    except KeyError as error:
        parser.exit(1,f'ICL: missing field or unknown check key {error}\n')
    except (ValueError,FileNotFoundError,ImportError,ET.ParseError) as error:
        parser.exit(1,f'ICL: {error}\n')


if __name__=='__main__':main()
