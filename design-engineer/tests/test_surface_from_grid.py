"""Geometry checks for the shared surface constructor; run in the CAD environment."""
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest
import numpy as np
import build123d as b
from OCP.BRep import BRep_Tool

path = Path(__file__).resolve().parents[1] / 'scripts/surface_from_grid.py'
spec = importlib.util.spec_from_file_location('surface_from_grid', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def point(u, v):
    x, z = 40*u-20, 30*v-15
    y = -.002*(x*x+z*z) + .3*(1+math.cos(2*math.pi*(z+.25*x)/7))
    return x, y, z


class SurfaceGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.face = module.surface_from_grid(
            [[point(u, v) for v in np.linspace(0, 1, 31)]
             for u in np.linspace(0, 1, 41)])

    def test_shape_between_input_samples(self):
        surface = BRep_Tool.Surface_s(self.face.wrapped)
        # Independent positions, including near-boundary locations.
        errors = []
        for u in np.linspace(.013, .987, 47):
            for v in np.linspace(.019, .981, 43):
                actual = surface.Value(float(u), float(v))
                expected = point(u, v)
                errors.append(math.dist((actual.X(), actual.Y(), actual.Z()), expected))
        self.assertLess(max(errors), .01)

    def test_join_cut_and_step_roundtrip(self):
        base = b.Solid.extrude(self.face.moved(b.Location((0, -.25, 0))), (0, -2, 0))
        relief = b.Solid.extrude(self.face, (0, -.5, 0))
        joined = base.fuse(relief)
        cutter = b.Solid.make_cylinder(3, 10, b.Plane(
            origin=(8, -5, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0)))
        result = joined.cut(cutter)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.solids()), 1)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'panel.STEP'
            b.export_step(result, output)
            reopened = b.import_step(output)
        self.assertTrue(reopened.is_valid)
        self.assertEqual(len(reopened.solids()), 1)
        self.assertFalse(reopened.is_inside((8, -1, 0)))
        self.assertTrue(reopened.is_inside((0, -1, 0)))


if __name__ == '__main__':
    unittest.main()
