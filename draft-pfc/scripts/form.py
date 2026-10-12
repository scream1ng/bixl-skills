"""Measured company form geometry and original DrawingML style prototypes."""
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree as E
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
A='http://schemas.openxmlformats.org/drawingml/2006/main'
D='http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing'
S='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
NS={'a':A,'x':D,'s':S}

@lru_cache(maxsize=1)
def reference():
    with ZipFile(ROOT/'assets/reference-pfc.xlsx') as z:
        sheet=E.fromstring(z.read('xl/worksheets/sheet1.xml'));drawing=E.fromstring(z.read('xl/drawings/drawing1.xml'))
    default=float(sheet.find('s:sheetFormatPr',NS).get('defaultRowHeight','12.75'))
    heights={int(r.get('r')):float(r.get('ht',default))*96/72 for r in sheet.findall('s:sheetData/s:row',NS)}
    def row_y(index):return sum(heights.get(i,default*96/72) for i in range(1,index+1))
    cols=sheet.find('s:cols',NS);widths=[]
    for i in range(1,25):
        col=next(c for c in cols if int(c.get('min'))<=i<=int(c.get('max')))
        w=float(col.get('width'));widths.append(int(((256*w+int(128/7))/256)*7))
    top=row_y(3);width=sum(widths);height=row_y(52)-top
    shapes=drawing.findall('x:twoCellAnchor/x:sp',NS)
    def text(sp):return [t.text or '' for t in sp.findall('.//a:t',NS)]
    def box(sp):
        xf=sp.find('x:spPr/a:xfrm',NS);o=xf.find('a:off',NS);e=xf.find('a:ext',NS)
        return [int(o.get('x'))/9525,int(o.get('y'))/9525-top,int(e.get('cx'))/9525,int(e.get('cy'))/9525]
    operation=next(s for s in shapes if 'Laser Cut Blank' in text(s))
    phases={};text_templates={};source_boxes={}
    for phase,label in [('laser','Laser Cut Blank'),('bend','Bend'),('weld','Weld'),('ecoat',"E'Coat"),('pack','PACK')]:
        sp=next(s for s in shapes if any(t.strip()==label for t in text(s)))
        phases[phase]=box(sp);source_boxes[phase]=box(sp);text_templates[phase]=sp.find('x:txBody',NS)
    raw=next(s for s in shapes if any('2440 x 1220 SHT' in t for t in text(s)))
    hardware=next(s for s in shapes if any('F/H WELD STUD' in t for t in text(s)))
    side=next(s for s in shapes if text(s) and text(s)[0]=='SIDE-PART')
    for key,sp in [('material',raw),('hardware',hardware),('side',side)]:
        source_boxes[key]=box(sp);text_templates[key]=sp.find('x:txBody',NS)
    symbol_offsets={}
    for key,(x,y,w,h) in source_boxes.items():
        symbol_offsets[key]={}
        for sp in shapes:
            geom=sp.find('x:spPr/a:prstGeom',NS)
            if text(sp) or geom is None or geom.get('prst') not in ('ellipse','rect','triangle'):continue
            sx,sy,sw,sh=box(sp)
            if sx>=x-1 and sy>=y-1 and sx+sw<=x+w+1 and sy+sh<=y+h+1:
                kind={'ellipse':'operation','rect':'inspection','triangle':'storage'}[geom.get('prst')]
                symbol_offsets[key][kind]=[sx-x,sy-y,sw,sh]
    # The reference's PACK operation symbol is a pasted circle image. Recreate
    # its outlined ellipse at the measured image bounds, keeping it editable.
    px,py,pw,ph=phases['pack']
    for pic in drawing.findall('x:twoCellAnchor/x:pic',NS):
        sx,sy,sw,sh=box(pic)
        if sx>=px and sy>=py and sx+sw<=px+pw and sy+sh<=py+ph:
            border=25400/9525
            symbol_offsets['pack']['operation']=[sx-px+border/2,sy-py+border/2,sw-border,sh-border]
    prototypes={}
    for name,geom in [('operation','ellipse'),('inspection','rect'),('storage','triangle')]:
        sp=next(s for s in shapes if not text(s) and s.find('x:spPr/a:prstGeom',NS) is not None and s.find('x:spPr/a:prstGeom',NS).get('prst')==geom)
        b=box(sp);ob=box(operation)
        prototypes[name]={'sp':sp,'box':b,'offset':[b[0]-ob[0],b[1]-ob[1]],'size':b[2:]}
    anchor=next(a for a in drawing if a.find('x:grpSp',NS) is not None);group=anchor.find('x:grpSp',NS)
    def anchor_point(tag):
        p=anchor.find('x:'+tag,NS);col=int(p.find('x:col',NS).text);row=int(p.find('x:row',NS).text)
        return [sum(widths[:col])+int(p.find('x:colOff',NS).text)/9525,row_y(row)+int(p.find('x:rowOff',NS).text)/9525-top]
    origin=anchor_point('from');end=anchor_point('to');extent=[end[i]-origin[i] for i in range(2)]
    xf=group.find('x:grpSpPr/a:xfrm',NS);co=xf.find('a:chOff',NS);ce=xf.find('a:chExt',NS);legend=[]
    for sp in group.findall('x:sp',NS):
        f=sp.find('x:spPr/a:xfrm',NS);o=f.find('a:off',NS);e=f.find('a:ext',NS)
        x=origin[0]+(int(o.get('x'))-int(co.get('x')))*extent[0]/int(ce.get('cx'))
        y=origin[1]+(int(o.get('y'))-int(co.get('y')))*extent[1]/int(ce.get('cy'))
        w=int(e.get('cx'))*extent[0]/int(ce.get('cx'));h=int(e.get('cy'))*extent[1]/int(ce.get('cy'))
        ts=text(sp);geom=sp.find('x:spPr/a:prstGeom',NS).get('prst')
        if ts:legend.append({'type':'text','x':x+3,'y':y+14,'w':w-3,'h':h,'lines':ts,'font_size':12,'line_height':12,'align':'left'})
        elif geom=='rect' and w>300:legend.append({'type':'rect','x':x,'y':y,'w':w,'h':h,'fill':'#fff','stroke':'#bfbfbf','stroke_width':.75})
        else:
            kind={'ellipse':'operation','rect':'inspection','triangle':'storage','rightArrow':'transport','chord':'delay'}[geom]
            legend.append({'type':kind,'x':x,'y':y,'w':w,'h':h,'fill':'#FFC000','stroke':'#385D8A','stroke_width':2.6667})
    return {'width':width,'height':height,'top':top,'last_row':52,'phases':phases,'material':box(raw),'hardware':box(hardware),'side':box(side),'symbols':prototypes,'symbol_offsets':symbol_offsets,'text_templates':text_templates,'legend':legend,'legend_anchor':anchor,'sheet':sheet}
