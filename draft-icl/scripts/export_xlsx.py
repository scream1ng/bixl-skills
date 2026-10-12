"""Patch the chosen company form without round-tripping unrelated workbook features."""
import copy
import posixpath
from datetime import date
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
from icl import limits, nominal
from presentation import caption
from form_layout import compact, print_setup

M='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
D='http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P='http://schemas.openxmlformats.org/package/2006/relationships'
q=lambda name:'{'+M+'}'+name


def col_index(ref):
    result=0
    for char in ref:
        if char.isalpha():result=result*26+ord(char)-64
    return result


def put(root,ref,value):
    data=root.find(q('sheetData'));row_num=int(''.join(c for c in ref if c.isdigit()))
    row=next((r for r in data if r.get('r')==str(row_num)),None)
    if row is None:
        row=E.SubElement(data,q('row'),r=str(row_num));data[:]=sorted(data,key=lambda r:int(r.get('r')))
    cell=next((c for c in row if c.get('r')==ref),None)
    if cell is None:
        cell=E.SubElement(row,q('c'),r=ref);row[:]=sorted(row,key=lambda c:col_index(c.get('r')))
    for child in list(cell):
        if child.tag in (q('v'),q('is'),q('f')):cell.remove(child)
    cell.attrib.pop('t',None)
    if value is None or value=='':return cell
    if isinstance(value,(float,int)):
        E.SubElement(cell,q('v')).text=str(value)
    else:
        cell.set('t','inlineStr');text=E.SubElement(E.SubElement(cell,q('is')),q('t'))
        text.set('{http://www.w3.org/XML/1998/namespace}space','preserve');text.text=str(value)
    return cell


def serialized(root):return E.tostring(root,encoding='utf-8',xml_declaration=True)


def scrub(parts):
    """Drop source-part leftovers no visible cell shows: unused shared strings, orphaned images, thumbnail and personal properties."""
    ct='[Content_Types].xml';types=E.fromstring(parts[ct])
    sheets=[n for n in parts if n.startswith('xl/worksheets/') and n.endswith('.xml')]
    if 'xl/sharedStrings.xml' in parts:
        sst=E.fromstring(parts['xl/sharedStrings.xml']);items=list(sst);mapping={}
        roots={n:E.fromstring(parts[n]) for n in sheets}
        for root in roots.values():
            for cell in root.iter(q('c')):
                if cell.get('t')=='s':
                    value=cell.find(q('v'));value.text=str(mapping.setdefault(int(value.text),len(mapping)))
        sst[:]=[items[old] for old,_ in sorted(mapping.items(),key=lambda pair:pair[1])]
        sst.set('count',str(len(mapping)));sst.set('uniqueCount',str(len(mapping)))
        parts['xl/sharedStrings.xml']=serialized(sst)
        for name,root in roots.items():parts[name]=serialized(root)
    for name in [n for n in parts if n.startswith('xl/drawings/_rels/')]:
        drawing=E.fromstring(parts['xl/drawings/'+posixpath.basename(name)[:-5]])
        used={b.get('{'+R+'}embed') for b in drawing.iter('{'+A+'}blip')}
        rels=E.fromstring(parts[name])
        for rel in list(rels):
            if rel.get('Type')==R+'/image' and rel.get('Id') not in used:rels.remove(rel)
        parts[name]=serialized(rels)
    def targets():
        for name in [n for n in parts if n.endswith('.rels')]:
            base=posixpath.dirname(posixpath.dirname(name))
            for rel in E.fromstring(parts[name]):
                target=rel.get('Target','')
                yield target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(base,target))
    root_rels=E.fromstring(parts['_rels/.rels'])
    for rel in list(root_rels):
        if rel.get('Target','').lstrip('/') in ('docProps/thumbnail.emf','docProps/custom.xml'):root_rels.remove(rel)
    parts['_rels/.rels']=serialized(root_rels)
    referenced=set(targets())
    for name in [n for n in parts if n.startswith('xl/media/') or n in ('docProps/thumbnail.emf','docProps/custom.xml')]:
        if name not in referenced:
            del parts[name]
            for item in list(types):
                if item.get('PartName','').lstrip('/')==name:types.remove(item)
    parts[ct]=serialized(types)
    if 'docProps/core.xml' in parts:
        core=E.fromstring(parts['docProps/core.xml'])
        for element in core:
            if element.tag.split('}')[-1] in ('creator','lastModifiedBy','lastPrinted'):element.text=''
        parts['docProps/core.xml']=serialized(core)


