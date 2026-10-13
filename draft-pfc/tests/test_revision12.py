import copy, struct, tempfile, unittest, zipfile, zlib
from pathlib import Path
from xml.etree import ElementTree as E
from test_workflow import pfc, fixture, ROWS

def png(width,height):
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+b'\xff\xff\xff'*width)*height))+chunk(b'IEND',b'')

class Revision12(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.bom=self.root/'bom.xlsx';fixture(self.bom,ROWS)
        self.path=pfc.build(self.bom,self.root/'job')
    def tearDown(self):self.tmp.cleanup()

    def test_screenshot_import_keeps_exact_descriptions_and_hashes(self):
        source=self.root/'source.png';source.write_bytes(png(2,2))
        rows=[{'row':1,'item':'123456','description':'Customer bracket'},
              {'row':2,'item':'123456E','description':'Customer bracket - ECOAT'},
              {'row':3,'item':'123456WE','description':'Customer bracket - WELD ASSEMBLY'}]
        transcription=self.root/'rows.json';pfc.save(transcription,rows)
        path=pfc.build_image(source,transcription,self.root/'screenshot-job');s=pfc.read(path)
        self.assertEqual(s['source']['format'],'calc_parts_table_image')
        self.assertEqual([r['description'] for r in s['source_rows']],[r['description'] for r in rows])
        self.assertEqual([n['family'] for n in s['nodes'][:2]],['weld','ecoat'])
        pfc.preview(path);pfc.approve(path,'test approval only')
        (path.parent/s['additional_sources'][0]['path']).write_text('changed')
        with self.assertRaisesRegex(ValueError,'Additional source changed'):pfc.export(path)

    def test_screenshot_rejects_duplicate_or_unreadable_rows(self):
        source=self.root/'source.png';source.write_bytes(png(2,2))
        transcription=self.root/'rows.json'
        for rows in [[{'row':1,'item':'123456','description':''}],
                     [{'row':1,'item':'123456','description':'Bracket'},{'row':1,'item':'123456E','description':'Bracket - ECOAT'}]]:
            pfc.save(transcription,rows)
            with self.assertRaises(ValueError):pfc.build_image(source,transcription,self.root/'bad-job')

    def override(self):
        s=pfc.read(self.path);scene=pfc.layout(s)
        edge=s['edges'][0];key=edge['from']+'->'+edge['to']
        points=copy.deepcopy(next(p['points'] for p in scene['items'] if p.get('edge_key')==key))
        s['layout']={'connector_overrides':{key:points}}
        return s,key,points

    def test_keyed_route_survives_edge_reordering_and_export(self):
        s,key,points=self.override();s['edges'].reverse();pfc.save(self.path,s)
        scene=pfc.layout(s)
        self.assertEqual(next(p['points'] for p in scene['items'] if p.get('edge_key')==key),points)
        pfc.preview(self.path);pfc.approve(self.path,'test approval only');out=pfc.export(self.path)
        native=pfc.read(self.path.parent/'scene.json')
        self.assertEqual(next(p['points'] for p in native['items'] if p.get('edge_key')==key),points)
        with zipfile.ZipFile(out) as z:self.assertIn('xl/drawings/drawing-pfc.xml',z.namelist())

    def test_invalid_connector_keys_diagonals_and_detached_ends_fail(self):
        s,key,points=self.override()
        for overrides in [{'missing->edge':points},{key:[[1,1],[2,2]]},{key:[[1,1],[1,2]]}]:
            s['layout']['connector_overrides']=overrides
            with self.assertRaises(ValueError):pfc.layout(s)

    def test_crossing_unrelated_box_fails(self):
        s,key,points=self.override()
        # Reposition an existing hardware box across a connector's vertical run.
        s['layout']['boxes']={next(n['key'] for n in s['nodes'] if n['kind']=='hardware'):[points[0][0]-5,points[0][1]+2,10,10]}
        with self.assertRaisesRegex(ValueError,'crosses'):pfc.layout(s)

    def test_modified_delivered_html_cannot_be_approved(self):
        preview=pfc.preview(self.path)
        preview.write_text(preview.read_text()+'<!-- changed -->')
        with self.assertRaisesRegex(ValueError,'Preview changed'):pfc.approve(self.path,'test approval only')

    def test_export_preserves_png_proportions_and_bytes(self):
        image=self.path.parent/'wide.png'
        image.write_bytes(png(200,100))
        s=pfc.read(self.path);key=s['main'][-1]
        s['images']={'wide':{'path':'wide.png','sha256':pfc.sha(image),'node_key':key,'box':[450,650,100,100]}}
        pfc.save(self.path,s);pfc.preview(self.path);pfc.approve(self.path,'test approval only');out=pfc.export(self.path)
        scene=pfc.read(self.path.parent/'scene.json');picture=next(p for p in scene['items'] if p['type']=='image')
        self.assertEqual((picture['x'],picture['y'],picture['w'],picture['h']),(450,675,100,50))
        with zipfile.ZipFile(out) as z:self.assertEqual(z.read('xl/media/pfc-render-1.png'),image.read_bytes())

if __name__=='__main__':unittest.main()
