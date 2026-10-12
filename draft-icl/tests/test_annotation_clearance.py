"""Regression tests for annotation clashes missed by leader-only validation."""
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from annotation_clearance import validate


def svg(contents):
    return ET.fromstring('<svg viewBox="0 0 2000 480">' + contents + '</svg>')


class ClearanceTests(unittest.TestCase):
    def test_reported_rear_angle_badge_on_height_line(self):
        root = svg('<g data-check="rear_height"><line x1="1900" y1="105" x2="1900" y2="375"/></g>'
                   '<g data-check="rear_angle"><rect x="1860" y="201" width="60" height="38" stroke="red"/></g>')
        with self.assertRaisesRegex(ValueError, 'rear_angle.*rear_height'):
            validate(root)
        root[1][0].set('x', '1720')
        self.assertEqual(validate(root)['labels_checked'], 1)

    def test_badge_vs_own_dimension_endpoint(self):
        with self.assertRaisesRegex(ValueError, 'intersects'):
            validate(svg('<g data-check="height"><line x1="100" y1="80" x2="100" y2="160"/>'
                         '<rect x="70" y="60" width="60" height="38" stroke="red"/></g>'))

    def test_badge_and_numeric_value_overlap(self):
        with self.assertRaisesRegex(ValueError, 'badges/values overlap'):
            validate(svg('<g data-check="angle"><rect x="100" y="100" width="102" height="30"/>'
                         '<rect x="190" y="96" width="60" height="38" stroke="red"/></g>'))

    def test_intentional_own_balloon_join_and_value_mask(self):
        validate(svg('<g data-check="hole"><polyline points="80,150 150,150"/>'
                     '<rect x="125" y="125" width="50" height="50" stroke="red"/></g>'
                     '<g data-check="height"><line x1="300" y1="100" x2="300" y2="200"/>'
                     '<rect x="280" y="140" width="60" height="30"/></g>'))

    def test_diagonal_contact_and_arc_are_checked(self):
        for line in ('<line x1="0" y1="0" x2="100" y2="100"/>',
                     '<path d="M 100 50 A 50 50 0 0 1 50 100"/>'):
            with self.assertRaisesRegex(ValueError, 'intersects'):
                validate(svg('<g data-check="angle">'+line+'</g>'
                             '<g data-check="badge"><rect x="76" y="76" width="24" height="24" stroke="red"/></g>'))

    def test_clipped_label_rejected(self):
        with self.assertRaisesRegex(ValueError, 'clipped'):
            validate(svg('<g data-check="height"><rect x="-1" y="0" width="60" height="38" stroke="red"/></g>'))


if __name__ == '__main__':
    unittest.main()
