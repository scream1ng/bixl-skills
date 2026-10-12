#!/usr/bin/env python3
"""BOM -> auditable graph -> HTML review -> approval-bound Excel PFC."""
import argparse, base64, copy, datetime, hashlib, html, json, re, shutil
import sys, textwrap, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
S = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS = {'s': S}

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path, obj): Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False)+'\n')
def read(path): return json.loads(Path(path).read_text())
def q(s): return html.escape(str(s), quote=True)

def spreadsheet(path):
    """Read OOXML values without executing macros; preserve source coordinates."""
    with zipfile.ZipFile(path) as z:
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            strings = [''.join(e.itertext()) for e in ET.fromstring(z.read('xl/sharedStrings.xml'))]
            # Only rich-text t nodes, excluding phonetic annotations.
            strings = [''.join(t.text or '' for t in e.findall('.//s:t', NS)) for e in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        rels = {r.get('Id'):r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        result = []
        for sheet in ET.fromstring(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet', NS):
            target = rels[sheet.get('{'+R+'}id')]
            member = target.lstrip('/') if target.startswith('/') else 'xl/'+target
            rows = []
            for inferred_row,row in enumerate(ET.fromstring(z.read(member)).findall('s:sheetData/s:row', NS),1):
                cells = {};column_index=0
                for c in row.findall('s:c', NS):
                    column_index+=1
                    if c.get('r'):
                        column=re.sub(r'\d','',c.get('r'));column_index=0
                        for letter in column:column_index=column_index*26+ord(letter)-64
                    else:
                        ci=column_index;column=''
                        while ci:ci,rem=divmod(ci-1,26);column=chr(65+rem)+column
                    v = c.find('s:v', NS); t=c.get('t'); f=c.find('s:f', NS)
                    value = v.text if v is not None else None
                    if t == 's' and value is not None: value=strings[int(value)]
                    elif t == 'inlineStr': value=''.join(x.text or '' for x in c.findall('.//s:t', NS))
                    elif value is not None and t not in ('str','e'):
                        try: value=float(value); value=int(value) if value.is_integer() else value
                        except ValueError: pass
                    if f is not None and value is None: raise ValueError('Formula has no cached value at '+sheet.get('name')+'!'+c.get('r'))
                    cells[column]=value
                rows.append((int(row.get('r',inferred_row)),cells))
            result.append((sheet.get('name'),rows))
        return result

def number(v):
    try: return float(v)
    except (TypeError,ValueError): return None

def family(row):
    v=' '.join(str(row.get(k,'') or '') for k in ('resource','description','operation')).lower()
    if 'laser' in v: return 'laser','Laser Cut Blank'
    if 'pressbrake' in v or 'press brake' in v: return 'bend','Bend'
    if 'weld' in v or 'mig' in v or 'tig' in v: return 'weld','Weld'
    if 'electrocoat' in v or 'e-coat' in v: return 'ecoat',"E'Coat"
    if 'powder' in v: return 'powdercoat','Powdercoat'
    return 'other',str(row.get('operation') or row.get('description') or 'Process — TBC')

def build(bom, job, sheet_name=None):
    sheets=spreadsheet(bom); choices=[]
    for name,rows in sheets:
        if sheet_name and name!=sheet_name: continue
        for idx,(rn,cells) in enumerate(rows[:20]):
            headers={str(v or '').strip().lower():col for col,v in cells.items()}
            if {'type','level','item/resource','description'}<=set(headers): choices.append((name,rows[idx+1:],headers)); break
    if len(choices)!=1: raise ValueError('Select exactly one BOM sheet using --sheet; found '+str(len(choices)))
    name,rows,headers=choices[0]; nodes=[]; stack={}; issues=[]; unsupported=[]; allrows=[]
    keys={'type':'type','level':'level','item/resource':'resource','description':'description','operation':'operation','cost group':'group','unit':'unit','consumption per lot size':'consumption','lot size quantity':'lot'}
    for rn,c in rows:
        if not c.get(headers['type']): continue
        r={k:c.get(headers[h]) for h,k in keys.items() if h in headers}; r['row']=rn;r['sheet']=name
        r['type']=str(r['type']).strip();r['resource']=str(r.get('resource') or '').strip()
        level=number(r.get('level'))
        if level is None or level<0 or int(level)!=level: raise ValueError('Invalid BOM level at row '+str(rn))
        level=int(level);r['level']=level;allrows.append(r)
        parents=[n for lev,n in stack.items() if lev<level]; parent=max(parents,key=lambda n:n['level']) if parents else None
        if r['type'].lower() in ('production','bom'):
            n={**r,'key':'bom-'+str(rn),'children':[],'rows':[],'parent':parent['key'] if parent else None}
            if parent is None and nodes: raise ValueError('Multiple/disconnected BOM roots at row '+str(rn))
            if parent and level!=parent['level']+1: raise ValueError('Skipped BOM level at row '+str(rn))
            if parent: parent['children'].append(n)
            nodes.append(n);stack={k:v for k,v in stack.items() if k<level};stack[level]=n
        elif parent:
            if level!=parent['level']+1: raise ValueError('Resource level does not match its parent at row '+str(rn))
            parent['rows'].append(r)
        else: raise ValueError('Resource without owning BOM at row '+str(rn))
    if not nodes or nodes[0]['type'].lower()!='production': raise ValueError('Expected one Production root')
    root=nodes[0]; graph=[];edges=[]; counter=0
    def add(key,item,label,kind,rows,**extra):
        graph.append({'key':key,'item':str(item),'label':str(label),'kind':kind,'source_rows':rows,**extra});return key
    def walk(n):
        nonlocal counter
        incoming=[walk(child) for child in n['children']]
        materials=[]
        for r in n['rows']:
            if r['type'].lower()=='item':
                qty=None
                if number(r.get('consumption')) is not None and number(r.get('lot')) and str(r.get('unit','')).lower() in ('ea','each'):
                    qty=number(r['consumption'])/number(r['lot'])
                desc=str(r.get('description') or 'Item — TBC')
                ispack=bool(re.search(r'carton|rsc\b|ribbon|label|pallet|pack',desc,re.I))
                ishardware=bool(re.search(r'stud|nut\b|bolt|screw|washer|rivet|bush',desc,re.I))
                if 'no cost' in desc.lower() or 'blank - material' in desc.lower():
                    issues.append({'key':'source-'+str(r['row']),'summary':n['resource']+': confirm material.','text':n['resource']+': material specification is missing in the BOM. Confirm shared sheet or actual material.'})
                key=add('item-'+str(r['row']),r['resource'],desc,'packaging' if ispack else 'hardware' if ishardware else 'material',[r['row']],quantity=qty,unit=r.get('unit'),parent=n['key'])
                materials.append(key)
        operations=[]
        for r in n['rows']:
            typ=r['type'].lower()
            if typ=='process' and str(r.get('group','')).upper()=='MACH':
                # Setup and operator time are evidence of the same physical operation.
                fam,label=family(r)
                evidence=[x['row'] for x in n['rows'] if x['type'].lower() in ('setup','process') and (x['resource']==r['resource'] or str(x.get('group','')).upper()=='LAB')]
                operations.append((fam,label,evidence))
            elif typ=='service':
                fam,label=family(r);operations.append((fam,label,[r['row']]))
            elif typ not in ('item','setup','process','surcharge'):
                unsupported.append(r['row'])
        if not operations:
            if any(r['type'].lower() in ('process','setup') for r in n['rows']):
                issues.append({'key':n['key'],'text':n['resource']+': no machine process identified; confirm operation.'})
            operations=[('other','Process — TBC',[n['row']])]
        if len(operations)>1:
            issues.append({'key':n['key'],'text':n['resource']+': multiple operations use BOM row order provisionally; confirm route order and which operation consumes each input.'})
        last=None
        for seq,(fam,label,evidence) in enumerate(operations):
            pack=(n is root and any(next(g for g in graph if g['key']==m)['kind']=='packaging' for m in materials) and fam=='other' and bool(re.search(r'work\s*bench',label,re.I)))
            if pack:
                fam,label='pack','Pack'
                issues.append({'key':n['key'],'summary':'Confirm Workbench is packing.','text':n['resource']+': Pack is inferred from Workbench and packaging items. Confirm the task is packing.'})
            counter+=1;key=add('op-'+str(n['row'])+'-'+str(seq),n['resource'],label,'operation',evidence,family=fam,op=(seq+1)*10,bom_key=n['key'],quantity=(number(n.get('consumption'))/number(n.get('lot')) if number(n.get('consumption')) is not None and number(n.get('lot')) and str(n.get('unit','')).lower() in ('ea','each') else None),unit=n.get('unit'))
            if last: edges.append({'from':last,'to':key})
            else:
                for inputkey in incoming+materials: edges.append({'from':inputkey,'to':key})
            last=key
        return last
    walk(root)
    # Keep packing consumables together, matching the supplied PFC's pack box.
    for op in [g for g in graph if g.get('family')=='pack']:
        keys=[g['key'] for g in graph if g['kind']=='packaging' and g.get('parent')==op['bom_key']]
        items=[g for g in graph if g['key'] in keys]
        if items:
            op['packaging']=items
            cartons=[g for g in items if re.search(r'carton|rsc\b',g['label'],re.I)]
            if len(cartons)==1 and cartons[0].get('quantity') and cartons[0]['quantity']>0:
                count=1/cartons[0]['quantity']
                op['label']='Pack\nCARTON #'+cartons[0]['item']+'\n'+format(count,'.4g')+' / BOX'
            else:op['label']='Pack'
            graph[:]=[g for g in graph if g['key'] not in keys]
            edges[:]=[e for e in edges if e['from'] not in keys]
    if unsupported: issues.append({'key':'unsupported','text':'Unmapped BOM row types: '+', '.join(map(str,unsupported))+'. Review before export.'})
    # Operation numbers are per component route; assemble main-chain order in the view.
    parents={n['key']:n['parent'] for n in nodes}; leaf=nodes[0]
    while leaf['children']: leaf=leaf['children'][0]
    main=[];cur=leaf
    while cur:
        main.extend(g['key'] for g in graph if g.get('bom_key')==cur['key'])
        cur=next((n for n in nodes if n['key']==cur['parent']),None)
    for i,key in enumerate(main): next(g for g in graph if g['key']==key)['op']=(i+1)*10
    job=Path(job);job.mkdir(parents=True,exist_ok=False)
    src=job/'sources';src.mkdir();target=src/Path(bom).name;shutil.copy2(bom,target)
    spec={'schema_version':1,'revision':1,'number':root['resource'],'name':root['description'],'plant':'TBC','issued_by':'TBC','original_date':None,'revision_date':None,'source':{'path':str(target.relative_to(job)),'sha256':sha(target),'sheet':name},'template_sha256':sha(ROOT/'assets/reference-pfc.xlsx'),'nodes':graph,'edges':edges,'main':main,'operation_numbering':{'basis':'proposed_route_sequence','increment':10,'restart_independent_routes':True,'source':None},'issues':issues,'source_rows':allrows,'history':[],'images':{}}
    save(job/'spec.json',spec);return job/'spec.json'

def valid(spec):
    nodes={n['key']:n for n in spec['nodes']}
    if len(nodes)!=len(spec['nodes']): raise ValueError('Duplicate graph keys')
    for e in spec['edges']:
        if e['from'] not in nodes or e['to'] not in nodes: raise ValueError('Broken graph edge')
    visiting=set();visited=set()
    def dfs(k):
        if k in visiting: raise ValueError('Cycle in process flow')
        if k in visited: return
        visiting.add(k)
        for e in spec['edges']:
            if e['from']==k: dfs(e['to'])
        visiting.remove(k);visited.add(k)
    for k in nodes: dfs(k)
    for k in spec['main']:
        if k not in nodes: raise ValueError('Main route references missing operation')

def digest(spec,path):
    s=copy.deepcopy(spec);s.pop('approval',None);s.pop('preview',None)
    job=Path(path).parent
    if sha(job/spec['source']['path'])!=spec['source']['sha256']: raise ValueError('BOM changed; re-import and review')
    if sha(ROOT/'assets/reference-pfc.xlsx')!=spec['template_sha256']: raise ValueError('Template changed; re-import and review')
    for source in spec.get('additional_sources',[]):
        if sha(job/source['path'])!=source['sha256']:raise ValueError('Additional source changed; re-render and review')
    for image in spec.get('images',{}).values():
        if sha(job/image['path'])!=image['sha256']:raise ValueError('Render changed; update image evidence and review')
    resources=['pfc.py','preview.html','comments.js','drawing.py','render_iso.py','form.py']
    return hashlib.sha256((json.dumps(s,sort_keys=True,ensure_ascii=False)+''.join(sha(ROOT/'scripts'/r) for r in resources)+sha(ROOT/'assets/logo.png')).encode()).hexdigest()

BOX_GROW=(1.3,1.35)  # width, height over the reference form's measured boxes
SYMBOL_GAP=14

def spaced(f):
    """Grow measured boxes about their centres and spread rows down to the legend."""
    top=f['material'][1];last=f['phases']['pack'];bottom=min(p['y'] for p in f['legend'])-16
    ky=min(1.6,(bottom-top-last[3]*BOX_GROW[1])/(last[1]-top))
    def grow(box):
        x,y,w,h=box;nw=w*BOX_GROW[0]
        return [x+(w-nw)/2,top+(y-top)*ky,nw,h*BOX_GROW[1]]
    return grow

def layout(spec):
    """Use the form's slot order and symbol styles, with roomier boxes, inside the page frame."""
    from form import reference
    f=reference();valid(spec);nodes={n['key']:n for n in spec['nodes']};main=spec['main'];pos={};W=f['width'];H=f['height']
    grow=spaced(f)
    slots=[grow(f['phases'][k]) for k in ('laser','bend','weld','ecoat','pack')]
    if len(main)>len(slots):raise ValueError('Route exceeds the original single-page form; create an inspected extra-page layout')
    if 1<len(main)<len(slots):
        # Shorter routes use the free page height instead of leaving it empty above the legend.
        y0=slots[0][1];last=slots[4] if nodes[main[-1]].get('family')=='pack' else slots[len(main)-1]
        step=(min(q['y'] for q in f['legend'])-16-last[3]-y0)/(len(main)-1)
        slots=[[x,y0+i*step,w,h] for i,(x,_,w,h) in enumerate(slots[:len(main)])]+slots[len(main):]
    for i,key in enumerate(main):
        box=list(slots[i])
        if nodes[key].get('family')=='pack':box[2:]=slots[4][2:]
        pos[key]=box
    branches=[n for n in spec['nodes'] if n['kind']=='operation' and n['key'] not in main]
    for i,n in enumerate(branches):
        box=grow(f['side']);box[1]+=i*(slots[1][1]-slots[0][1]);pos[n['key']]=box
    hardware_count=0
    for n in spec['nodes']:
        if n['kind']=='operation':continue
        target=next((e['to'] for e in spec['edges'] if e['from']==n['key']),None)
        if n['kind']=='hardware':
            box=grow(f['hardware']);box[1]+=hardware_count*(box[3]+SYMBOL_GAP);hardware_count+=1
        elif target in main:box=grow(f['material'])
        else:box=grow([f['side'][0],f['material'][1],f['side'][2],f['material'][3]])
        pos[n['key']]=box
    for key,box in spec.get('layout',{}).get('boxes',{}).items():
        if key not in nodes or len(box)!=4:raise ValueError('Invalid layout override '+key)
        pos[key]=box
    keys=list(pos)
    for i,k in enumerate(keys):
        x,y,w,h=pos[k]
        if min(x,y)<0 or min(w,h)<=0 or x+w>W or y+h>H:raise ValueError('Box exceeds reference page '+k)
        for l in keys[i+1:]:
            bx,by,bw,bh=pos[l]
            if x<bx+bw and x+w>bx and y<by+bh and y+h>by:raise ValueError('Overlapping boxes '+k+' / '+l+'; revise spec.layout.boxes')
    scene=[]
    def add(kind,**p):scene.append({'type':kind,**p})
    add('frame',x=1,y=1,w=W-2,h=H-2,fill='none',stroke='#000000',stroke_width=2)
    route_left=max(pos[k][0] for k in main);route_right=min(pos[k][0]+pos[k][2] for k in main)
    route_axis=(route_left+route_right)/2 if route_left<route_right else None
    for e in spec['edges']:
        a=pos[e['from']];b=pos[e['to']];aw,ah=a[2:];bw,bh=b[2:]
        if nodes[e['from']]['kind']=='hardware':points=[[a[0]+aw/2,a[1]+ah],[a[0]+aw/2,b[1]+bh/2],[b[0],b[1]+bh/2]]
        elif a[0]+aw/2<b[0] and a[1]>=b[1]:
            mid=(a[0]+aw+b[0])/2
            points=[[a[0]+aw,a[1]+ah/2],[mid,a[1]+ah/2],[mid,b[1]+bh/2],[b[0],b[1]+bh/2]]
        elif a[0]>b[0]+bw:points=[[a[0]+aw/2,a[1]+ah],[a[0]+aw/2,b[1]+bh/2],[b[0]+bw,b[1]+bh/2]]
        else:
            left=max(a[0]+3,b[0]+3);right=min(a[0]+aw-3,b[0]+bw-3)
            if left<right:
                axis=route_axis if e['to'] in main and route_axis is not None and left<=route_axis<=right else (left+right)/2
                points=[[axis,a[1]+ah],[axis,b[1]]]
            else:
                mid=(a[1]+ah+b[1])/2
                points=[[a[0]+aw/2,a[1]+ah],[a[0]+aw/2,mid],[b[0]+bw/2,mid],[b[0]+bw/2,b[1]]]

        add('path',points=points,stroke='#4F81BD',stroke_width=2)
    for n in spec['nodes']:
        x,y,w,h=pos[n['key']];label=n['label']
        if n.get('quantity') is not None and n['kind']=='hardware':label+=' (x '+format(n['quantity'],'.4g')+')'
        lines=[n['item']]
        for paragraph in label.splitlines():lines+=textwrap.wrap(paragraph,max(15,int((w-6)/7)))
        if n['kind']=='operation' and n.get('family')!='pack':lines+=['Operation '+str(n['op'])]
        lines=n.get('display_lines',lines)
        if n.get('family')=='pack':lines=[line.upper() if line.strip().lower()=='pack' else line for line in lines]
        template=n.get('family','laser') if n['kind']=='operation' else 'hardware' if n['kind']=='hardware' else 'material'
        if template not in f['text_templates']:template='laser'
        add('rect',x=x,y=y,w=w,h=h,fill='#fff',stroke='#000000',stroke_width=1,key=n['key'])
        add('text',x=x+3,y=y+13.4,w=w-6,h=h,lines=lines,key=n['key'],font_size=13.333333,line_height=14,native_box=[x,y,w,h],operation_style=True,source_text=template)
        if template=='pack':scene[-1]['y']=y+22.733333;scene[-1]['line_height']=18.666667
        syms=n.get('symbols',['operation','storage'] if n.get('family')=='pack' else ['operation','inspection','storage'] if n['kind']=='operation' else ['storage'])
        for i,sym in enumerate(syms):
            proto=f['symbols'][sym];sw,sh=proto['size']
            # One bottom row with clear gaps; the text keeps the space above it.
            dx=SYMBOL_GAP-4+sum(f['symbols'][p]['size'][0]+SYMBOL_GAP for p in syms[:i]);dy=h-sh-8
            add(sym,x=x+dx,y=y+dy,w=sw,h=sh,fill='#FFC000',stroke='#385D8A',stroke_width=2.666667,source_symbol=True)
    for name,image in spec.get('images',{}).items():
        x,y,w,h=image['box'];key=image['node_key'];parent=image.get('within_node')
        if key not in nodes or min(x,y)<0 or min(w,h)<=0 or x+w>W or y+h>f['legend'][0]['y']-12:raise ValueError('Image exceeds reference page '+name)
        if parent:
            bx,by,bw,bh=pos[parent]
            if x<bx or y<by or x+w>bx+bw or y+h>by+bh:raise ValueError('Image exceeds its process box '+name)
        for k,(bx,by,bw,bh) in pos.items():
            if k==parent:continue
            if x<bx+bw and x+w>bx and y<by+bh and y+h>by:raise ValueError('Image overlaps process box '+name+' / '+k)
        add('image',x=x,y=y,w=w,h=h,key=key,image_key=name)
        if image.get('caption'):add('text',x=x,y=y+h+14,w=w,h=18,lines=[image['caption']],font_size=12,line_height=12,key=key)
    for primitive in f['legend']:scene.append({**primitive,'legend':True})
    return {'width':W,'height':H,'items':scene,'boxes':pos,'reference_form':True}

def bind_images(scene,spec,job):
    for p in scene['items']:
        if p['type']=='image':
            i=spec['images'][p['image_key']];path=Path(job)/i['path']
            if sha(path)!=i['sha256']:raise ValueError('Render changed; re-render and review')
            p['data_url']='data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()
    return scene

def svg(scene):
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{scene["width"]}" height="{scene["height"]}" viewBox="0 0 {scene["width"]} {scene["height"]}" role="img" aria-label="Process flow chart"><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M1 1 L8 5 L1 9" fill="none" stroke="#4F81BD" stroke-width="1.5"/></marker></defs>']
    for p in scene['items']:
        t=p['type'];attrs=' data-check="'+q(p['key'])+'"' if p.get('key') else ''
        if t=='path':out.append('<polyline points="'+' '.join(str(x)+','+str(y) for x,y in p['points'])+'" fill="none" stroke="'+p.get('stroke','#4F81BD')+'" stroke-width="'+str(p.get('stroke_width',2))+'" marker-end="url(#arrow)"/>');continue
        x,y,w,h=[p[k] for k in ('x','y','w','h')]
        if t=='image':out.append(f'<image x="{x}" y="{y}" width="{w}" height="{h}" href="{q(p["data_url"])}" preserveAspectRatio="xMidYMid meet"{attrs}/>')
        elif t in ('rect','frame'):out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{p.get("fill","white")}" stroke="{p.get("stroke","#000")}" stroke-width="{p.get("stroke_width",1)}"{attrs}/>')
        elif t=='text':
            tx=x if p.get('align')=='left' else x+w/2;align='start' if p.get('align')=='left' else 'middle'
            out.append(f'<text x="{tx}" y="{y}" text-anchor="{align}" font-family="Arial" font-size="{p.get("font_size",13.333333)}" fill="#000"{attrs}>')
            for i,line in enumerate(p['lines']):
                style=' font-style="italic" text-decoration="underline"' if p.get('operation_style') and line.startswith('Operation ') else ''
                out.append(f'<tspan x="{tx}" dy="{0 if i==0 else p.get("line_height",14)}"{style}>{q(line)}</tspan>')
            out.append('</text>')
        elif t=='operation':out.append(f'<ellipse cx="{x+w/2}" cy="{y+h/2}" rx="{w/2}" ry="{h/2}" fill="#FFC000" stroke="#385D8A" stroke-width="2.6667"/>')
        elif t=='inspection':out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#FFC000" stroke="#385D8A" stroke-width="2.6667"/>')
        elif t=='storage':out.append(f'<path d="M{x} {y}h{w}l{-w/2} {h}Z" fill="#FFC000" stroke="#385D8A" stroke-width="2.6667"/>')
        elif t=='transport':out.append(f'<path d="M{x} {y+h/4}h{w*.6}v{-h/4}l{w*.4} {h/2}-{w*.4} {h/2}v{-h/4}H{x}Z" fill="#FFC000" stroke="#385D8A" stroke-width="2.6667"/>')
        elif t=='delay':out.append(f'<path d="M{x} {y}h{w/2}a{w/2} {h/2} 0 0 1 0 {h}H{x}Z" fill="#FFC000" stroke="#385D8A" stroke-width="2.6667"/>')
    return ''.join(out)+'</svg>'

def preview(path):
    path=Path(path);spec=read(path);scene=bind_images(layout(spec),spec,path.parent);fp=digest(spec,path)
    meta={'process':'pfc','number':spec['number'],'name':spec['name'],'revision':spec['revision'],'fingerprint':fp,'check_labels':{n['key']:n['item']+' — '+n['label'] for n in spec['nodes']}}
    logo='data:image/png;base64,'+base64.b64encode((ROOT/'assets/logo.png').read_bytes()).decode()
    fields={'TITLE':q(spec['name']),'REVISION':str(spec['revision']),'PART':q(spec['number']),'PROCESS':'PFC','DRAWING':svg(scene),'LOGO':logo,'META':json.dumps(meta,ensure_ascii=False).replace('<','\\u003c'),'COMMENTS_SCRIPT':(ROOT/'scripts/comments.js').read_text(),'EXPORT_NOTE':'<br>'.join(q(i['text']) for i in spec['issues']) or 'Review the flow, branches and operation labels, then approve in chat.','HEADER':f'<b>IXL Part Number:</b> {q(spec["number"])}<br><b>Part / Description:</b> {q(spec["name"])}<br><b>Plant:</b> {q(spec["plant"])} &nbsp; <b>Issued by:</b> {q(spec["issued_by"])}<br><b>Date (Orig.):</b> {q(spec.get("original_date") or "TBC")} &nbsp; <b>Date (rev.):</b> {q(spec.get("revision_date") or "TBC")}','SOURCE_NOTE':'Source: '+q(Path(spec['source']['path']).name)+' · '+q(spec['source']['sheet'])}
    template=(ROOT/'scripts/preview.html').read_text()
    fields['REVIEW_NOTES']=('<div class="review-notes"><strong>To confirm</strong><ul>'+''.join('<li>'+q(i.get('summary') or i['text'])+'</li>' for i in spec['issues'])+'</ul></div>') if spec['issues'] else ''
    for k,v in fields.items():template=template.replace('{{'+k+'}}',v)
    if re.search(r'\{\{[A-Z_]+\}\}',template):raise ValueError('Unresolved preview token')
    if len(template.encode())>=1_000_000:raise ValueError('Preview exceeds 1 MB')
    out=path.parent/f'preview-r{spec["revision"]}.html';out.write_text(template)
    (path.parent/'preview.html').write_text(template)
    save(path.parent/'scene.json',scene)
    old=spec.get('preview');spec['preview']={'fingerprint':fp,'sha256':sha(out),'path':out.name}
    if old!=spec['preview']:spec.pop('approval',None)
    save(path,spec);return out

def approve(path,note):
    path=Path(path);spec=read(path)
    if not note.strip():raise ValueError('Record actual user approval wording')
    if not spec.get('preview') or spec['preview']['fingerprint']!=digest(spec,path):raise ValueError('Regenerate and review the current preview first')
    if sha(path.parent/spec['preview']['path'])!=spec['preview']['sha256']:raise ValueError('Preview changed')
    spec['approval']={'wording':note,'fingerprint':spec['preview']['fingerprint'],'preview_sha256':spec['preview']['sha256'],'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};save(path,spec)

def export(path):
    path=Path(path).resolve();spec=read(path);fp=digest(spec,path)
    if spec.get('approval',{}).get('fingerprint')!=fp:raise ValueError('Explicit approval of the current preview is required')
    if sha(path.parent/spec['preview']['path'])!=spec['approval']['preview_sha256']:raise ValueError('Approved HTML changed')
    scene=layout(spec);save(path.parent/'scene.json',scene)
    from drawing import finish
    out=path.parent/f'{spec["number"]}-PFC-r{spec["revision"]}.xlsx'
    finish(ROOT/'assets/reference-pfc.xlsx',out,spec,scene,ROOT)
    return out

def main():
    a=argparse.ArgumentParser();s=a.add_subparsers(dest='command',required=True)
    p=s.add_parser('import');p.add_argument('bom');p.add_argument('--job',required=True);p.add_argument('--sheet')
    for c in ('preview','approve','export'):
        p=s.add_parser(c);p.add_argument('spec')
        if c=='approve':p.add_argument('--note',required=True)
    args=a.parse_args()
    try:
        if args.command=='import':out=build(args.bom,args.job,args.sheet)
        elif args.command=='preview':out=preview(args.spec)
        elif args.command=='approve':approve(args.spec,args.note);out='Approval recorded'
        else:out=export(args.spec)
        print(out)
    except (ValueError,OSError) as e:print(str(e),file=sys.stderr);sys.exit(1)
if __name__=='__main__':main()
