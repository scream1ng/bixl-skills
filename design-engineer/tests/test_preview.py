"""Stage preview coverage checks; run in the CAD environment."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import build123d as b

path = Path(__file__).resolve().parents[1] / 'scripts/preview.py'
spec = importlib.util.spec_from_file_location('preview', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        part = b.Box(100, 60, 20) + b.Pos(0, 0, 20) * b.Cylinder(10, 20)
        self.step = self.dir / 'model.step'
        b.export_step(part, str(self.step))
        self.elements = [{'id': 'E1', 'name': 'Base', 'value': '100 x 60 x 20', 'source': 'provided', 'anchor': [0, -30, 0]},
                         {'id': 'E2', 'name': 'Boss', 'value': 'D20', 'source': 'estimated', 'anchor': [0, 0, 30]}]

    def run_preview(self, elements, stage='blockout', html=False, front=None):
        spec = {'project': 't', 'revision': 'r1', 'elements': elements, **({'front': front} if front else {})}
        (self.dir / 'elements.json').write_text(json.dumps(spec))
        return module.generate(self.step, self.dir / 'elements.json', self.dir / 'out', stage, html)

    def test_sheet_and_html_cover_every_element(self):
        result = self.run_preview(self.elements, html=True)
        self.assertTrue(Path(result['sheet']).is_file())
        self.assertEqual(result['hidden_in_all_views'], [])
        page = Path(result['html']).read_text()
        self.assertNotIn('__SCENE_GZIP_BASE64__', page)
        self.assertLess(result['bytes'], module.INLINE_HTML_LIMIT)

    def test_missing_anchor_blocks_and_removes_stale_outputs(self):
        self.run_preview(self.elements, html=True)
        broken = self.elements + [{'id': 'E3', 'name': 'Slot'}]
        with self.assertRaisesRegex(module.Blocked, 'E3: missing anchor'):
            self.run_preview(broken, html=True)
        self.assertFalse((self.dir / 'out/sheet.png').exists())
        self.assertFalse((self.dir / 'out/preview.html').exists())

    def test_anchor_outside_model_blocks(self):
        with self.assertRaisesRegex(module.Blocked, 'outside model bounds'):
            self.run_preview([dict(self.elements[0], anchor=[500, 0, 0])])

    def test_hidden_everywhere_needs_reason(self):
        underside = {'id': 'E3', 'name': 'Underside', 'source': 'assumed', 'anchor': [0, 0, -10]}
        with self.assertRaisesRegex(module.Blocked, 'E3'):
            self.run_preview(self.elements + [underside])
        self.assertFalse((self.dir / 'out/sheet.png').exists())
        result = self.run_preview(self.elements + [dict(underside, hidden='flat, see underside.png')])
        self.assertEqual(result['hidden_in_all_views'], ['E3'])

    def test_legend_fits_many_elements(self):
        from PIL import Image
        many = [dict(self.elements[0], id=f'E{i}') for i in range(40)]
        image = Image.open(self.run_preview(many)['sheet'])
        self.assertGreaterEqual(image.height, 100 + 46 * 40)

    def test_pending_allowed_until_detail(self):
        pending = self.elements + [{'id': 'E3', 'name': 'Vent', 'status': 'pending'}]
        self.assertEqual(self.run_preview(pending)['pending'], ['E3'])
        with self.assertRaisesRegex(module.Blocked, 'pending at detail'):
            self.run_preview(pending, stage='detail')

    def test_stl_input(self):
        stl = self.dir / 'model.stl'
        b.export_stl(b.import_step(str(self.step)), str(stl))
        self.step = stl
        self.assertEqual(self.run_preview(self.elements)['components'], 1)

    def test_front_axis_turns_product_face_to_front_view(self):
        back_face = {'id': 'E3', 'name': 'Logo', 'source': 'provided', 'anchor': [0, 30, 0]}
        with self.assertRaisesRegex(module.Blocked, 'E3'):
            self.run_preview(self.elements + [back_face])
        result = self.run_preview([self.elements[1], back_face], front='+Y')  # E1 (-Y) is now the back
        self.assertEqual(result['hidden_in_all_views'], [])
        with self.assertRaisesRegex(module.Blocked, 'front must be one of'):
            self.run_preview(self.elements, front='Y')

    def test_untessellatable_face_is_retried_then_skipped(self):
        class Bad:
            area = 2.0
            def tessellate(self, *_): raise AttributeError('no triangulation')

        class Shape:
            def tessellate(self, *_): raise AttributeError('no triangulation')
            def faces(self): return [b.Box(10, 10, 10).faces()[0], Bad()]
        skipped = []
        self.assertGreater(len(module.triangles(Shape(), skipped)), 0)
        self.assertEqual(skipped, [2.0])

    def test_viewer_keeps_detail_within_size_limit(self):
        b.export_step(b.Sphere(40) - b.Pos(0, 0, 40) * b.Cylinder(15, 20), str(self.step))
        elements = [{'id': 'E1', 'name': 'Dome', 'source': 'provided', 'anchor': [0, -40, 0]}]
        result = self.run_preview(elements, html=True)
        full = len(module.load_components(self.step)[0][0][1])
        self.assertGreater(full, 500)
        self.assertEqual(result['faces'], full)  # fits, so nothing is decimated
        self.assertLess(result['bytes'], module.INLINE_HTML_LIMIT)


if __name__ == '__main__':
    unittest.main()
