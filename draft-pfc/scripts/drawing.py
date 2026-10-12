"""Native Excel workbook writer: header cells and DrawingML shapes on the reference form."""
import copy, datetime, hashlib, json, re, struct, zipfile
from pathlib import Path
from xml.etree import ElementTree as E

A='http://schemas.openxmlformats.org/drawingml/2006/main'
D='http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing'
S='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P='http://schemas.openxmlformats.org/package/2006/relationships'
C='http://schemas.openxmlformats.org/package/2006/content-types'
for pre,ns in [('a',A),('xdr',D),('r',R)]:E.register_namespace(pre,ns)

def sub(parent,ns,tag,attrs=None,**kwargs):return E.SubElement(parent,'{'+ns+'}'+tag,{**(attrs or {}),**{k:str(v) for k,v in kwargs.items()}})
def xml(root):return E.tostring(root,encoding='utf-8',xml_declaration=True)

def native(scene,scale,top=120):
    root=E.Element('{'+D+'}wsDr');idx=0
    def shape(x,y,w,h,geometry='rect',lines=None,fill=None,line=True,arrow=False,rot=None,font_size=13.333333,line_height=14,operation_style=False,align='ctr'):
        nonlocal idx
        idx+=1;anchor=sub(root,D,'absoluteAnchor');sub(anchor,D,'pos',x=int(x*scale*9525),y=int((y*scale+top)*9525));sub(anchor,D,'ext',cx=max(1,int(w*scale*9525)),cy=max(1,int(h*scale*9525)))
        sp=sub(anchor,D,'sp');nv=sub(sp,D,'nvSpPr');sub(nv,D,'cNvPr',id=idx,name='PFC '+str(idx));sub(nv,D,'cNvSpPr')
        props=sub(sp,D,'spPr');xf=sub(props,A,'xfrm',**({'rot':rot} if rot else {}));sub(xf,A,'off',x=int(x*scale*9525),y=int((y*scale+top)*9525));sub(xf,A,'ext',cx=max(1,int(w*scale*9525)),cy=max(1,int(h*scale*9525)))
        geom=sub(props,A,'prstGeom',prst=geometry);sub(geom,A,'avLst')
        if fill:sub(sub(props,A,'solidFill'),A,'srgbClr',val=fill.lstrip('#'))
        else:sub(props,A,'noFill')
        ln=sub(props,A,'ln',w=19050 if geometry=='line' else 9525)
        if line:sub(sub(ln,A,'solidFill'),A,'srgbClr',val='4F81BD' if geometry=='line' else '000000')
        else:sub(ln,A,'noFill')
        if arrow:sub(ln,A,'tailEnd',type='arrow')
        if lines:
            tb=sub(sp,D,'txBody');sub(tb,A,'bodyPr',wrap='square',anchor='t',lIns='27432',rIns='27432',tIns='22860',bIns='0');sub(tb,A,'lstStyle')
            for text in lines:
                p=sub(tb,A,'p');pp=sub(p,A,'pPr',algn=align);sub(sub(pp,A,'lnSpc'),A,'spcPct',val='100000');run=sub(p,A,'r');rp=sub(run,A,'rPr',lang='en-AU',sz=round(font_size*scale*75));
                if operation_style and text.startswith('Operation '):rp.set('i','1');rp.set('u','sng')
                sub(sub(rp,A,'solidFill'),A,'srgbClr',val='000000');sub(rp,A,'latin',typeface='Arial');sub(run,A,'t').text=text;sub(p,A,'endParaRPr',lang='en-AU')
        sub(anchor,D,'clientData')
    for p in scene['items']:
        t=p['type']
        if t in ('image','frame') or p.get('legend'):continue
        if t=='path':
            pairs=list(zip(p['points'],p['points'][1:]))
            for j,((x1,y1),(x2,y2)) in enumerate(pairs):
                if x1==x2 and y1==y2:continue
                # line geometry orientation, with tail tip at destination.
                old=len(root);shape(min(x1,x2),min(y1,y2),abs(x2-x1),abs(y2-y1),geometry='line',arrow=j==len(pairs)-1)
                xf=root[-1].find('.//{'+A+'}xfrm')
                if x2<x1:xf.set('flipH','1')
                if y2<y1:xf.set('flipV','1')
            continue
        x,y,w,h=[p[k] for k in ('x','y','w','h')]
        if t=='rect':shape(x,y,w,h,fill='#ffffff')
        elif t=='text':
            bx,by,bw,bh=p.get('native_box',[x,y-13,w,max(h,14*len(p['lines']))]);shape(bx,by,bw,bh,lines=p['lines'],line=False,font_size=p.get('font_size',13.333333),line_height=p.get('line_height',14),operation_style=p.get('operation_style',False),align='l' if p.get('align')=='left' else 'ctr')
            if p.get('source_text'):
                from form import reference
                tb=copy.deepcopy(reference()['text_templates'][p['source_text']])
                paragraphs=[para for para in tb.findall('{'+A+'}p') if any((t.text or '').strip() for t in para.iter('{'+A+'}t'))]
                # Retain the template's blank paragraphs and formatting; replace all
                # sample text. Additional labels receive the same regular paragraph.
                for i,para in enumerate(paragraphs):
                    ts=list(para.iter('{'+A+'}t'))
                    for j,t in enumerate(ts):t.text=p['lines'][i] if i<len(p['lines']) and j==0 else ''
                for text in p['lines'][len(paragraphs):]:
                    para=copy.deepcopy(paragraphs[0]);ts=list(para.iter('{'+A+'}t'))
                    for j,t in enumerate(ts):t.text=text if j==0 else ''
                    tb.append(para)
                if scale!=1:
                    for el in tb.iter():
                        if el.get('sz'):el.set('sz',str(round(int(el.get('sz'))*scale)))
                        if el.tag=='{'+A+'}spcPts':el.set('val',str(round(int(el.get('val'))*scale)))
                sp=root[-1].find('{'+D+'}sp');sp.remove(sp.find('{'+D+'}txBody'));sp.append(tb)
        else:
            geometry={'operation':'ellipse','inspection':'rect','storage':'triangle','transport':'rightArrow','delay':'flowChartDelay'}[t]
            shape(x,y,w,h,geometry=geometry,fill='#ffda22' if t=='operation' else '#ffffff',rot='10800000' if t=='storage' else None)
            if p.get('source_symbol'):
                from form import reference
                sp=root[-1].find('{'+D+'}sp');old=sp.find('{'+D+'}spPr');props=copy.deepcopy(reference()['symbols'][t]['sp'].find('{'+D+'}spPr'))
                xf=props.find('{'+A+'}xfrm');xf.find('{'+A+'}off').set('x',str(int(x*scale*9525)));xf.find('{'+A+'}off').set('y',str(int((y*scale+top)*9525)));xf.find('{'+A+'}ext').set('cx',str(int(w*scale*9525)));xf.find('{'+A+'}ext').set('cy',str(int(h*scale*9525)));sp.remove(old);sp.insert(1,props)
    if scene.get('reference_form'):
        from form import reference
        anchor=copy.deepcopy(reference()['legend_anchor'])
        for i,el in enumerate(anchor.iter('{'+D+'}cNvPr'),20000):el.set('id',str(i))
        root.append(anchor)
    return root

