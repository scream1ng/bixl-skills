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

    def run_preview(self, elements, stage='blockout', html=False, front=None, **more):
        spec = {'project': 't', 'revision': 'r1', 'elements': elements, **({'front': front} if front else {})}
        (self.dir / 'elements.json').write_text(json.dumps(spec))
        return module.generate(self.step, self.dir / 'elements.json', self.dir / 'out', stage, html, **more)

    def test_draft_views_and_one_snapshot_per_element(self):
        from PIL import Image
        result = self.run_preview(self.elements, with_snapshots=True)
        self.assertEqual(sorted(result['views']), ['front', 'iso', 'rear', 'right', 'top'])
        self.assertEqual(Image.open(result['views']['iso']).size, (1000, 760))
        self.assertEqual(sorted(result['snapshots']), ['E1', 'E2'])
        boss = Image.open(result['snapshots']['E2']); self.assertEqual(boss.size, (640, 480))
        self.assertGreater(len(boss.convert('L').getcolors(1 << 16)), 8)      # shaded geometry, not a blank frame
        self.assertEqual(result['snapshot_missing'], [])
        self.assertNotIn('image', json.loads((self.dir / 'elements.json').read_text())['elements'][0])  # no silent edits

    def test_snapshot_from_underside_is_evidence_for_a_hidden_element(self):
        underside = {'id': 'E3', 'name': 'Underside', 'source': 'assumed', 'anchor': [0, 0, -10]}
        with self.assertRaisesRegex(module.Blocked, 'E3'):
            self.run_preview(self.elements + [underside])
        result = self.run_preview(self.elements + [underside], with_snapshots=True)
        self.assertEqual(result['hidden_in_all_views'], ['E3'])
        self.assertIn('E3', result['snapshots'])

    def test_fill_images_sets_basis_by_stage_and_keeps_own_pictures(self):
        from PIL import Image
        Image.new('RGB', (40, 40)).save(self.dir / 'section.png')
        own = dict(self.elements[1], image='section.png', image_basis='cad', approval='assumed')
        self.run_preview([dict(self.elements[0], approval='agreed'), own], stage='detail', fill_images=True)
        saved = json.loads((self.dir / 'elements.json').read_text())['elements']
        self.assertEqual(saved[0]['image'], 'out/elements/E1.jpg'); self.assertEqual(saved[0]['image_basis'], 'final')
        self.assertEqual(saved[0]['anchor'], [0, -30, 0])                    # anchors stay in model coordinates
        self.assertEqual(saved[1]['image'], 'section.png')
        self.assertEqual(self.run_preview(saved, fill_images=True)['filled'], ['E1'])
        self.assertEqual(json.loads((self.dir / 'elements.json').read_text())['elements'][0]['image_basis'], 'cad')

    def test_fill_images_replaces_snapshots_from_another_out_and_clears_stale_ones(self):
        self.run_preview(self.elements, fill_images=True)
        saved = json.loads((self.dir / 'elements.json').read_text())['elements']
        self.assertTrue(saved[0]['image_auto'])
        spec = {'project': 't', 'revision': 'r1', 'elements': saved}
        (self.dir / 'elements.json').write_text(json.dumps(spec))
        module.generate(self.step, self.dir / 'elements.json', self.dir / 'out-r2', 'blockout', fill_images=True)
        saved = json.loads((self.dir / 'elements.json').read_text())['elements']
        self.assertEqual(saved[0]['image'], 'out-r2/elements/E1.jpg')
        saved[1]['status'] = 'pending'
        self.run_preview(saved, fill_images=True)
        boss = json.loads((self.dir / 'elements.json').read_text())['elements'][1]
        self.assertFalse({'image', 'image_basis', 'image_caption', 'image_auto'} & set(boss))

    def test_duplicate_step_labels_become_unique_components(self):
        from unittest.mock import patch
        x = b.Box(10, 10, 10); x.label = 'part'; y = b.Pos(30, 0, 0) * b.Box(5, 6, 5); y.label = 'part'
        shape = type('Shape', (), {'solids': lambda self: [x, y]})()          # labels do not survive a STEP round trip
        with patch.object(b, 'import_step', return_value=shape):
            self.assertEqual([n for n, _ in module.load_components(self.step)[0]], ['part', 'part_2'])
            result = self.run_preview([{'id': 'E1', 'name': 'Cube', 'source': 'provided', 'anchor': [0, -5, 0]}], with_snapshots=True)
        self.assertEqual(result['components'], 2)

    def test_unsafe_element_id_is_blocked(self):
        with self.assertRaisesRegex(module.Blocked, 'HTML-safe'):
            self.run_preview([dict(self.elements[0], id='../E1')], with_snapshots=True)

    def test_whole_part_frame_fits_the_part(self):
        from PIL import Image
        result = self.run_preview([dict(self.elements[0], frame=100)], with_snapshots=True)
        im = Image.open(result['snapshots']['E1']).convert('L'); w, h = im.size
        border = [im.getpixel((x, y)) for x in range(w) for y in (0, h - 1)] + [im.getpixel((x, y)) for y in range(h) for x in (0, w - 1)]
        self.assertGreater(min(border), 240)                                   # nothing clipped at the edges

    def test_internal_element_is_reported_not_faked(self):
        from PIL import Image
        Image.new('RGB', (40, 40)).save(self.dir / 'core.png')
        inside = {'id': 'E3', 'name': 'Core', 'source': 'assumed', 'anchor': [0, 0, 10], 'hidden': 'solid interior', 'image': 'core.png'}
        result = self.run_preview(self.elements + [inside], with_snapshots=True)
        self.assertEqual(result['snapshot_missing'], ['E3'])

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
        with self.assertRaisesRegex(module.Blocked, 'E3'):  # a description alone is not evidence
            self.run_preview(self.elements + [dict(underside, hidden='flat', image='underside.png')])
        from PIL import Image
        Image.new('RGB', (40, 40)).save(self.dir / 'underside.png')
        result = self.run_preview(self.elements + [dict(underside, hidden='flat', image='underside.png')])
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

    def test_detail_needs_user_approval_not_just_a_measurement(self):
        with self.assertRaisesRegex(module.Blocked, 'E1: not approved'):  # E1 is provided but unapproved
            self.run_preview(self.elements, stage='detail')
        approved = [dict(self.elements[0], approval='agreed'), dict(self.elements[1], approval='assumed')]
        self.assertEqual(self.run_preview(approved, stage='detail')['elements'], 2)

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

    def test_missing_model_blocks_with_a_message(self):
        self.step = self.dir / 'nope.step'
        with self.assertRaisesRegex(module.Blocked, 'model not found: .*nope.step'):
            self.run_preview(self.elements)

    def test_anchor_off_the_surface_blocks(self):
        for bad in ([40, 0, 20], [0, 0, 0]):                                   # in the air beside the boss; buried in the base
            with self.assertRaisesRegex(module.Blocked, 'E3: anchor is 10.0 mm from the model surface'):
                self.run_preview(self.elements + [{'id': 'E3', 'name': 'Bad', 'source': 'assumed', 'anchor': bad}])
        with self.assertRaisesRegex(module.Blocked, r'nearest surface point \[40.00, 0.00, 10.00\]'):
            self.run_preview(self.elements + [{'id': 'E3', 'name': 'Bad', 'source': 'assumed', 'anchor': [40, 0, 20]}], front='+X')
        with self.assertRaisesRegex(module.Blocked, 'E3: anchor .* three finite numbers'):
            self.run_preview(self.elements + [{'id': 'E3', 'name': 'Bad', 'source': 'assumed', 'anchor': [float('nan'), 0, 0]}])

    def test_snapshot_faces_the_element_surface(self):
        # Low on the front face: the old side-of-the-part rule picked an underside view for it.
        self.run_preview(self.elements, with_snapshots=True, fill_images=True)
        saved = json.loads((self.dir / 'elements.json').read_text())['elements']
        self.assertTrue(saved[0]['image_caption'].endswith('from iso'))

    def test_own_images_in_snapshot_folders_survive(self):
        from PIL import Image
        (self.dir / 'out/elements').mkdir(parents=True)
        Image.new('RGB', (40, 40)).save(self.dir / 'out/elements/E1-section.jpg')
        Image.new('RGB', (40, 40), 'red').save(self.dir / 'out/elements/E3.jpg')   # a section named like a snapshot
        core = {'id': 'E3', 'name': 'Core', 'source': 'assumed', 'anchor': [0, 0, 0], 'hidden': 'interior',
                'image': 'out/elements/E3.jpg', 'image_basis': 'cad'}
        base = dict(self.elements[0], image='out/elements/E1-section.jpg', image_basis='cad')
        self.run_preview([base, self.elements[1], core], with_snapshots=True, fill_images=True)
        self.assertTrue((self.dir / 'out/elements/E1-section.jpg').is_file())
        self.assertEqual(Image.open(self.dir / 'out/elements/E3.jpg').getpixel((5, 5)), (254, 0, 0))
        saved = json.loads((self.dir / 'elements.json').read_text())['elements']
        self.assertEqual([saved[0]['image'], saved[2]['image']], ['out/elements/E1-section.jpg', 'out/elements/E3.jpg'])
        self.assertNotIn('image_auto', saved[0])

    def test_wall_in_front_hides_an_inner_part(self):
        # A closed 1.5 mm housing around an inner block: the block's face is on a surface but never visible.
        b.export_step(b.Compound([b.Box(100, 100, 100) - b.Box(97, 97, 97), b.Box(97, 97, 97)]), str(self.step))
        shell = {'id': 'E1', 'name': 'Housing', 'source': 'provided', 'anchor': [0, -50, 0]}
        inner = {'id': 'E2', 'name': 'Inner block', 'source': 'provided', 'anchor': [0, -48.5, 0]}
        with self.assertRaisesRegex(module.Blocked, 'hidden in all views without section/detail evidence: E2;'):
            self.run_preview([shell, inner], with_snapshots=True)

    def test_old_auto_snapshot_is_not_section_evidence(self):
        from PIL import Image
        Image.new('RGB', (40, 40)).save(self.dir / 'old.jpg')
        core = {'id': 'E3', 'name': 'Core', 'source': 'assumed', 'anchor': [0, 0, 0], 'hidden': 'interior',
                'image': 'old.jpg', 'image_basis': 'cad', 'image_auto': True}
        with self.assertRaisesRegex(module.Blocked, 'E3: anchor is'):
            self.run_preview(self.elements + [core], with_snapshots=True, fill_images=True)

    def test_comment_positions_use_the_model_frame(self):
        import base64, gzip, re, struct
        import numpy as np
        result = self.run_preview(self.elements, html=True, front='+X', with_snapshots=True)
        blob = max(re.findall(r'[A-Za-z0-9+/=]{200,}', Path(result['html']).read_text()), key=len)
        raw = gzip.decompress(base64.b64decode(blob)); n = struct.unpack('<I', raw[:4])[0]
        scene = json.loads(raw[4:4 + n])
        for shown, own in zip(scene['elements'], self.elements):      # viewer anchors map back to elements.json
            np.testing.assert_allclose(np.array(shown['anchor']) @ np.array(scene['unturn']), own['anchor'], atol=1e-9)

    def test_viewer_byte_budget(self):
        import numpy as np
        g = np.linspace(0, 100, 121); x, y = np.meshgrid(g, g); z = 5 * np.sin(x / 7) * np.cos(y / 9)
        v = np.stack([x, y, z], -1); a, b_, c, d = v[:-1, :-1], v[:-1, 1:], v[1:, 1:], v[1:, :-1]
        tris = np.concatenate([np.stack([a, b_, c], -2).reshape(-1, 3, 3), np.stack([a, c, d], -2).reshape(-1, 3, 3)])
        out = self.dir / 'out'; out.mkdir()
        full = module.html([('p', tris)], [], {}, 'blockout', out)
        small = module.html([('p', tris)], [], {}, 'blockout', out, limit=full[0])
        self.assertLess(small[0], full[0]); self.assertLess(small[1], full[1])

    def test_packed_viewer_meshes_round_trip(self):
        import numpy as np
        part = b.Sphere(40) - b.Pos(0, 0, 40) * b.Cylinder(15, 20)
        mesh = module.compact_mesh(module.triangles(part, []), 10**9)
        info, origin, step, blob = module.pack_meshes([{'id': 'p', **mesh}, {'id': 'q', **mesh}])
        # Same decoding as assets/preview.html.
        raw, offset, decoded = np.frombuffer(blob, np.uint8), 0, []
        def planes(count, width):
            nonlocal offset
            out = sum(raw[offset + p * count:offset + (p + 1) * count].astype(np.int64) << (8 * p) for p in range(width))
            offset += count * width; return out
        for c in info:
            n = c['vertices']; pos = np.asarray(origin) + planes(3 * n, 2).reshape(3, n).T * np.asarray(step)
            index, newest = [], -1
            for k in planes(3 * c['faces'], 3):
                v = newest + 1 - int(k); index.append(v); newest = max(newest, v)
            decoded.append(pos[np.array(index)].reshape(-1, 3, 3))
        self.assertEqual(offset, len(blob))
        original = np.asarray(mesh['positions']).reshape(-1, 3)[np.asarray(mesh['indices'])].reshape(-1, 3, 3)
        for d in decoded:
            self.assertLessEqual(np.abs(d - original).max(), max(step) / 2 + 1e-9)


if __name__ == '__main__':
    unittest.main()
