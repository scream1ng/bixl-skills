"""Design board build checks; standard library + Pillow."""
import base64
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image

path = Path(__file__).resolve().parents[1] / 'scripts/board.py'
spec = importlib.util.spec_from_file_location('board', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BoardTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        for name, color in (('a.png', 'red'), ('b.png', 'blue')):
            Image.new('RGB', (1600, 900), color).save(self.dir / name)
        (self.dir / 'elements.json').write_text(json.dumps({'elements': [
            {'id': 'E1', 'name': 'Plate', 'value': '100 x 60', 'source': 'provided', 'image': 'a.png'},
            {'id': 'E2', 'name': 'Boss', 'value': 'D20', 'source': 'estimated'}]}))
        (self.dir / 'preview.html').write_text('<!doctype html><p>viewer "quoted"</p>')
        self.board = {'project': 'Test', 'revision': 'r1', 'stage': 'blockout', 'next': ['Answer Q1'],
                      'sections': [{'title': 'Concept', 'bullets': ['x'], 'images': [{'src': 'a.png', 'caption': 'A'}],
                                    'compare': [{'a': 'a.png', 'b': 'b.png'}]}],
                      'elements': 'elements.json', 'viewer': 'preview.html',
                      'decisions': [{'date': '2026-10-06', 'text': 'ok'}], 'open': ['LED']}

    def build(self):
        (self.dir / 'board.json').write_text(json.dumps(self.board))
        return module.build(self.dir / 'board.json')

    def test_builds_full_quality_page_with_cards_and_viewer(self):
        result = self.build()
        page = Path(result['board']).read_text()
        for marker in ('__TITLE__', '__NAV__', '__BODY__'):
            self.assertNotIn(marker, page)
        uri = page.split('src="data:image/png;base64,', 1)[1].split('"', 1)[0]
        self.assertEqual(Image.open(io.BytesIO(base64.b64decode(uri))).size, (1600, 900))
        self.assertEqual(page.count('class="card"'), 2)
        self.assertIn('to confirm', page)
        self.assertIn('class="cmp"', page)
        self.assertIn('<iframe srcdoc="', page)
        self.assertIn('viewer &quot;quoted&quot;', page)

    def test_missing_image_blocks_and_removes_stale_board(self):
        out = Path(self.build()['board'])
        self.board['sections'][0]['images'].append({'src': 'gone.png'})
        with self.assertRaisesRegex(module.Blocked, 'missing image: gone.png'):
            self.build()
        self.assertFalse(out.exists())

    def test_non_image_blocks(self):
        self.board['sections'][0]['images'] = [{'src': 'elements.json'}]
        with self.assertRaisesRegex(module.Blocked, 'not an image'):
            self.build()


if __name__ == '__main__':
    unittest.main()
