import copy, json, sys, tempfile, unittest, zipfile
from pathlib import Path
from xml.etree import ElementTree as E
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import pfc
from drawing import native

def fixture(path,rows):
    ns=pfc.S
    root=E.Element('{'+ns+'}worksheet');data=E.SubElement(root,'{'+ns+'}sheetData')
    for i,vals in enumerate(rows,1):
        row=E.SubElement(data,'{'+ns+'}row',{'r':str(i)})
        for value in vals:
            cell=E.SubElement(row,'{'+ns+'}c',{'t':'inlineStr'})
            E.SubElement(E.SubElement(cell,'{'+ns+'}is'),'{'+ns+'}t').text=str(value)
    # Deliberately omit cell coordinates, as D365 does in the uploaded BOM.
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('xl/worksheets/sheet.xml',E.tostring(root))
        z.writestr('xl/workbook.xml',f'<workbook xmlns="{ns}" xmlns:r="{pfc.R}"><sheets><sheet name="BOM" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet.xml" Type="'+pfc.R+'/worksheet"/></Relationships>')

HEADER=['Type','Level','Item/Resource','Description','Operation','Cost group','Unit','Consumption per lot size','Lot size quantity']
ROWS=[HEADER,
 ['Production',0,'FIN','Finished assembly','','FIN','ea',100,100],
 ['BOM',1,'WELD','Welded assembly','','WIP','ea',100,100],
 ['BOM',2,'LASER','Laser component','','WIP','ea',100,100],
 ['Item',3,'STOCK','2 mm steel sheet','','RAW','ea',1,100],
 ['Setup',3,'LC','Laser cutter','Laser Cut','MACH','Hours',.1,100],
 ['Process',3,'LC','Laser cutter','Laser Cut','MACH','Hours',.3,100],
 ['Process',3,'OPLC','Laser operator','OPLC','LAB','Hours',.3,100],
 ['Item',2,'STUD','M6 Weld Stud','','RAW','ea',200,100],
 ['Process',2,'MIG','MIG weld','MIG','MACH','Hours',2,100],
 ['Service',1,'ECT','Electrocoating','','VEND','ea',100,100],
 ['Item',1,'CARTON','RSC carton','','RAW','ea',4,100],
 ['Item',1,'LABEL','Transfer labels','','RAW','m',.1,100],
 ['Process',1,'BENCH','Work Bench','Workbench','MACH','Hours',.2,100],
 ['Surcharge',1,'Surcharge','Overhead','','OVH','AUD',20,100]]

