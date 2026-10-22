"""v1.7: trim-edge naming, sliver filter, imported-outline rebuild, edge-aware comments, user gauge edge."""
import json,subprocess,sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from test_backbar import bent
import test_sequence_preview
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import geometry as g
from physical_changes import compare_blanks
from sequence_preview import preview,step_svg,method_name
from unfold import clean_blank,boundary_area
SCRIPT=Path(__file__).resolve().parents[1]/'scripts/backbar.py'

class Revision17(unittest.TestCase):
    def test_trim_edge_naming(self):
        blank,bends,rows,frame=test_sequence_preview.SequencePreview().fixture()
        self.assertEqual(method_name(blank,rows[2],[]),'DIRECT EDGE')
        changes=compare_blanks(g.rect(-20,-40,20,40.3),blank)
        self.assertEqual(method_name(blank,rows[2],changes),'TRIM EDGE')
        rows[2]['gauging']['trial_authorized']=True
        self.assertEqual(method_name(blank,rows[2],changes),'TRIM EDGE TRIAL')
        svg=step_svg(blank,bends,rows,3,frame,changes=changes)
        self.assertIn('contact-trimmed',svg)
    def test_banner_and_labels(self):
        blank,bends,rows,frame=test_sequence_preview.SequencePreview().fixture()
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'r.html';preview(f,'R',blank,blank,bends,rows,2,[],'','p.step',[1,2,3])
            t=f.read_text()
            self.assertIn('Physical blank: UNCHANGED',t);self.assertIn('Existing part edge · no trim',t)
            self.assertNotIn('physical-changes"',t)
    def test_numerical_sliver_is_not_a_change(self):
        self.assertEqual(compare_blanks(g.rect(0,0,20,20),g.rect(0,0,20,20.00001)),[])
    def test_outline_rebuild_merges_collinear_segments(self):
        p=g.BRepBuilderAPI_MakePolygon()
        for x,y in [(0,0),(7,0),(20,0),(20,9),(20,20),(0,20)]:p.Add(g.gp_Pnt(x,y,0))
        p.Close();face=g.BRepBuilderAPI_MakeFace(p.Wire()).Face()
        clean=clean_blank(face)
        self.assertEqual(len(g.edges(clean)),4)
        self.assertAlmostEqual(boundary_area(clean),400,places=6)
        from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffset
        from OCP.GeomAbs import GeomAbs_Arc
        off=BRepOffsetAPI_MakeOffset(clean,GeomAbs_Arc);off.Perform(.1);self.assertTrue(off.IsDone())
    def test_comment_ui_records_edges_and_copies_plain_text(self):
        blank,bends,rows,frame=test_sequence_preview.SequencePreview().fixture()
        root=ET.fromstring(step_svg(blank,bends,rows,3,frame))
        picks=[e for e in root.iter() if e.attrib.get('class')=='pick']
        self.assertEqual(len(picks),len(g.edges(blank)))
        tip=[e for e in picks if e.attrib.get('data-dist')=='40.00']
        self.assertTrue(tip and float(tip[0].attrib['data-angle'])<1e-6 and tip[0].attrib['data-status']=='existing')
        self.assertIn('id="cbuf"',g.COMMENT_UI);self.assertIn("e.target.closest('[data-edge],[data-label]')",g.COMMENT_UI)
        self.assertIn('Request trim',g.COMMENT_UI)
    def test_user_gauge_edge_must_exist(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'p.step';bent(src,sym=True)
            ok=subprocess.run([sys.executable,str(SCRIPT),str(src),str(Path(d)/'a')],capture_output=True,text=True)
            self.assertEqual(ok.returncode,0,ok.stderr);tip=json.loads(ok.stdout)['plates'][0]['program_gauge_mm']
            bad=subprocess.run([sys.executable,str(SCRIPT),str(src),str(Path(d)/'b'),'--gauge-edge',f'1={tip-3}'],capture_output=True,text=True)
            self.assertNotEqual(bad.returncode,0);self.assertIn('no straight edge parallel',bad.stderr)
            good=subprocess.run([sys.executable,str(SCRIPT),str(src),str(Path(d)/'c'),'--gauge-edge',f'1={tip}'],capture_output=True,text=True)
            self.assertEqual(good.returncode,0,good.stderr)
            self.assertTrue(json.loads(good.stdout)['plates'][0]['gauging']['direct'])

if __name__=='__main__':unittest.main()