def build(path,spec,layout,template):
    import cairosvg
    svg=path.parent/f'drawing-r{spec["revision"]}.svg'
    png=cairosvg.svg2png(bytestring=svg.read_bytes())
    with ZipFile(template) as z:original={n:z.read(n) for n in z.namelist()}
    parts=dict(original);sheet=E.fromstring(parts[layout['sheet']]);styles=E.fromstring(parts['xl/styles.xml'])
    layout,last=compact(sheet,layout,spec['checks'],styles)
    xfs=styles.find(q('cellXfs'));style_cache={}
    for ref in layout['clear_cells']:put(sheet,ref,None)
    for row in layout['clear_rows']:
        for col in ('B','C','E','G'):put(sheet,f'{col}{row}',None)
    for ref,value in layout['fixed_cells'].items():put(sheet,ref,value)
    metadata={**spec['part'],'revision':str(spec['revision'])}
    for ref,field in layout['metadata'].items():
        value=metadata.get(field,'TBC')
        if field=='date':value=(date.fromisoformat(value)-date(1899,12,30)).days
        put(sheet,ref,value)
    slots={key:iter(rows) for key,rows in layout['groups'].items()}
    for check in spec['checks']:
        row=next(slots[check.get('group','main')]);cell=put(sheet,f'B{row}',check['id'])
        old_style=cell.get('s','0')
        if old_style not in style_cache:
            style=copy.deepcopy(xfs[int(old_style)]);alignment=style.find(q('alignment'))
            if alignment is None:alignment=E.SubElement(style,q('alignment'))
            alignment.set('horizontal','center');alignment.set('vertical','center');style.set('applyAlignment','1')
            style_cache[old_style]=str(len(xfs));xfs.append(style)
        cell.set('s',style_cache[old_style])
        description=caption(check,{c['key']:c for c in spec['checks']})
        for col,value in [('C',description),('E',limits(check)),('G',check['gauge'])]:put(sheet,f'{col}{row}',value)
    xfs.set('count',str(len(xfs)));parts['xl/styles.xml']=serialized(styles)
    parts[layout['sheet']]=serialized(sheet)
    old_sheet=E.fromstring(original[layout['sheet']])
    for tag in ('cols','pageMargins'):
        old,new=old_sheet.find(q(tag)),sheet.find(q(tag))
        assert (E.tostring(old) if old is not None else None)==(E.tostring(new) if new is not None else None),tag

    history=E.fromstring(parts[layout['history']])
    for ref,value in [('B1',spec['part']['number']),('B2',spec['part'].get('customer_number','')),('B3',spec['part']['name'])]:put(history,ref,value)
    records=spec.get('history',[])+[{'date':spec['part']['date'],'revision':str(spec['revision']),'change':spec.get('change','Inspection plan'),'author':spec.get('author','')}]
    prototype=copy.deepcopy(history.find(q('sheetData')+'/'+q('row')+'[@r="15"]'))
    for row in range(16,6+len(records)):
        if history.find(q('sheetData')+'/'+q('row')+f'[@r="{row}"]')is None and prototype is not None:
            clone=copy.deepcopy(prototype);clone.set('r',str(row))
            for cell in clone:
                import re
                cell.set('r',re.sub(r'\d+$',str(row),cell.get('r')))
                for node in list(cell):cell.remove(node)
                cell.attrib.pop('t',None)
            history.find(q('sheetData')).append(clone)
    for row in range(6,max(16,6+len(records))):
        for col in 'ABCD':put(history,f'{col}{row}',None)
    for row,record in enumerate(records,6):
        for col,key in [('A','date'),('B','revision'),('C','change'),('D','author')]:
            value=record.get(key,'')
            if key=='date':value=(date.fromisoformat(value)-date(1899,12,30)).days
            put(history,f'{col}{row}',value)
    dimension=history.find(q('dimension'))
    if dimension is not None:
        bounds=dimension.get('ref').split(':');end=bounds[-1]
        history_last=max(int(row.get('r'))for row in history.find(q('sheetData')))
        dimension.set('ref',bounds[0]+':'+''.join(c for c in end if c.isalpha())+str(history_last))
    parts[layout['history']]=serialized(history)

    config=layout['drawing'];drawing=E.fromstring(parts[config['part']])
    for anchor in list(drawing):
        if not any(b.get('{'+R+'}embed')==config['logo_rel'] for b in anchor.iter('{'+A+'}blip')):drawing.remove(anchor)
    anchor=E.SubElement(drawing,'{'+D+'}oneCellAnchor')
    origin=E.SubElement(anchor,'{'+D+'}from')
    for tag,value in [('col',0),('colOff',0),('row',config['row']),('rowOff',0)]:E.SubElement(origin,'{'+D+'}'+tag).text=str(value)
    w,h=config['width_px'],config['height_px'];aspect=spec['drawing']['width']/spec['drawing']['height']
    w=min(w,h*aspect);h=w/aspect
    E.SubElement(anchor,'{'+D+'}ext',cx=str(round(w*9525)),cy=str(round(h*9525)))
    picture=E.SubElement(anchor,'{'+D+'}pic');nv=E.SubElement(picture,'{'+D+'}nvPicPr')
    ids=[int(n.get('id')) for n in drawing.iter('{'+D+'}cNvPr')]
    E.SubElement(nv,'{'+D+'}cNvPr',id=str(max(ids,default=0)+1),name='ICL approved drawing')
    locks=E.SubElement(nv,'{'+D+'}cNvPicPr');E.SubElement(locks,'{'+A+'}picLocks',noChangeAspect='1')
    fill=E.SubElement(picture,'{'+D+'}blipFill');E.SubElement(fill,'{'+A+'}blip',{'{'+R+'}embed':'rIdICL'})
    E.SubElement(E.SubElement(fill,'{'+A+'}stretch'),'{'+A+'}fillRect')
    props=E.SubElement(picture,'{'+D+'}spPr');E.SubElement(E.SubElement(props,'{'+A+'}prstGeom',prst='rect'),'{'+A+'}avLst')
    E.SubElement(anchor,'{'+D+'}clientData');parts[config['part']]=serialized(drawing)
    rels=E.fromstring(parts[config['rels']])
    for rel in list(rels):
        if rel.get('Id')=='rIdICL':rels.remove(rel)
    E.SubElement(rels,'{'+P+'}Relationship',Id='rIdICL',Type=R+'/image',Target='../media/icl-approved.png')
    parts[config['rels']]=serialized(rels);parts['xl/media/icl-approved.png']=png
    ct='[Content_Types].xml';types=E.fromstring(parts[ct]);C='http://schemas.openxmlformats.org/package/2006/content-types'
    if not any(t.get('Extension')=='png' for t in types):E.SubElement(types,'{'+C+'}Default',Extension='png',ContentType='image/png')
    # A template's obsolete source-part formula may have a calc-chain entry.
    if 'P1' in layout['fixed_cells'] and 'xl/calcChain.xml' in parts:
        chain=E.fromstring(parts['xl/calcChain.xml'])
        for entry in list(chain):
            if entry.get('r')=='P1' and entry.get('i')=='1':chain.remove(entry)
        if len(chain):parts['xl/calcChain.xml']=serialized(chain)
        else:
            del parts['xl/calcChain.xml'];rels_name='xl/_rels/workbook.xml.rels';rels=E.fromstring(parts[rels_name])
            for item in list(rels):
                if item.get('Target','').endswith('calcChain.xml'):rels.remove(item)
            parts[rels_name]=serialized(rels)
            for item in list(types):
                if item.get('PartName','').endswith('calcChain.xml'):types.remove(item)
    parts[ct]=serialized(types);scrub(parts);print_setup(parts,layout,last)
    target=path.parent/f'{spec["process"]}-icl-r{spec["revision"]}.xlsx'
    buffer=BytesIO()
    with ZipFile(buffer,'w',ZIP_DEFLATED) as z:
        for name,data in parts.items():z.writestr(name,data)
    with ZipFile(buffer) as z:
        assert z.testzip() is None
        assert z.read('xl/media/icl-approved.png')==png
        for name in (layout['sheet'],layout['history']):
            assert not E.fromstring(z.read(name)).findall('.//'+q('c')+'[@t="e"]')
    target.write_bytes(buffer.getvalue())
    import json
    from verify_print import verify
    report=verify(target)
    target.with_suffix('.print-settings.json').write_text(json.dumps(report,indent=2), encoding='utf-8')
    return target