def header(sr,data,spec):
    # Fill the form's header cells in place, keeping their styles. Dates use the
    # reference date style, switched to dd/mm/yyyy; missing values read TBC.
    cells={c.get('r'):c for c in sr.iter('{'+S+'}c')}
    def put(ref,value):
        c=cells[ref]
        for child in list(c):c.remove(child)
        c.attrib.pop('t',None)
        if isinstance(value,(int,float)):sub(c,S,'v').text=str(value)
        else:c.set('t','inlineStr');sub(sub(c,S,'is'),S,'t').text=str(value)
    for ref,value in {'G2':spec['number'],'G3':spec['name'],'U1':spec['plant'],'R3':spec.get('issued_by') or 'TBC','X1':1}.items():put(ref,value)
    for ref,key in (('R2','original_date'),('V2','revision_date')):
        date=spec.get(key)
        put(ref,(datetime.date.fromisoformat(date)-datetime.date(1899,12,30)).days if date else 'TBC')
    styles=data['xl/styles.xml'].decode()
    if 'formatCode="dd/mm/yyyy"' not in styles:
        styles=re.sub(r'<numFmts count="(\d+)">',lambda m:f'<numFmts count="{int(m.group(1))+1}"><numFmt numFmtId="165" formatCode="dd/mm/yyyy"/>',styles,count=1)
        xfs=re.search(r'<cellXfs[^>]*>(.*?)</cellXfs>',styles,re.S);items=re.findall(r'<xf [^>]*?(?:/>|>.*?</xf>)',xfs.group(1))
        style=int(cells['R2'].get('s'));items[style]=items[style].replace('numFmtId="15"','numFmtId="165"',1)
        styles=styles[:xfs.start(1)]+''.join(items)+styles[xfs.end(1):]
    data['xl/styles.xml']=styles.encode()

