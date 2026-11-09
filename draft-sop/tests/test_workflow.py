import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import sop  # noqa: E402
from fill import fill_sop  # noqa: E402


def job(tmp, n=3, **overrides):
    (tmp / 'photos').mkdir()
    steps = []
    for i in range(n):
        Image.new('RGB', (900, 600) if i % 2 else (600, 900), (120, 100, 90)).save(tmp / 'photos' / f'p{i}.jpg')
        steps.append({'key': f's{i}', 'photo': f'photos/p{i}.jpg', 'text': f'Fit part ① step {i}',
                      'callouts': [{'n': 1, 'at': [0.5, 0.5], 'tag': [0.1, 0.1]}],
                      'marks': [{'type': 'oval', 'x': 0.3, 'y': 0.3, 'w': 0.4, 'h': 0.4}]})
    spec = {'version': 1, 'revision': 1, 'part': {'number': '1', 'name': 'Test part', 'doc_no': 'A1'}, 'steps': steps}
    spec.update(overrides)
    (tmp / 'spec.json').write_text(json.dumps(spec, ensure_ascii=False))
    return tmp / 'spec.json'


class Workflow(unittest.TestCase):
    def test_full_flow_and_gates(self):
        with tempfile.TemporaryDirectory() as d:
            spec = job(Path(d), n=10)
            sop.prep(spec)
            sop.preview(spec)
            with self.assertRaises(ValueError):
                sop.export(spec)  # no approval
            sop.approve(spec, 'test approval')
            out = sop.export(spec)
            self.assertIn('2 page(s), 10 photos', out)
            data = json.loads(spec.read_text())
            data['steps'][0]['text'] = 'Changed ①'
            spec.write_text(json.dumps(data, ensure_ascii=False))
            with self.assertRaises(ValueError):
                sop.export(spec)  # stale approval

    def test_text_rules(self):
        with tempfile.TemporaryDirectory() as d:
            spec = job(Path(d), n=1)
            data = json.loads(spec.read_text())
            data['steps'][0]['text'] = 'one two three four five six seven eight nine ten eleven ①'
            spec.write_text(json.dumps(data, ensure_ascii=False))
            with self.assertRaisesRegex(ValueError, 'max 10'):
                sop.load(spec)
            data['steps'][0]['text'] = 'Fit part ③'
            spec.write_text(json.dumps(data, ensure_ascii=False))
            with self.assertRaisesRegex(ValueError, 'no callout 3'):
                sop.load(spec)

    def test_every_template_fills(self):
        img = Image.new('RGB', (800, 600), 'grey')
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'x.jpg'
            img.save(p)
            for fmt, sizes in sop.FORMATS.items():
                for spp in sizes:
                    data = fill_sop([{'image': str(p), 'text': 'x', 'annotations': []}] * (spp + 1),
                                    '1', 'n', 'A1', format_key=fmt, steps_per_page=spp)
                    self.assertGreater(len(data), 1000, f'{fmt} {spp}')

    def test_bullets_in_word(self):
        from docx import Document
        with tempfile.TemporaryDirectory() as d:
            spec = job(Path(d), n=1)
            data = json.loads(spec.read_text())
            data['steps'][0]['text'] = ['Pack part ①', ['611061', '611060']]
            spec.write_text(json.dumps(data, ensure_ascii=False))
            sop.prep(spec); sop.preview(spec); sop.approve(spec, 'ok')
            out = Path(sop.export(spec).splitlines()[0])
            cell = Document(str(out)).tables[0].rows[2].cells[0]
            from docx.oxml.ns import qn
            self.assertEqual([p.text for p in cell.paragraphs], ['Pack part ①', '611061', '611060'])
            self.assertEqual([p._p.pPr.find(qn('w:numPr')).find(qn('w:ilvl')).get(qn('w:val')) for p in cell.paragraphs], ['0', '1', '1'])
            self.assertEqual(cell.paragraphs[0].runs[0].font.size.pt, 14)

    def test_label_leader_and_check_sheet(self):
        with tempfile.TemporaryDirectory() as d:
            spec = job(Path(d), n=1)
            data = json.loads(spec.read_text())
            data['steps'][0]['marks'] = [{'type': 'text', 'x': 0.05, 'y': 0.02, 'w': 0.2, 'h': 0.06, 'text': '611061 Template', 'to': [0.5, 0.5]}]
            spec.write_text(json.dumps(data, ensure_ascii=False))
            sop.prep(spec)
            marks = sop.compile_marks(sop.load(spec)[1]['steps'][0], (600, 900))
            arrow = next(m for m in marks if m['type'] == 'arrow' and m['x2'] == 0.5)
            self.assertAlmostEqual(arrow['y1'], 0.08, places=2)  # starts at the label's bottom edge
            self.assertIn('check-r1.jpg', str(sop.preview(spec)))

    def test_auto_steps_per_page(self):
        with tempfile.TemporaryDirectory() as d:
            _, spec = sop.load(job(Path(d), n=3))
            self.assertEqual(spec['steps_per_page'], 4)


if __name__ == '__main__':
    unittest.main()
