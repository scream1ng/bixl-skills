"""quote.py and render_report.py: totals must match the calculator and the page must be well formed."""
import json
import math
import re
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from calculate import calculate
from quote import run
from render_report import render

EX = ROOT / 'examples/bracket'


class QuoteTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((EX / 'quote.json').read_text())

    def test_matches_separate_handling_row(self):
        # The v1.3 example charged handling in its own row; v1.4 puts it in the laser run. Same money.
        old = calculate(json.loads((EX / 'input.json').read_text()))
        new = run(self.spec)['quantities']['100']['result']
        self.assertAlmostEqual(old['per_assembly'], new['per_assembly'], places=6)

    def test_handling_is_whole_sheets(self):
        for q, v in run(self.spec)['quantities'].items():
            r = v['result']; row = next(x for x in r['rows'] if x['id'] == 'bracket-laser')
            sheets = math.ceil(int(q) / 54)
            self.assertAlmostEqual(row['cycle_seconds']['sheet_load_unload'] * int(q), sheets * 600, places=6)

    def test_laser_row_with_setup_rejected(self):
        spec = json.loads(json.dumps(self.spec))
        next(r for r in spec['base']['rows'] if r['id'] == 'bracket-laser')['setup_h'] = 0.25
        next(r for r in spec['base']['rows'] if r['id'] == 'bracket-laser')['setup_count'] = 1
        with self.assertRaises(ValueError):
            run(spec)

    def test_quantity_in_base_rejected(self):
        spec = json.loads(json.dumps(self.spec)); spec['base']['quantity'] = 5
        with self.assertRaises(ValueError):
            run(spec)

    def test_report_renders(self):
        res = run(self.spec)
        meta = json.loads((EX / 'report_meta.json').read_text())
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'r.html'
            render(res, meta, out)
            page = out.read_text()
        self.assertNotIn('/*QUOTE*/', page)
        ids = re.findall(r'\bid="([^"]+)"', page)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn('"status":"known-cost subtotal"', page)   # unpriced e-coat carried through

    def test_unknown_meta_rejected(self):
        with self.assertRaises(ValueError):
            render(run(self.spec), {'title': 'x', 'colour': 'red'}, '/tmp/never.html')


if __name__ == '__main__':
    unittest.main()
