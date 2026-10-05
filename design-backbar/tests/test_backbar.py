"""Regression tests on flat patterns built with OCP primitives; no fixture files."""
import json
import math
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from OCP.BRep import BRep_Builder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon, BRepBuilderAPI_Transform
from OCP.BRepGProp import BRepGProp
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakePrism, BRepPrimAPI_MakeRevol
from OCP.GProp import GProp_GProps
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Reader, STEPControl_Writer
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopTools import TopTools_ListOfShape
from OCP.TopoDS import TopoDS_Compound
from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec

SKILL = Path(__file__).resolve().parent.parent / 'SKILL.md'
T = 2.0


def prism(pp):
    p = BRepBuilderAPI_MakePolygon()
    for x, y in pp:
        p.Add(gp_Pnt(x, y, 0))
    p.Close()
    return BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(p.Wire()).Face(), gp_Vec(0, 0, T)).Shape()


def fuse(shapes):
    args, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
    args.Append(shapes[0])
    for f in shapes[1:]:
        tools.Append(f)
    f = BRepAlgoAPI_Fuse(); f.SetArguments(args); f.SetTools(tools); f.Build()
    return f.Shape()


def volume(s):
    g = GProp_GProps(); BRepGProp.VolumeProperties_s(s, g); return g.Mass()


def write(path, *shapes):
    c = TopoDS_Compound(); b = BRep_Builder(); b.MakeCompound(c)
    for s in shapes:
        b.Add(c, s)
    wr = STEPControl_Writer(); wr.Transfer(c, STEPControl_AsIs); wr.Write(str(path))


def bent(path, w=60.0, sym=False, drop=15.0):
    """Flat pattern plus a truly folded L (2 mm inner radius, 90 deg) so the tab can be carried onto the folded part.
    Flange A ends on a slant (40 deep at x=0, 25 at x=w) unless sym, then it is square (40 deep)."""
    a = [(0, -40), (w, -40 if sym else -40 + drop), (w, 0), (0, 0)]
    flat = fuse([prism(a), prism([(0, 0), (w, 0), (w, 4.71), (0, 4.71)]), prism([(0, 4.71), (w, 4.71), (w, 80), (0, 80)])])
    ax = gp_Ax1(gp_Pnt(0, 0, T + 2), gp_Dir(-1, 0, 0))
    p = BRepBuilderAPI_MakePolygon()
    for x, z in ((0, 0), (w, 0), (w, T), (0, T)):
        p.Add(gp_Pnt(x, 0, z))
    p.Close()
    rot = gp_Trsf(); rot.SetRotation(ax, math.pi / 2)
    formed = fuse([prism([(0, 0), (w, 0), (w, 80 - 4.71), (0, 80 - 4.71)]),
                   BRepPrimAPI_MakeRevol(BRepBuilderAPI_MakeFace(p.Wire()).Face(), ax, math.pi / 2).Shape(),
                   BRepBuilderAPI_Transform(prism(a), rot, True).Shape()])
    mv = gp_Trsf(); mv.SetTranslation(gp_Vec(300, 0, 0))
    write(path, flat, BRepBuilderAPI_Transform(formed, mv, True).Shape())
    return volume(formed)


def part(path, w=60.0, bends=1):
    """Flat pattern with separate bend-strip faces (3 mm strips) plus a formed L body of equal volume.
    Flange A ends on a slant: 40 deep at x=0, 25 at x=w. Bend 1 centre y=1.5; bend 2 centre y=81.5, 17 mm flange beyond."""
    faces = [prism([(0, -40), (w, -25), (w, 0), (0, 0)]), prism([(0, 0), (w, 0), (w, 3), (0, 3)]),
             prism([(0, 3), (w, 3), (w, 80), (0, 80)])]
    if bends == 2:
        faces += [prism([(0, 80), (w, 80), (w, 83), (0, 83)]), prism([(0, 83), (w, 83), (w, 100), (0, 100)])]
    flat = fuse(faces)
    formed = BRepAlgoAPI_Fuse(BRepPrimAPI_MakeBox(gp_Pnt(300, 0, 0), w, 90, T).Shape(),
                              BRepPrimAPI_MakeBox(gp_Pnt(300, 0, 0), w, T, volume(flat) / w / T - 90 + T).Shape()).Shape()
    write(path, flat, formed)


