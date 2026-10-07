"""Board contract and evidence integrity checks, standard library + Pillow."""
import base64
import importlib.util
import io
import json
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from PIL import Image

path = Path(__file__).resolve().parents[1] / 'scripts/board.py'
spec = importlib.util.spec_from_file_location('board', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class Structure(HTMLParser):
    def __init__(self):
        super().__init__(); self.sections=[]; self.banner=False; self.images=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='section': self.sections.append(attrs.get('id'))
        if tag in ('header','nav'): self.banner=True
        if tag=='img' and attrs.get('src'):self.images.append(attrs['src'])

class BoardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.dir=Path(self.temp.name)
        for name,color in [('a.png','red'),('b.png','grey')]:
            Image.new('RGB',(1600,900),color).save(self.dir/name)
        self.elements=[{'id':'E1','name':'Plate','value':'100 × 60','source':'provided','image':'a.png','image_basis':'cad'},
                       {'id':'E2','name':'Boss','source':'estimated','approval':'assumed','image':'b.png','image_basis':'cad',
                        'questions':['Select hardware before production.']}]
        (self.dir/'preview.html').write_text('<!doctype html><p>viewer "quoted"</p>')
        self.board={'schema_version':2,'project':'Test <part>','revision':'CAD R1','board_revision':'R2','stage':'proposal',
                    'elements':'elements.json','viewer':'preview.html',
                    'review':{'images':[{'src':'a.png','basis':'concept','caption':'Option A'}],
                              'compare':[{'a':'a.png','a_basis':'concept','b':'b.png','b_basis':'cad'}]},
                    'history':[{'revision':'R1','summary':'Initial geometry.'}],
                    'board_history':[{'revision':'R2','summary':'Added detail.'}]}
    def build(self):
        (self.dir/'elements.json').write_text(json.dumps({'elements':self.elements}))
        (self.dir/'board.json').write_text(json.dumps(self.board))
        return module.build(self.dir/'board.json')
    def test_full_quality_three_sections_and_provenance(self):
        result=self.build();page=Path(result['delivery_board']).read_text();parsed=Structure();parsed.feed(page)
        self.assertEqual(parsed.sections,['review','elements','history']);self.assertFalse(parsed.banner)
        self.assertEqual(page.count('class="element"'),2)
        self.assertEqual(Image.open(io.BytesIO(base64.b64decode(parsed.images[0].split(',')[1]))).size,(1600,900))
        self.assertIn('Approval: open',page);self.assertIn('Approval: assumed',page)
        self.assertNotIn('Approval: agreed',page)
        self.assertIn('Select hardware before production.',page)
        self.assertIn('viewer &quot;quoted&quot;',page)
        self.assertIn('Test &lt;part&gt;',page)
        self.assertEqual(Path(result['delivery_board']).name,'board-R2.html')
    def test_all_elements_need_snapshot(self):
        self.elements[1].pop('image')
        with self.assertRaisesRegex(module.Blocked,'E2.*snapshot'):self.build()
    def test_missing_image_removes_stale_output(self):
        out=Path(self.build()['board']);self.elements[0]['image']='gone.png'
        with self.assertRaisesRegex(module.Blocked,'missing image'):self.build()
        self.assertFalse(out.exists())
    def test_non_image_and_evidence_labels(self):
        self.elements[0]['image']='elements.json'
        with self.assertRaisesRegex(module.Blocked,'not an image'):self.build()
        self.elements[0]['image']='a.png';self.elements[0].pop('image_basis')
        with self.assertRaisesRegex(module.Blocked,'image basis'):self.build()
    def test_final_snapshots_cannot_be_concepts(self):
        self.board['stage']='delivery';self.board['review']['images'][0]['basis']='final'
        with self.assertRaisesRegex(module.Blocked,'delivered geometry'):self.build()
        for e in self.elements:e['image_basis']='final'
        self.build()
    def test_concept_board_without_viewer(self):
        self.board.pop('viewer');page=Path(self.build()['board']).read_text()
        self.assertIn('Design Review',page);self.assertNotIn('<iframe',page)
    def test_legacy_content_is_not_silently_lost(self):
        self.board['sections']=[{'title':'Important detail'}]
        with self.assertRaisesRegex(module.Blocked,'legacy sections'):self.build()
    def test_deferral_requires_actual_approval_record(self):
        self.elements[0]['deferrals']=[{'question':'Material?','assumption':'PLA'}]
        with self.assertRaisesRegex(module.Blocked,'explicit approval record'):self.build()
    def test_elements_paths_follow_elements_file(self):
        sub=self.dir/'parts';sub.mkdir()
        for n in ['a.png','b.png']:(sub/n).write_bytes((self.dir/n).read_bytes())
        (sub/'elements.json').write_text(json.dumps({'elements':self.elements}))
        self.board['elements']='parts/elements.json';self.build()
    def test_duplicate_ids_block(self):
        self.elements[1]['id']='E1'
        with self.assertRaisesRegex(module.Blocked,'unique'):self.build()

if __name__=='__main__':unittest.main()