class Workflow(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.bom=self.root/'BOM.xlsx';fixture(self.bom,ROWS)
        self.path=pfc.build(self.bom,self.root/'job')
    def tearDown(self):self.tmp.cleanup()
    def test_physical_operations_and_ownership(self):
        s=pfc.read(self.path);ops=[n for n in s['nodes'] if n['kind']=='operation']
        self.assertEqual([n['family'] for n in ops],['laser','weld','ecoat','pack'])
        stud=next(n for n in s['nodes'] if n['item']=='STUD');self.assertEqual(stud['quantity'],2)
        weld=next(n for n in ops if n['family']=='weld');self.assertIn({'from':stud['key'],'to':weld['key']},s['edges'])
        pack=ops[-1];self.assertIn('25 / BOX',pack['label']);self.assertEqual(len(pack['packaging']),2)
        self.assertEqual(len(s['source_rows']),len(ROWS)-1)
        self.assertEqual(s['plant'],'TBC')
        self.assertEqual(s['operation_numbering']['basis'],'proposed_route_sequence')
        self.assertIsNone(s['operation_numbering']['source'])
    def test_component_quantity_stays_with_manufactured_stage(self):
        rows=copy.deepcopy(ROWS);rows[3][7]=200
        fixture(self.root/'two-components.xlsx',rows)
        path=pfc.build(self.root/'two-components.xlsx',self.root/'two-components-job')
        laser=next(n for n in pfc.read(path)['nodes'] if n.get('family')=='laser')
        self.assertEqual(laser['quantity'],2)
        self.assertEqual(laser['unit'],'ea')

    def test_approval_and_source_bindings(self):
        with self.assertRaisesRegex(ValueError,'approval'):pfc.export(self.path)
        preview=pfc.preview(self.path);self.assertLess(preview.stat().st_size,1_000_000)
        pfc.approve(self.path,'TEST ONLY');s=pfc.read(self.path);s['nodes'][0]['label']='Changed';pfc.save(self.path,s)
        with self.assertRaisesRegex(ValueError,'approval'):pfc.export(self.path)
        pfc.preview(self.path);self.assertNotIn('approval',pfc.read(self.path))
        s=pfc.read(self.path);(self.path.parent/s['source']['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'BOM changed'):pfc.preview(self.path)
    def test_reject_hierarchy_errors(self):
        rows=copy.deepcopy(ROWS);rows[4][1]=5;fixture(self.root/'bad.xlsx',rows)
        with self.assertRaisesRegex(ValueError,'level'):pfc.build(self.root/'bad.xlsx',self.root/'bad-job')
    def test_image_and_cad_approval_bindings(self):
        s=pfc.read(self.path);job=self.path.parent
        image=job/'render.png';original=(pfc.ROOT/'assets/logo.png').read_bytes();image.write_bytes(original)
        cad=job/'source.step';cad.write_bytes(b'test-source-geometry')
        s['additional_sources']=[{'path':cad.name,'sha256':pfc.sha(cad)}]
        s['images']={'main':{'path':image.name,'sha256':pfc.sha(image),'node_key':s['main'][0],'box':[20,140,80,90]}}
        pfc.save(self.path,s);preview=pfc.preview(self.path)
        self.assertIn('data:image/png;base64,',preview.read_text())
        pfc.approve(self.path,'TEST ONLY');image.write_bytes(b'changed image')
        with self.assertRaisesRegex(ValueError,'Render changed'):pfc.export(self.path)
        image.write_bytes(original);cad.write_bytes(b'changed geometry')
        with self.assertRaisesRegex(ValueError,'Additional source changed'):pfc.preview(self.path)
    def test_native_drawing_and_topology(self):
        s=pfc.read(self.path);scene=pfc.layout(s);r=native(scene,.76)
        text=[t.text for t in r.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t')]
        self.assertIn('STUD',text);self.assertIn('CARTON #CARTON',text)
        broken=copy.deepcopy(s);broken['edges'].append({'from':s['main'][-1],'to':s['main'][0]})
        with self.assertRaisesRegex(ValueError,'Cycle'):pfc.layout(broken)
        broken=copy.deepcopy(s);broken['layout']={'boxes':{s['main'][1]:[375,140,250,116]}}
        with self.assertRaisesRegex(ValueError,'Overlapping'):pfc.layout(broken)
    def test_reference_form_symbols_and_spacing(self):
        from form import reference
        f=reference();s=pfc.read(self.path);scene=pfc.layout(s)
        grow=pfc.spaced(f)
        self.assertEqual(scene['boxes'][s['main'][0]],grow(f['phases']['laser']))
        bend=grow(f['phases']['bend']);second=scene['boxes'][s['main'][1]]
        self.assertEqual([second[0]]+second[2:],[bend[0]]+bend[2:])
        last=scene['boxes'][s['main'][-1]]
        self.assertAlmostEqual(last[1]+last[3],min(q['y'] for q in f['legend'])-16)
        self.assertGreater(scene['boxes'][s['main'][0]][2],f['phases']['laser'][2]*1.2)
        self.assertEqual(scene['height'],f['height'])
        self.assertTrue(any(p['type']=='frame' for p in scene['items']))
        drawing=native(scene,1,f['top']);ns={'x':'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
        for geometry in ('ellipse','rect','triangle'):
            matched=[]
            for props in drawing.findall('.//x:sp/x:spPr',ns):
                g=props.find('a:prstGeom',ns);color=props.find('a:solidFill/a:srgbClr',ns)
                if g is not None and g.get('prst')==geometry and color is not None and color.get('val')=='FFC000':matched.append(props)
            self.assertTrue(matched)
            self.assertTrue(any(p.find('a:ln/a:solidFill/a:srgbClr',ns) is not None and p.find('a:ln/a:solidFill/a:srgbClr',ns).get('val')=='385D8A' for p in matched))
        self.assertIsNotNone(drawing.find('.//x:grpSp',ns))
        axes=[]
        for item in scene['items']:
            if item['type']!='path':continue
            for a,b in zip(item['points'],item['points'][1:]):self.assertTrue(a[0]==b[0] or a[1]==b[1],(a,b))
            if len(item['points'])==2:axes.append(item['points'][0][0])
        # Shifted reference slots still share one straight main-route spine.
        self.assertGreater(len(axes),1)
        self.assertEqual(len(set(axes)),1)

        pack=next(n for n in s['nodes'] if n.get('family')=='pack')
        tb=next(sp.find('x:txBody',ns) for sp in drawing.findall('.//x:sp',ns) if any(t.text=='PACK' for t in sp.findall('.//a:t',ns)))
        source=f['text_templates']['pack']
        self.assertEqual(len(tb.findall('a:p',ns)),len(source.findall('a:p',ns)))
        for actual,original in zip(tb.findall('a:p',ns),source.findall('a:p',ns)):
            self.assertEqual(E.tostring(actual.find('a:pPr',ns)),E.tostring(original.find('a:pPr',ns)))
        self.assertIn('PACK',[t.text for t in tb.findall('.//a:t',ns)])
        # Symbols sit in one row inside their box, with clear gaps between them.
        for key,(bx,by,bw,bh) in scene['boxes'].items():
            syms=sorted((i for i in scene['items'] if i.get('source_symbol') and bx<=i['x']<bx+bw and by<=i['y']<by+bh),key=lambda i:i['x'])
            for i in syms:self.assertLessEqual(i['x']+i['w'],bx+bw);self.assertLessEqual(i['y']+i['h'],by+bh)
            for left,right in zip(syms,syms[1:]):self.assertGreaterEqual(right['x']-(left['x']+left['w']),pfc.SYMBOL_GAP-.01)

    def test_export_writes_macro_free_workbook(self):
        s=pfc.read(self.path);s.update(plant='Press Shop',issued_by='Tester',original_date='2026-10-01');pfc.save(self.path,s)
        pfc.preview(self.path);pfc.approve(self.path,'TEST ONLY');out=pfc.export(self.path)
        ns={'s':pfc.S}
        with zipfile.ZipFile(out) as z:
            names=z.namelist();self.assertFalse([n for n in names if 'vba' in n.lower() or 'thumbnail' in n])
            for n in names:
                if n.endswith(('.xml','.rels')):E.fromstring(z.read(n))
            sheet=E.fromstring(z.read('xl/worksheets/sheet1.xml'))
            cells={c.get('r'):c for c in sheet.iter('{'+pfc.S+'}c')}
            text=lambda r:''.join(cells[r].itertext())
            self.assertEqual(text('G2'),s['number']);self.assertEqual(text('G3'),s['name'])
            self.assertEqual(text('U1'),'Press Shop');self.assertEqual(text('R3'),'Tester')
            self.assertEqual(text('R2'),'46296');self.assertEqual(text('V2'),'TBC')
            self.assertIn('formatCode="dd/mm/yyyy"',z.read('xl/styles.xml').decode())
            self.assertEqual(sheet.find('s:pageSetup',ns).get('orientation'),'portrait')
            self.assertIn('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml',z.read('[Content_Types].xml').decode())
            labels=[t.text for t in E.fromstring(z.read('xl/drawings/drawing-pfc.xml')).iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t')]
            for n in s['nodes']:self.assertIn(n['item'],labels)
            joined=' '.join(t or '' for t in labels)
            for placeholder in ('PART-NO','SIDE-PART','MAT-CODE','HW-CODE','CARTON-CODE'):self.assertNotIn(placeholder,joined)


if __name__=='__main__':unittest.main()