class Backbar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.script = SKILL.parent / 'scripts' / 'geometry.py'
        for name, kw in (('one', {}), ('two', {'bends': 2}), ('wide', {'w': 85.0})):
            part(cls.tmp / f'{name}.step', **kw)
        cls.bent_volume = bent(cls.tmp / 'bent.step')
        bent(cls.tmp / 'square.step', sym=True)

    def run_script(self, name, *opts):
        out = Path(tempfile.mkdtemp(dir=self.tmp))
        r = subprocess.run([sys.executable, str(self.script), str(self.tmp / f'{name}.step'), str(out), *opts],
                           capture_output=True, text=True)
        return r, out

    def result(self, name, *opts):
        r, out = self.run_script(name, *opts)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout), out

    def plates(self, name, *opts):
        res, out = self.result(name, *opts)
        return res['plates'], out

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

    def test_forced_side_beyond_other_bend_warns(self):
        (p1, _), out = self.plates('two', '--side', '1=' + ('-' if self.plates('two')[0][0]['side'] == '+' else '+'))
        self.assertIn('bend this one first', p1['warnings'][0])
        self.assertTrue((out / p1['dxf']).exists())

    def test_bad_side_rejected(self):
        for s in ('1=+-', '0=+', '1=', 'x=+', '5=+', '1=++'):
            r, _ = self.run_script('two', '--side', s)
            self.assertNotEqual(r.returncode, 0, s)
            self.assertIn('ERROR: --side', r.stderr, s)

    def test_bad_at_rejected(self):
        for s in ('0=10', '1=', '1=nan', '1=inf', 'x=10', '2=10', '1=10=2'):
            r, _ = self.run_script('one', '--at', s)
            self.assertNotEqual(r.returncode, 0, s)
            self.assertIn('ERROR: --at', r.stderr, s)

    def test_too_wide_is_error_without_dxf(self):
        (p,), out = self.plates('wide')
        self.assertIn('does not fit', p['plate_error'])
        self.assertNotIn('dxf', p)
        self.assertEqual(sorted(f.name for f in out.iterdir()), ['preview.html'])

    def test_step_with_tab_on_folded_part(self):
        res, out = self.result('bent')
        (p,) = res['plates']
        tab = p['tab']
        self.assertEqual((res['step'], res['notes'], p['warnings']), ('bent_with_tab.step', [], []))
        self.assertEqual((tab['placed'], tab['width_mm'], tab['heights_mm'], tab['edge_off_tip_line_mm']), ('widest', 5.0, [8.75, 10.0], 0.0))
        self.assertEqual(p['bend_to_finger_tip_mm'], round(p['program_gauge_mm'] + 50, 2))
        r = STEPControl_Reader(); r.ReadFile(str(out / res['step'])); r.TransferRoots()
        e, solids = TopExp_Explorer(r.OneShape(), TopAbs_SOLID), []
        while e.More():
            solids.append(e.Current()); e.Next()
        self.assertEqual(len(solids), 1)
        self.assertAlmostEqual(volume(solids[0]) - self.bent_volume, 5 * 9.375 * T, places=2)   # 5 wide, 8.75..10 tall

    def test_forced_tab_position(self):
        side = self.plates('bent')[0][0]['tab']['tip_to_tab_outer_mm'] < 0 and -1 or 1
        (p,), _ = self.plates('bent', '--at', f'1={side * 20}')
        self.assertEqual((p['tab']['placed'], p['tab']['tip_to_tab_outer_mm'], p['tab']['tip_to_tab_mm']), ('forced', side * 20.0, 15.0))
        (p,), _ = self.plates('bent', '--at', '1=3')
        self.assertIn('at least the tab width', p['tab']['error'])

    def test_square_end_needs_no_tab(self):
        res, out = self.result('square')
        self.assertIn('no tab needed', res['plates'][0]['tab']['skipped'])
        self.assertIsNone(res['step'])
        self.assertFalse(any(f.suffix == '.step' for f in out.iterdir()))


if __name__ == '__main__':
    unittest.main()