def finish(base,out,spec,scene,skillroot):
    with zipfile.ZipFile(base) as z:data={n:z.read(n) for n in z.namelist()}
    # Shape and cell authoring use the same sheet dimensions. Keep the supplied
    # form's header/grid styles. Default PFC orientation is the reference's portrait.
    sr=E.fromstring(data['xl/worksheets/sheet1.xml']);ns={'s':S}
    header(sr,data,spec)
    rows=sr.find('s:sheetData',ns)
    header_height=sum(float(r.get('ht','12.75'))*96/72 for r in rows if int(r.get('r'))<=3)
    top=header_height if scene.get('reference_form') else header_height+14
    cols=sr.find('s:cols',ns);width=0
    # Preserve the reference's individual header column widths, rather than
    # giving its short date/issuer merges uniform narrow columns.
    for i in range(1,25):
        w=3.7109375
        if cols is not None:
            for c in cols:
                if int(c.get('min'))<=i<=int(c.get('max')):w=float(c.get('width',w));break
        # OOXML column widths already contain the padding allowance. Adding
        # five pixels again makes the native side branch exceed the print area.
        width+=int(((256*w+int(128/7))/256)*7)
    scale=width/scene['width'];total=top+scene['height']*scale
    # Blank drawing grid below the 3-row company header; native shapes carry the text.
    for row in list(rows):
        if int(row.get('r'))>3 and not scene.get('reference_form'):rows.remove(row)
    import math
    count=52 if scene.get('reference_form') else math.ceil(total/17)+2
    if scene.get('reference_form'):
        # Keep the original border-carrying blank cells and their row heights.
        # They form the full A4:X52 outside frame, including the bottom corners.
        for row in list(rows):
            if int(row.get('r'))>count:rows.remove(row)
    else:
        for i in range(4,count+1):sub(rows,S,'row',r=i,ht='12.75',customHeight='1')
    # Schema order: printOptions, pageMargins, pageSetup, headerFooter, ..., drawing.
    header_footer=sr.find('s:headerFooter',ns)
    for tag in ('drawing','legacyDrawing','pageSetup','pageMargins','printOptions','headerFooter','rowBreaks','colBreaks'):
        for el in sr.findall('s:'+tag,ns):sr.remove(el)
    dim=sr.find('s:dimension',ns)
    if dim is not None:dim.set('ref',f'A1:X{count}')
    # Remove source-part body merges before rebuilding the blank grid.
    merges=sr.find('s:mergeCells',ns)
    if merges is not None and not scene.get('reference_form'):
        for m in list(merges):
            first=int(''.join(filter(str.isdigit,m.get('ref').split(':')[0])))
            if first>3:merges.remove(m)
        merges.set('count',str(len(merges)))
    props=sr.find('s:sheetPr',ns)
    if props is None:props=E.Element('{'+S+'}sheetPr');sr.insert(0,props)
    ps=props.find('s:pageSetUpPr',ns)
    if ps is None:ps=sub(props,S,'pageSetUpPr')
    ps.set('fitToPage','1');ps.set('autoPageBreaks','0')
    if scene.get('reference_form'):
        from form import reference
        options=reference()['sheet'].find('{'+S+'}printOptions')
        if options is not None:sr.append(copy.deepcopy(options))
        sr.append(copy.deepcopy(reference()['sheet'].find('{'+S+'}pageMargins')))
    else:sub(sr,S,'pageMargins',left='.3',right='.3',top='.3',bottom='.3',header='.15',footer='.15')
    sub(sr,S,'pageSetup',paperSize='9',orientation='portrait',fitToWidth='1',fitToHeight='1',usePrinterDefaults='0')
    if header_footer is not None:sr.append(header_footer)
    sub(sr,S,'drawing',{'{'+R+'}id':'rIdPfc'})
    data['xl/worksheets/sheet1.xml']=xml(sr)
    rel=E.Element('{'+P+'}Relationships');sub(rel,P,'Relationship',Id='rIdPfc',Type=R+'/drawing',Target='../drawings/drawing-pfc.xml');data['xl/worksheets/_rels/sheet1.xml.rels']=xml(rel)
    draw=native(scene,scale,top)
    # Reuse the company logo only, never template part snapshots.
    logo=(skillroot/'assets/logo.png').read_bytes()
    lw,lh=struct.unpack('>II',logo[16:24]);logo_scale=min(94/lw,31/lh)
    idx=10000;anc=sub(draw,D,'absoluteAnchor');sub(anc,D,'pos',x='95000',y='25000');sub(anc,D,'ext',cx=int(lw*logo_scale*9525),cy=int(lh*logo_scale*9525));pic=sub(anc,D,'pic');nv=sub(pic,D,'nvPicPr');sub(nv,D,'cNvPr',id=idx,name='IXL logo');sub(nv,D,'cNvPicPr');bf=sub(pic,D,'blipFill');sub(bf,A,'blip',{'{'+R+'}embed':'rIdLogo'});sub(sub(bf,A,'stretch'),A,'fillRect');sp=sub(pic,D,'spPr');g=sub(sp,A,'prstGeom',prst='rect');sub(g,A,'avLst');sub(anc,D,'clientData')
    rel=E.Element('{'+P+'}Relationships');sub(rel,P,'Relationship',Id='rIdLogo',Type=R+'/image',Target='../media/pfc-logo.png');data['xl/media/pfc-logo.png']=logo
    render_media=set()
    for i,p in enumerate((p for p in scene['items'] if p['type']=='image'),1):
        image=spec['images'][p['image_key']];job=Path(out).parent;png=(job/image['path']).read_bytes()
        if hashlib.sha256(png).hexdigest()!=image['sha256']:raise ValueError('Unapproved image bytes')
        iw,ih=struct.unpack('>II',png[16:24]);fit=min(p['w']/iw,p['h']/ih);w=iw*fit;h=ih*fit;x=p['x']+(p['w']-w)/2;y=p['y']+(p['h']-h)/2
        anchor=sub(draw,D,'absoluteAnchor');sub(anchor,D,'pos',x=int(x*scale*9525),y=int((y*scale+top)*9525));sub(anchor,D,'ext',cx=int(w*scale*9525),cy=int(h*scale*9525));picture=sub(anchor,D,'pic');nv=sub(picture,D,'nvPicPr');sub(nv,D,'cNvPr',id=10000+i,name=p['image_key']+' isometric');sub(nv,D,'cNvPicPr');bf=sub(picture,D,'blipFill');sub(bf,A,'blip',{'{'+R+'}embed':'rIdRender'+str(i)});sub(sub(bf,A,'stretch'),A,'fillRect');sp=sub(picture,D,'spPr');g=sub(sp,A,'prstGeom',prst='rect');sub(g,A,'avLst');sub(anchor,D,'clientData')
        media='xl/media/pfc-render-'+str(i)+'.png';data[media]=png;render_media.add(media);sub(rel,P,'Relationship',Id='rIdRender'+str(i),Type=R+'/image',Target='../media/'+Path(media).name)
    data['xl/drawings/drawing-pfc.xml']=xml(draw);data['xl/drawings/_rels/drawing-pfc.xml.rels']=xml(rel)
    wb=E.fromstring(data['xl/workbook.xml']);sheet=wb.find('s:sheets/s:sheet',ns);sheet.set('name',('PFC '+spec['number'])[:31]);name=sheet.get('name')
    defs=wb.find('s:definedNames',ns)
    if defs is None:defs=sub(wb,S,'definedNames')
    for d in list(defs):
        if d.get('name') in ('_xlnm.Print_Area','_xlnm.Print_Titles'):defs.remove(d)
    sub(defs,S,'definedName',name='_xlnm.Print_Area',localSheetId='0').text="'"+name.replace("'","''")+f"'!$A$1:$X${count}"
    data['xl/workbook.xml']=xml(wb)
    if 'docProps/app.xml' in data:
        app=E.fromstring(data['docProps/app.xml'])
        for e in app.iter():
            if e.tag.split('}')[-1]=='lpstr' and e.text and e.text.startswith('PFC '):e.text=name
        data['docProps/app.xml']=xml(app)
    # Clean inaccessible source-part artefacts and remove any VBA in XLSX output.
    keep={'xl/drawings/drawing-pfc.xml','xl/drawings/_rels/drawing-pfc.xml.rels','xl/media/pfc-logo.png'}|render_media
    for n in list(data):
        if (n.startswith(('xl/drawings/','xl/media/','xl/printerSettings/')) and n not in keep) or 'vbaProject' in n or 'thumbnail' in n or n=='docProps/custom.xml':del data[n]
    for n in ('xl/_rels/workbook.xml.rels','_rels/.rels'):
        rel=E.fromstring(data[n])
        for r in list(rel):
            if any(t in r.get('Type','') for t in ('vbaProject','thumbnail','custom-properties')):rel.remove(r)
        data[n]=xml(rel)
    ct=E.fromstring(data['[Content_Types].xml'])
    for el in list(ct):
        if el.tag.endswith('Override') and el.get('PartName','').lstrip('/') not in data:ct.remove(el)
        elif el.get('PartName')=='/xl/workbook.xml':el.set('ContentType','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml')
    sub(ct,C,'Override',PartName='/xl/drawings/drawing-pfc.xml',ContentType='application/vnd.openxmlformats-officedocument.drawing+xml')
    if not any(e.get('Extension')=='png' for e in ct):sub(ct,C,'Default',Extension='png',ContentType='image/png')
    data['[Content_Types].xml']=xml(ct)
    # Replace template author metadata rather than crediting the sample's author.
    if 'docProps/core.xml' in data:
        core=E.fromstring(data['docProps/core.xml'])
        for e in core:
            if e.tag.split('}')[-1] in ('creator','lastModifiedBy'):e.text=spec.get('issued_by','TBC')
        data['docProps/core.xml']=xml(core)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for n,v in data.items():z.writestr(n,v)
    # Exact workbook-level verification, without claiming Windows printer validation.
    with zipfile.ZipFile(out) as z:
        texts=[t.text for t in E.fromstring(z.read('xl/drawings/drawing-pfc.xml')).iter('{'+A+'}t')]
        for n in spec['nodes']:
            if n['item'] not in texts:raise ValueError('Missing exported item '+n['item'])
        if any('vbaProject' in n for n in z.namelist()):raise ValueError('Unexpected VBA in XLSX')
    report={'sha256':hashlib.sha256(Path(out).read_bytes()).hexdigest(),'orientation':'portrait','paper':'A4','fitToWidth':1,'fitToHeight':1,'print_area':f'A1:X{count}','native_shapes':True,'render_images':len(render_media),'Windows_Excel_printer_confirmed':False}
    Path(str(out)+'.print-settings.json').write_text(json.dumps(report,indent=2))
