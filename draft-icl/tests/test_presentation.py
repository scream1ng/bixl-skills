import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from lxml import etree as E
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import icl
from presentation import normalize, caption, pack_views
from verify_print import verify
M='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


class Presentation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.job=Path(self.tmp.name)/'job';shutil.copytree(ROOT/'examples/bending',self.job)
        self.path=self.job/'spec.json';self.spec=json.loads(self.path.read_text(encoding='utf-8'))
    def write(self):self.path.write_text(json.dumps(self.spec),encoding='utf-8')
    def export(self):
        self.write();icl.preview(self.path);icl.approve(self.path,'TEST ONLY');return icl.export(self.path)
    def test_angles_one_decimal_without_rounding_measurement_or_tolerance(self):
        c=self.spec['checks'][0];c.update(nominal=145.75745152,unit='deg',gauge='Protractor',tolerance=.25)
        self.spec['drawing']['dimensions']=[{'check':c['key'],'kind':'angle','centre':[400,200],'radius':50,'start_deg':0,'end_deg':145.75745152,'value_xy':[400,300],'badge_xy':[300,300]}]
        out=self.export()
        self.assertEqual(c['nominal'],145.75745152);self.assertEqual(icl.nominal(c),'145.8°');self.assertEqual(icl.limits(c),'±0.25°')
        self.assertIn('145.8°',(self.job/'drawing-r1.svg').read_text(encoding='utf-8'))
        with ZipFile(out)as z:
            sheet=E.fromstring(z.read('xl/worksheets/sheet1.xml'));self.assertEqual(''.join(sheet.find(f'.//{M}c[@r="C11"]').itertext()),'Check angle 145.8°')
    def test_caption_uses_current_measured_related_check_values(self):
        a={'key':'w','nominal':6.1,'unit':'mm'};b={'key':'l','nominal':10,'unit':'mm','feature':'slot','size_checks':['w','l']}
        self.assertEqual(caption(b,{'w':a,'l':b}),'Check slot 6.1 × 10 mm');a['nominal']=5.4
        self.assertEqual(caption(b,{'w':a,'l':b}),'Check slot 5.4 × 10 mm')
    def test_laser_slot_is_one_checkpoint_cell_and_one_label(self):
        check=copy.deepcopy(self.spec['checks'][0]);check.pop('nominal')
        check.update(key='slot',feature='slot',group='hourly',tolerance=.2,measurements=[{'key':'width','nominal':6.1},{'key':'length','nominal':10}])
        self.spec.update(process='laser',checks=[check])
        self.spec['drawing']['dimensions']=[
            {'check':'slot','measurement':'width','kind':'vertical','a':[100,197],'b':[100,203],'offset':200,'show_badge':False},
            {'check':'slot','measurement':'length','kind':'horizontal','a':[95,200],'b':[105,200],'offset':250,'show_badge':False}]
        self.spec['drawing']['balloons']=[{'checks':['slot'],'target':[100,200],'elbows':[[100,100]],'badge_xy':[350,100]}]
        out=self.export()
        svg=E.fromstring((self.job/'drawing-r1.svg').read_bytes());ns={'s':'http://www.w3.org/2000/svg'}
        self.assertEqual(svg.xpath('count(.//s:text[text()="L2"])',namespaces=ns),1)
        self.assertIn('6.1',svg.xpath('.//s:text/text()',namespaces=ns));self.assertIn('10',svg.xpath('.//s:text/text()',namespaces=ns))
        with ZipFile(out)as z:
            sheet=E.fromstring(z.read('xl/worksheets/sheet1.xml'))
            captions=[''.join(c.itertext())for c in sheet.iter(M+'c')]
            self.assertEqual(captions.count('Check slot 6.1 × 10 mm'),1)
            self.assertEqual([c['id']for c in icl.load(self.path)[1]['checks']],['L1','L2','L3'])
        self.assertEqual(check['measurements'][0]['nominal'],6.1)
    def test_three_common_holes_keep_one_balloon_after_view_packing(self):
        check=copy.deepcopy(self.spec['checks'][0]);check.update(id='L1',key='holes',feature='hole',nominal=6.1)
        self.spec.update(process='laser',checks=[check])
        self.spec['drawing']={'width':400,'height':400,'source_width':400,'source_height':400,'geometry':'geometry.svg','dimensions':[],
            'views':[{'key':'flat','source_box':[0,0,400,400],'box':[0,0,200,200]}],
            'balloons':[{'checks':['holes'],'view':'flat','badge_xy':[350,200],'targets':[{'target':[100,y],'elbows':[[300,y],[300,200]]}for y in [100,200,300]]}]}
        geometry=b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400"><g data-view="flat"><circle cx="100" cy="100" r="3" stroke="black" fill="none"/></g></svg>'
        svg=E.fromstring(icl.render_svg(self.spec,geometry).encode());ns={'s':'http://www.w3.org/2000/svg'}
        group=svg.xpath('.//s:g[@data-checks="holes"]',namespaces=ns)[0]
        self.assertEqual(len(group.findall('{'+ns['s']+'}polyline')),3)
        self.assertEqual(group.xpath('s:text/text()',namespaces=ns),['L1'])
        self.assertEqual([float(c.get('cy'))for c in group.findall('{'+ns['s']+'}circle')],[50,100,150])
        self.assertEqual(group.find('{'+ns['s']+'}text').get('x'),'175.0')
    def test_common_balloon_cannot_cross_a_different_checkpoint(self):
        self.spec['drawing']['dimensions']=[]
        self.spec['drawing']['balloons']=[{'checks':['left_height'],'badge_xy':[300,200],'targets':[{'target':[100,100]},{'target':[100,300]}]},
            {'checks':['right_height'],'target':[200,50],'badge_xy':[200,350]}]
        with self.assertRaisesRegex(ValueError,'leaders cross'):icl.render_svg(self.spec,(self.job/'geometry.svg').read_bytes())
    def test_compound_measurements_reject_ambiguous_or_separate_criteria(self):
        check=self.spec['checks'][0];check.pop('nominal')
        for items in [[{'key':'width','nominal':6.1},{'key':'width','nominal':10}],
                      [{'key':'width','nominal':6.1},{'key':'length','nominal':True}],
                      [{'key':'width','nominal':6.1},{'key':'length','nominal':10,'tolerance':.3}]]:
            with self.subTest(items=items):
                check['measurements']=items;self.write()
                with self.assertRaises(ValueError):icl.load(self.path)
    def test_deleting_check_updates_linked_balloons_and_contiguous_ids(self):
        self.spec['drawing']['balloons']=[{'checks':['left_height','right_height'],'target':[100,100],'badge_xy':[100,200]}];self.write()
        icl.remove_check(self.path,'left_height');out=icl.preview(self.path)
        self.assertIn('data-checks="right_height"',out.read_text(encoding='utf-8'));self.assertNotIn('data-check="left_height"',out.read_text(encoding='utf-8'))
        spec=icl.load(self.path)[1];self.assertEqual([c['id']for c in spec['checks']],['B1','B2','B3']);self.assertEqual(spec['revision'],2)
    def test_unavailable_gauge_needs_explicit_equipment_availability(self):
        self.spec['checks'][0]['gauge']='Height gauge';self.write()
        with self.assertRaisesRegex(ValueError,'not available'):icl.preview(self.path)
        self.spec['available_gauges']=['Vernier','Height gauge'];self.write();icl.preview(self.path)
    def test_company_final_visual_row_is_unique_last_and_not_alterable(self):
        layout=json.loads((ROOT/'processes/laser/layout.json').read_text(encoding='utf-8'));self.spec['process']='laser'
        for c in self.spec['checks']:c['group']='hourly'
        spec=normalize(self.spec,layout);quality=spec['checks'][-1];self.assertEqual(quality['limits'],'SOP008');quality['key']='existing_quality'
        self.assertEqual(len(normalize(spec,layout)['checks']),len(spec['checks']))
        quality['key']='laser_safe_edges';quality['limits']='TBC'
        with self.assertRaisesRegex(ValueError,'profile explicitly'):normalize(spec,layout)
    def test_mixed_inspection_groups_rejected_before_preview(self):
        self.spec['process']='laser'
        for c,g in zip(self.spec['checks'],['hourly','setup','hourly']):c['group']=g
        self.write()
        with self.assertRaisesRegex(ValueError,'group order'):icl.preview(self.path)
    def test_compact_form_keeps_all_checks_equal_and_saves_landscape(self):
        out=self.export()
        with ZipFile(out)as z:
            root=E.fromstring(z.read('xl/worksheets/sheet1.xml'));styles=E.fromstring(z.read('xl/styles.xml'))
            for row in [10,11,12,13]:
                self.assertEqual(float(root.find(f'{M}sheetData/{M}row[@r="{row}"]').get('ht')),24)
                for col in ['B','C','E','G']:
                    cell=root.find(f'.//{M}c[@r="{col}{row}"]');xf=styles.find(M+'cellXfs')[int(cell.get('s'))];font=styles.find(M+'fonts')[int(xf.get('fontId'))];self.assertEqual(font.find(M+'sz').get('val'),'10')
            for i in [1,2]:self.assertEqual(E.fromstring(z.read(f'xl/worksheets/sheet{i}.xml')).find(M+'pageSetup').get('orientation'),'landscape')
            self.assertFalse(any('printerSettings'in n for n in z.namelist()))
            self.assertIn('A1:T20',z.read('xl/workbook.xml').decode().replace('$',''))
        report=verify(out);self.assertTrue(report['file_page_setup_verified']);self.assertFalse(report['windows_excel_print_verified'])
    def test_utf8_preview_and_svg_survive_cp1252_locale(self):
        self.spec['part']['name']='Angle ° inspection';self.spec['checks'][0].update(nominal=105,unit='deg',gauge='Protractor')
        self.spec['drawing']['dimensions']=[{'check':'left_height','kind':'angle','centre':[400,200],'radius':50,'start_deg':0,'end_deg':105,'value_xy':[400,300],'badge_xy':[300,300]}];self.write()
        oldread=Path.read_text;oldwrite=Path.write_text
        def read(path,*a,**kw):kw.setdefault('encoding','cp1252');return oldread(path,*a,**kw)
        def write(path,*a,**kw):kw.setdefault('encoding','cp1252');return oldwrite(path,*a,**kw)
        with patch.object(Path,'read_text',read),patch.object(Path,'write_text',write):icl.preview(self.path);icl.approve(self.path,'TEST ONLY');out=icl.export(self.path)
        self.assertIn('105.0°',(self.job/'drawing-r1.svg').read_text(encoding='utf-8'));self.assertTrue(out.exists())
    def test_grouped_angle_geometry_and_annotation_share_projection(self):
        spec=copy.deepcopy(self.spec);c=spec['checks'][0];c.update(nominal=105,unit='deg')
        spec['drawing']={'width':800,'height':300,'source_width':400,'source_height':400,'geometry':'geometry.svg','views':[{'key':'a','source_box':[0,0,400,400],'box':[0,0,300,300]}],
        'dimensions':[{'check':'left_height','kind':'angle','view':'a','centre':[200,200],'radius':50,'start_deg':0,'end_deg':105,'value_xy':[200,300],'badge_xy':[70,300]}]}
        geometry=b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400"><g data-view="a"><line x1="0" y1="200" x2="400" y2="200" stroke="black"/></g></svg>'
        mapped,wire=pack_views(spec,geometry);self.assertEqual(mapped['drawing']['dimensions'][0]['centre'],[150,150]);self.assertNotIn('contact_segments',mapped['drawing']['dimensions'][0])
        svg=icl.render_svg(spec,geometry);self.assertIn('105.0°',svg);self.assertIn('scale(0.75)',svg)
    def test_visual_reference_cannot_be_overridden_by_tolerance_or_duplicates(self):
        layout=json.loads((ROOT/'processes/laser/layout.json').read_text(encoding='utf-8'));self.spec['process']='laser'
        for c in self.spec['checks']:c['group']='hourly'
        spec=normalize(self.spec,layout);spec['checks'][-1]['tolerance']=0
        with self.assertRaisesRegex(ValueError,'profile explicitly'):normalize(spec,layout)
        spec=normalize(self.spec,layout);extra=copy.deepcopy(spec['checks'][-1]);extra['key']='duplicate';spec['checks'].append(extra)
        with self.assertRaisesRegex(ValueError,'Duplicate configured'):normalize(spec,layout)
    def test_svg_inherited_root_styles_survive_both_layouts_and_rasterization(self):
        import cairosvg
        import cairocffi as cairo
        from io import BytesIO
        spec=copy.deepcopy(self.spec);spec['drawing']={'width':400,'height':400,'geometry':'geometry.svg','dimensions':[]}
        geometry=b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" stroke="black" fill="none" stroke-width="4"><g data-view="a"><path d="M 10 10 L 390 390"/></g></svg>'
        # Single-view legacy geometry has no view metadata.
        plain=geometry.replace(b' data-view="a"',b'')
        for grouped in [False,True]:
            if grouped:spec['drawing']['views']=[{'key':'a','source_box':[0,0,400,400],'box':[0,0,400,400]}]
            svg=icl.render_svg(spec,geometry if grouped else plain)
            parsed=E.fromstring(svg.encode());self.assertTrue(parsed.xpath('//s:g[@stroke="black" and @fill="none"]',namespaces={'s':icl.SVG}))
            surface=cairo.ImageSurface.create_from_png(BytesIO(cairosvg.svg2png(bytestring=svg.encode())))
            data=bytes(surface.get_data());self.assertTrue(any(data[i]<100 for i in range(0,len(data),4)),'CAD wireframe disappeared')
    def test_print_verifier_rejects_wrong_sheet_truncated_area_and_disabled_fit(self):
        out=self.export()
        with ZipFile(out)as z:original={n:z.read(n)for n in z.namelist()}
        for area,disabled in [("'incorrect'!$A$1:$T$19",False),("'part no'!$A$1:$A$1",False),(None,True)]:
            parts=dict(original)
            if area:
                book=E.fromstring(parts['xl/workbook.xml']);node=next(n for n in book.find(M+'definedNames')if n.get('localSheetId')=='0');node.text=area;parts['xl/workbook.xml']=E.tostring(book)
            if disabled:
                sheet=E.fromstring(parts['xl/worksheets/sheet1.xml']);sheet.find(f'{M}sheetPr/{M}pageSetUpPr').set('fitToPage','false');parts['xl/worksheets/sheet1.xml']=E.tostring(sheet)
            bad=self.job/'bad.xlsx'
            with ZipFile(bad,'w')as z:
                for name,data in parts.items():z.writestr(name,data)
            with self.assertRaises(ValueError):verify(bad)
    def test_crossing_leaders_fail_instead_of_printing_ambiguous_routes(self):
        self.spec['drawing']['balloons']=[{'checks':['left_height'],'target':[100,200],'badge_xy':[300,200]},{'checks':['right_height'],'target':[200,100],'badge_xy':[200,300]}]
        with self.assertRaisesRegex(ValueError,'leaders cross'):icl.render_svg(self.spec,(self.job/'geometry.svg').read_bytes())
        self.spec['drawing']['balloons'][1]['badge_xy']=[400,100]
        icl.render_svg(self.spec,(self.job/'geometry.svg').read_bytes())
    def test_extended_history_keeps_date_and_wrap_styles(self):
        self.spec['history']=[{'date':'2026-10-12','revision':i,'change':'Previous operator check revision','author':''}for i in range(1,12)]
        out=self.export()
        with ZipFile(out)as z:
            history=E.fromstring(z.read('xl/worksheets/sheet2.xml'));a6=history.find(f'.//{M}c[@r="A6"]');a17=history.find(f'.//{M}c[@r="A17"]')
            self.assertEqual(a6.get('s'),a17.get('s'));self.assertEqual(''.join(history.find(f'.//{M}c[@r="B17"]').itertext()),'1')
            self.assertEqual(history.find(M+'dimension').get('ref'),'A1:U17')


if __name__=='__main__':unittest.main()
