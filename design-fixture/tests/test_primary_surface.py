"""Primary datum points of a part share one trimmed face; a second surface (across a bend or step) fails."""
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
import primary_surface


def box(x0, y0, z0, x1, y1, z1):
    return BRepPrimAPI_MakeBox(gp_Pnt(x0, y0, z0), gp_Pnt(x1, y1, z1)).Shape()


def fuse(*shapes):
    out = shapes[0]
    for s in shapes[1:]: out = BRepAlgoAPI_Fuse(out, s).Shape()
    return out


# Lower leg bottom z=0 (x 0..50), riser, upper leg bottom z=10 (x 50..100): two surfaces a bend/step apart.
STEPPED = fuse(box(0, 0, 0, 50, 20, 5), box(45, 0, 0, 50, 20, 15), box(50, 0, 10, 100, 20, 15))


def a(name, xyz):
    return {'name': name, 'role': 'Primary', 'part': 'Tube', 'contact': list(xyz), 'normal': [0, 0, 1]}


def spec(*contacts, **extra):
    return {'workpiece': {'parts': {'Tube': 'Part_1'}}, 'contacts': list(contacts), **extra}


class PrimarySurfaceTests(unittest.TestCase):
    def run_with(self, s):
        return primary_surface.audit(s, {'Part_1': STEPPED})

    def test_points_spread_along_one_face_pass(self):
        r = self.run_with(spec(a('A1', (5, 10, 0)), a('A2', (40, 5, 0)), a('A3', (40, 15, 0))))
        self.assertEqual(r['status'], 'pass')

    def test_point_on_a_second_surface_fails_with_a_fix(self):
        r = self.run_with(spec(a('A1', (5, 10, 0)), a('A2', (40, 10, 0)), a('A3', (90, 10, 10))))
        self.assertEqual(r['status'], 'fail')
        self.assertIn('Tube: move primary points A1, A2, A3 onto one face', r['next_action'])

    def test_user_quoted_waiver_is_an_exception_not_a_pass(self):
        s = spec(a('A1', (5, 10, 0)), a('A3', (90, 10, 10)),
                 primary_surface_waivers=[{'part': 'Tube', 'reason': 'user: "step is machined, use both"'}])
        self.assertEqual(self.run_with(s)['status'], 'exception')

    def test_secondary_and_auxiliary_points_are_not_primary(self):
        side = {'name': 'B1', 'role': 'Secondary', 'part': 'Tube', 'contact': [90, 10, 10], 'normal': [0, 0, 1]}
        self.assertEqual(self.run_with(spec(a('A1', (5, 10, 0)), a('A2', (40, 10, 0)), side))['status'], 'pass')

    def test_point_off_the_part_is_unknown(self):
        self.assertEqual(self.run_with(spec(a('A1', (5, 10, 0)), a('A2', (5, 10, -3))))['status'], 'unknown')

    def test_coplanar_flanges_either_side_of_a_raised_web_fail(self):
        hat = fuse(box(0, 0, 0, 40, 20, 3), box(37, 0, 0, 40, 20, 20), box(37, 0, 17, 63, 20, 20),
                   box(60, 0, 0, 63, 20, 20), box(60, 0, 0, 100, 20, 3))
        r = primary_surface.audit(spec(a('A1', (5, 10, 0)), a('A2', (95, 10, 0))), {'Part_1': hat})
        self.assertEqual(r['status'], 'fail')

    def test_one_surface_split_by_the_export_passes(self):
        split = fuse(box(0, 0, 0, 50, 20, 5), box(50, 0, 0, 100, 20, 5))  # no unify: two bottom faces sharing an edge
        r = primary_surface.audit(spec(a('A1', (5, 10, 0)), a('A2', (95, 10, 0))), {'Part_1': split})
        self.assertEqual(r['status'], 'pass', r)
        self.assertEqual(len(set(r['parts'][0]['faces'].values())), 2)


if __name__ == '__main__':
    unittest.main()
