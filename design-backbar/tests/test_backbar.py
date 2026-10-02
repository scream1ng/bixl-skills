"""Regression tests on flat patterns built with OCP primitives; no fixture files."""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from OCP.BRep import BRep_Builder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
from OCP.BRepGProp import BRepGProp
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakePrism
from OCP.GProp import GProp_GProps
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.TopTools import TopTools_ListOfShape
from OCP.TopoDS import TopoDS_Compound
from OCP.gp import gp_Pnt, gp_Vec

SKILL = Path(__file__).resolve().parent.parent / 'SKILL.md'
T = 2.0


def prism(pp):
    p = BRepBuilderAPI_MakePolygon()
    for x, y in pp:
        p.Add(gp_Pnt(x, y, 0))
    p.Close()
    return BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(p.Wire()).Face(), gp_Vec(0, 0, T)).Shape()


def part(path, w=60.0, bends=1):
    """Flat pattern with separate bend-strip faces (3 mm strips) plus a formed L body of equal volume.
    Flange A ends on a slant: 40 deep at x=0, 25 at x=w. Bend 1 centre y=1.5; bend 2 centre y=81.5, 17 mm flange beyond."""
    faces = [prism([(0, -40), (w, -25), (w, 0), (0, 0)]), prism([(0, 0), (w, 0), (w, 3), (0, 3)]),
             prism([(0, 3), (w, 3), (w, 80), (0, 80)])]
    if bends == 2:
        faces += [prism([(0, 80), (w, 80), (w, 83), (0, 83)]), prism([(0, 83), (w, 83), (w, 100), (0, 100)])]
    args, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
    args.Append(faces[0])
    for f in faces[1:]:
        tools.Append(f)
    fuse = BRepAlgoAPI_Fuse(); fuse.SetArguments(args); fuse.SetTools(tools); fuse.Build()
    flat = fuse.Shape()
    g = GProp_GProps(); BRepGProp.VolumeProperties_s(flat, g)
    formed = BRepAlgoAPI_Fuse(BRepPrimAPI_MakeBox(gp_Pnt(300, 0, 0), w, 90, T).Shape(),
                              BRepPrimAPI_MakeBox(gp_Pnt(300, 0, 0), w, T, g.Mass() / w / T - 90 + T).Shape()).Shape()
    c = TopoDS_Compound(); b = BRep_Builder(); b.MakeCompound(c); b.Add(c, flat); b.Add(c, formed)
    wr = STEPControl_Writer(); wr.Transfer(c, STEPControl_AsIs); wr.Write(str(path))


class Backbar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        code = re.search(r'^```python backbar.py\n(.*?)^```$', SKILL.read_text(), re.S | re.M).group(1)
        cls.script = cls.tmp / 'backbar.py'
        cls.script.write_text(code)
        for name, kw in (('one', {}), ('two', {'bends': 2}), ('wide', {'w': 85.0})):
            part(cls.tmp / f'{name}.step', **kw)

    def run_script(self, name, *opts):
        out = self.tmp / f'out_{name}_{len(opts)}'
        r = subprocess.run([sys.executable, str(self.script), str(self.tmp / f'{name}.step'), str(out), *opts],
                           capture_output=True, text=True)
        return r, out

    def plates(self, name, *opts):
        r, out = self.run_script(name, *opts)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)['plates'], out

    def test_one_bend_gauges_slanted_end(self):
        (p,), out = self.plates('one')
        self.assertEqual((p['wrap_mm'], p['front_edge_to_bend_mm'], p['bend_to_finger_tip_mm']), (20.0, 21.5, 91.5))
        self.assertEqual((p['wall_each_side_mm'], p['clearance_mm'], p['warnings']), (19.9, 0.1, []))
        self.assertTrue((out / p['dxf']).exists())

    def test_two_bends_free_side_and_die_clearance(self):
        (p1, p2), _ = self.plates('two')
        self.assertEqual((p1['front_edge_to_bend_mm'], p1['bend_to_finger_tip_mm']), (21.5, 91.5))
        self.assertEqual((p2['wrap_mm'], p2['front_edge_to_bend_mm'], p2['bend_to_finger_tip_mm']), (10.5, 8.0, 68.5))
        self.assertNotEqual(p1['side'], p2['side'])

    def test_forced_side_into_other_bend_is_error(self):
        (p1, _), _ = self.plates('two', '--side', '1=' + ('-' if self.plates('two')[0][0]['side'] == '+' else '+'))
        self.assertIn('error', p1)
        self.assertNotIn('dxf', p1)

    def test_bad_side_rejected(self):
        for s in ('1=+-', '0=+', '1=', 'x=+', '5=+'):
            r, _ = self.run_script('two', '--side', s)
            self.assertNotEqual(r.returncode, 0, s)
            self.assertIn('ERROR: --side', r.stderr, s)

    def test_too_wide_is_error_without_dxf(self):
        (p,), out = self.plates('wide')
        self.assertIn('does not fit', p['error'])
        self.assertEqual(sorted(f.name for f in out.iterdir()), ['preview.html'])


if __name__ == '__main__':
    unittest.main()
