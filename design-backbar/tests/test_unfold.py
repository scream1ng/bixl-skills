"""Unfold a bend on a concave flange whose centroid is across the tangent."""
import math,sys,unittest
from pathlib import Path
from test_backbar import prism,fuse,T
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace,BRepBuilderAPI_MakePolygon,BRepBuilderAPI_Transform
from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevol
from OCP.gp import gp_Ax1,gp_Dir,gp_Pnt,gp_Trsf

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'scripts'))
import geometry as g
from unfold import unfold

class Unfold(unittest.TestCase):
    def test_concave_notch_uses_local_material_side(self):
        root=prism([(0,0),(100,0),(100,60),(80,60),(80,20),(0,20)])
        ax=gp_Ax1(gp_Pnt(80,0,4),gp_Dir(0,1,0))
        section=BRepBuilderAPI_MakePolygon()
        for y,z in ((20,0),(60,0),(60,T),(20,T)):
            section.Add(gp_Pnt(80,y,z))
        section.Close()
        bend=BRepPrimAPI_MakeRevol(BRepBuilderAPI_MakeFace(section.Wire()).Face(),ax,math.pi/2).Shape()
        rotation=gp_Trsf();rotation.SetRotation(ax,math.pi/2)
        child=BRepBuilderAPI_Transform(prism([(65,20),(80,20),(80,60),(65,60)]),rotation,True).Shape()
        formed=fuse([root,bend,child])
        self.assertTrue(g.BRepCheck_Analyzer(formed).IsValid())
        blank,bends,thickness,carriers=unfold(formed)
        self.assertTrue(g.BRepCheck_Analyzer(blank).IsValid())
        self.assertEqual(len(bends),1)
        self.assertEqual(len(carriers),2)
        self.assertAlmostEqual(thickness,T)
        self.assertAlmostEqual(g.area(blank),2800+600+40*3*math.pi/2,places=5)

if __name__=='__main__':unittest.main()
