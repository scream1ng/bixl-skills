import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import subprocess
from io import BytesIO
from zipfile import ZipFile
from lxml import etree as E

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import icl


class Workflow(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.job=Path(self.tmp.name)/'job';shutil.copytree(ROOT/'examples/bending',self.job)
        self.path=self.job/'spec.json';self.spec=json.loads(self.path.read_text())

    def write(self):self.path.write_text(json.dumps(self.spec))

    @unittest.skipUnless(shutil.which('node'), 'Node is optional; needed only for comment UI tests')
    def test_comment_controller_interaction(self):
        subprocess.run(['node', str(ROOT/'tests/test_comments.cjs')], check=True, capture_output=True, text=True)

    def test_review_is_offline_small_and_does_not_export(self):
        result=icl.preview(self.path);content=result.read_text()
        self.assertLess(result.stat().st_size,1000000)
        self.assertNotIn('<script src=',content)
        self.assertIn('data-check="left_height"',content)
        self.assertFalse(list(self.job.glob('*.xlsx')))
        with self.assertRaisesRegex(ValueError,'No approval'):icl.export(self.path)

    def test_comment_buttons_have_explicit_embedded_host_colours(self):
        content=icl.preview(self.path).read_text()
        self.assertIn('<aside class="icl-controls"',content)
        document=E.HTML(content)
        self.assertFalse(document.xpath('//header'))
        for control in ['mode','copy','notes','status','exported']:
            self.assertEqual(len(document.xpath(f'//aside//*[@id="{control}"]')),1)
        self.assertIn('Comment mode</button>',content)
        self.assertIn('button{color:#20262c!important;-webkit-text-fill-color:#20262c!important',content)
        self.assertIn('.icl-controls #mode{color:#fff!important;-webkit-text-fill-color:#fff!important;background:#e31837',content)
        self.assertIn('.pin .marker,.pin .marker span{color:#fff!important',content)

    def test_revision_and_stale_approval(self):
        icl.preview(self.path);icl.approve(self.path,'TEST ONLY: approve this temporary fixture')
        self.spec['checks'][0]['nominal']=36;self.write()
        with self.assertRaisesRegex(ValueError,'revision already exists'):icl.preview(self.path)
        self.spec['revision']=2;self.write();icl.preview(self.path)
        with self.assertRaisesRegex(ValueError,'Approval is stale'):icl.export(self.path)

    def test_source_change_requires_remeasurement(self):
        with (self.job/'part.step').open('ab') as f:f.write(b'changed')
        with self.assertRaisesRegex(ValueError,'Source changed'):icl.preview(self.path)

    def test_template_isolation_and_exported_content(self):
        before={str(p):icl.digest(p.read_bytes()) for p in (ROOT/'processes').rglob('*') if p.is_file()}
        icl.preview(self.path);icl.approve(self.path,'TEST ONLY: approve this temporary fixture');out=icl.export(self.path)
        m='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
        with ZipFile(out) as z,ZipFile(ROOT/'processes/bending/template.xlsx') as original:
            root=E.fromstring(z.read('xl/worksheets/sheet1.xml'));cells={c.get('r'):c for c in root.iter(m+'c')}
            self.assertEqual(''.join(cells['B10'].itertext()),'B1')
            self.assertEqual(''.join(cells['C10'].itertext()),'Check part to Reference sample')
            self.assertIn('35 mm',''.join(cells['C11'].itertext()))
            self.assertEqual(''.join(cells['E11'].itertext()),'±0.5 mm')
            styles=E.fromstring(z.read('xl/styles.xml')).find(m+'cellXfs')
            self.assertEqual(styles[int(cells['B10'].get('s'))].find(m+'alignment').get('vertical'),'center')
            self.assertTrue(z.read('xl/media/icl-approved.png').startswith(b'\x89PNG'))
            old=E.fromstring(original.read('xl/worksheets/sheet1.xml'))
            for tag in ['cols','pageMargins']:
                a,b=old.find(m+tag),root.find(m+tag)
                self.assertEqual(E.tostring(a) if a is not None else None,E.tostring(b) if b is not None else None)
        after={str(p):icl.digest(p.read_bytes()) for p in (ROOT/'processes').rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    def test_export_carries_no_template_part_leftovers(self):
        icl.preview(self.path);icl.approve(self.path,'TEST ONLY: approve this temporary fixture');out=icl.export(self.path)
        m='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
        with ZipFile(out) as z:
            names=z.namelist()
            self.assertNotIn('docProps/thumbnail.emf',names);self.assertNotIn('docProps/custom.xml',names)
            strings=len(E.fromstring(z.read('xl/sharedStrings.xml')))
            used={int(c.find(m+'v').text) for n in names if n.startswith('xl/worksheets/sheet') for c in E.fromstring(z.read(n)).iter(m+'c') if c.get('t')=='s'}
            self.assertEqual(used,set(range(strings)))
            media={n for n in names if n.startswith('xl/media/')}
            targets={'xl/media/'+r.get('Target').split('/')[-1] for n in names if n.endswith('.rels') for r in E.fromstring(z.read(n)) if 'media/' in r.get('Target','')}
            self.assertEqual(media,targets)
            core=E.fromstring(z.read('docProps/core.xml'))
            self.assertFalse([e.text for e in core if e.tag.endswith(('creator','lastModifiedBy')) and e.text])

    def test_laser_check_requires_group(self):
        self.spec['process']='laser';self.write()
        with self.assertRaisesRegex(ValueError,'group setup or hourly'):icl.preview(self.path)

    def test_laser_routes_only_to_laser_template(self):
        self.spec['process']='laser'
        for index,check in enumerate(self.spec['checks']):check['group']='hourly';check['id']='L'+str(index+1)
        self.write();icl.preview(self.path);icl.approve(self.path,'TEST ONLY: laser export fixture');out=icl.export(self.path)
        with ZipFile(out) as z:
            root=E.fromstring(z.read('xl/worksheets/sheet1.xml'));m='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
            cells={c.get('r'):''.join(c.itertext()) for c in root.iter(m+'c')}
            self.assertEqual(cells['B11'],'L1');self.assertEqual(cells['F6'],'LASER')

    def test_welding_preview_requires_own_template_for_export(self):
        self.spec['process']='welding';self.write();icl.preview(self.path)
        icl.approve(self.path,'TEST ONLY: welding fixture')
        with self.assertRaisesRegex(ValueError,'Company template'):icl.export(self.path)

    def test_capacity_does_not_silently_drop_checks(self):
        for i in range(4,11):
            c=copy.deepcopy(self.spec['checks'][0]);c.update(key=f'extra{i}',id=f'B{i}');self.spec['checks'].append(c)
        self.write()
        with self.assertRaisesRegex(ValueError,'capacity'):icl.preview(self.path)

    def test_geometry_scripts_rejected(self):
        (self.job/'geometry.svg').write_text('<svg viewBox="0 0 1800 430"><script>alert(1)</script></svg>')
        with self.assertRaisesRegex(ValueError,'vector shapes'):icl.preview(self.path)

    def test_dimension_numbers_survive_rasterization(self):
        import cairosvg
        import cairocffi as cairo
        _,spec,geometry,_,_,_=icl.load(self.path)
        image=cairo.ImageSurface.create_from_png(BytesIO(cairosvg.svg2png(bytestring=icl.render_svg(spec,geometry).encode())))
        data=bytes(image.get_data());stride=image.get_stride()
        # The interior of the 100 mm label excludes surrounding dimension lines.
        coloured=0
        for y in range(332,355):
            for x in range(1232,1268):
                b,g,r,a=data[y*stride+x*4:y*stride+x*4+4]
                if r>g+15 and r>b+15 and r>150:coloured+=1
        self.assertGreater(coloured,30,'The dimension number disappeared from the Excel PNG.')

    def test_feature_balloons_follow_stable_keys_when_ids_change(self):
        self.spec['drawing']['balloons']=[{'checks':['left_height','right_height'],'target':[150,200],'elbows':[[75,200]],'badge_xy':[75,120]}]
        self.spec['checks'][0]['id']='B8'
        geometry=(self.job/'geometry.svg').read_bytes()
        svg=E.fromstring(icl.render_svg(self.spec,geometry).encode())
        ns={'s':icl.SVG}
        group=svg.xpath('//s:g[@data-checks="left_height,right_height"]',namespaces=ns)[0]
        self.assertEqual(group.xpath('string(s:text)',namespaces=ns),'B8 / B2')
        self.assertEqual(group.xpath('string(s:polyline/@points)',namespaces=ns),'150,200 75,200 75,120')
        self.spec['drawing']['balloons'][0]['checks']=['unknown']
        with self.assertRaisesRegex(ValueError,'stable check keys'):icl.render_svg(self.spec,geometry)

    def test_surface_angle_contacts_and_nominal_are_consistent(self):
        check=self.spec['checks'][0]
        check.update(nominal=105,unit='deg',tolerance=None)
        dimension={'check':check['key'],'kind':'angle','centre':[400,200],'radius':50,'start_deg':180,'end_deg':285,'value_xy':[400,300],'badge_xy':[300,300],
                   'contact_segments':[[[300,200],[350,200]],[[410,160],[420,120]]]}
        self.spec['drawing']['dimensions']=[dimension]
        geometry=(self.job/'geometry.svg').read_bytes()
        svg=E.fromstring(icl.render_svg(self.spec,geometry).encode())
        ns={'s':icl.SVG}
        group=svg.xpath('//s:g[@data-check="left_height"]',namespaces=ns)[0]
        self.assertEqual(group.xpath('.//s:circle/@cx',namespaces=ns),['300','350','410','420'])
        self.assertIn('105.0°',group.xpath('.//s:text/text()',namespaces=ns))
        dimension['end_deg']=270
        with self.assertRaisesRegex(ValueError,'arc sweep'):icl.render_svg(self.spec,geometry)
        dimension['end_deg']=285;dimension['contact_segments'].pop()
        with self.assertRaisesRegex(ValueError,'exactly two surfaces'):icl.render_svg(self.spec,geometry)


if __name__=='__main__':unittest.main()
