"""Multi-body STEP split and grouping (skipped without the CAD engine)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
try:
    from OCP.BRep import BRep_Builder
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
    from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
    from OCP.TopoDS import TopoDS_Compound
except ImportError:
    BRep_Builder = None


@unittest.skipIf(BRep_Builder is None, 'OCP not installed')
class MultiBody(unittest.TestCase):
    def test_groups_identical_bodies(self):
        comp = TopoDS_Compound(); b = BRep_Builder(); b.MakeCompound(comp)
        b.Add(comp, BRepPrimAPI_MakeBox(200, 100, 2).Shape())
        for x in (20, 60):
            ax = gp_Ax2(gp_Pnt(x, 50, 2), gp_Dir(0, 0, 1))
            b.Add(comp, BRepPrimAPI_MakeCylinder(ax, 3, 20).Shape())
        with tempfile.TemporaryDirectory() as d:
            step = Path(d) / 'multi.step'
            w = STEPControl_Writer(); w.Transfer(comp, STEPControl_AsIs); w.Write(str(step))
            out = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'step_geometry.py'), str(step),
                                  '--outline', str(Path(d) / 'flat.json')],
                                 capture_output=True, text=True, check=True).stdout
            r = json.loads(out)
            self.assertEqual(r['solids'], 3)
            self.assertEqual(r['body_groups'], 2)
            plate, studs = r['bodies']
            self.assertEqual((plate['qty'], plate['role']), (1, 'sheet'))
            self.assertAlmostEqual(plate['thickness_mm'], 2.0, places=1)
            self.assertTrue((Path(d) / 'flat-B1.json').exists())
            self.assertEqual(studs['qty'], 2)
            self.assertTrue(studs['role'].startswith('non-sheet'))


if __name__ == '__main__':
    unittest.main()
