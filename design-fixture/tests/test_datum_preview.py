"""Stage 3.5 datum scheme preview and its hard-predecessor gate."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import workflow as wf
from datum_preview import generate

class DatumPreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        shutil.copytree(ROOT / 'examples/flat-plate', self.path / 'input')
        self.spec = self.path / 'input/spec.json'

    def edit(self, **changes):
        data = json.loads(self.spec.read_text()); data.update(changes)
        self.spec.write_text(json.dumps(data)); return data

    def test_markers_carry_321_roles_and_no_fixture_geometry(self):
        result = generate(self.spec, self.path / 'datum')
        self.assertEqual(result['counts'], {'Primary': 3, 'Secondary': 2, 'Tertiary': 1, 'Auxiliary': 0, 'Clamp': 1})
        self.assertEqual(result['off_surface'], [])
        scene = json.loads((self.path / 'datum/datum-scene.json').read_text())
        self.assertTrue(all(c['group'] == 'workpiece' for c in scene['components']))
        self.assertEqual({m['color'] for m in scene['markers'] if m['role'] == 'Primary'}, {'#1b6ec2'})
        self.assertNotIn('__SCENE_JSON__', (self.path / 'datum/datum-preview.html').read_text())
        self.assertFalse(list((self.path / 'datum').glob('*.step')))
        self.assertFalse(list((self.path / 'datum').glob('*.dxf')))

    def test_point_off_the_part_is_reported_not_silently_moved(self):
        data = json.loads(self.spec.read_text())
        data['contacts'][0]['contact'] = [-50.0, -30.0, 90.0]
        self.spec.write_text(json.dumps(data))
        result = generate(self.spec, self.path / 'datum')
        self.assertEqual(result['off_surface'], ['A1'])

    def test_concept_requires_a_current_datum_review(self):
        record = wf.initialize(self.spec, 'weld')
        self.assertFalse(wf.datum_reviewed(record))
        with self.assertRaises(ValueError): wf.datum_ok(record, 'Looks right')
        record['datum_preview'] = {**generate(self.spec, self.path / 'datum'), 'datum_digest': record['datum_digest']}
        with self.assertRaises(ValueError): wf.datum_ok(record, '  ')
        wf.datum_ok(record, 'Primaries on the base flange are right')
        self.assertTrue(wf.datum_reviewed(record))

    def test_moving_a_datum_stales_the_review_but_an_unrelated_edit_does_not(self):
        record = wf.initialize(self.spec, 'weld')
        record['datum_preview'] = {**generate(self.spec, self.path / 'datum'), 'datum_digest': record['datum_digest']}
        wf.datum_ok(record, 'Reviewed')
        self.edit(decisions=['Taller clamp platform'])
        wf.resume(self.spec, record)
        self.assertTrue(wf.datum_reviewed(record))
        data = json.loads(self.spec.read_text())
        data['contacts'][1]['contact'] = [40.0, -30.0, 60.0]
        self.spec.write_text(json.dumps(data))
        wf.resume(self.spec, record)
        self.assertFalse(wf.datum_reviewed(record))

    def test_cannot_ack_a_scheme_that_was_never_previewed(self):
        record = wf.initialize(self.spec, 'weld')
        record['datum_preview'] = {**generate(self.spec, self.path / 'datum'), 'datum_digest': record['datum_digest']}
        data = json.loads(self.spec.read_text())
        data['contacts'][0]['contact'] = [-45.0, -30.0, 60.0]
        self.spec.write_text(json.dumps(data))
        wf.resume(self.spec, record)
        with self.assertRaises(ValueError): wf.datum_ok(record, 'Fine by me')
        self.assertFalse(wf.datum_reviewed(record))

    def test_datum_review_never_satisfies_finalization(self):
        record = wf.initialize(self.spec, 'weld')
        record['datum_preview'] = {**generate(self.spec, self.path / 'datum'), 'datum_digest': record['datum_digest']}
        wf.datum_ok(record, 'Reviewed')
        record['stage'] = 'datum_preview'
        with self.assertRaises(ValueError): wf.authorize(record, 'Finalize the package')
        with self.assertRaises(ValueError): wf.finalization_allowed(self.spec, record)

if __name__ == '__main__': unittest.main()
