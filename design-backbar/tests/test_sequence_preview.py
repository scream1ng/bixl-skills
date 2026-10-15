"""Sequence review contracts: shared jig, direct edge, exact reference and numbering."""
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import geometry as g
from backbar import bend_permutation, tab_conflicts
from sequence_preview import preview, step_svg


class SequencePreview(unittest.TestCase):
    def fixture(self):
        identity = g.gp_Trsf()
        blank = g.rect(-20, -40, 20, 40)
        bends = [dict(T=identity, face=g.rect(-20, -1, 20, 1)) for _ in range(3)]
        plate = g.rect(-50, 20, 50, 110)
        rows = [dict(bend=i, T=identity, loc=blank, tip=40, cx=0,
                     gauging=dict(direct=i==3), tab={}, warnings=[]) for i in range(1,4)]
        rows[0].update(plate=plate)
        rows[0]['tab']=dict(piece=g.rect(10,35,15,40))
        rows[1].update(plate=plate, same_plate_as=1)
        rows[1]['tab']=dict(same_tab_as=1)
        return blank,bends,rows,identity

    def test_plate_visibility_and_shared_tab_highlight(self):
        blank,bends,rows,frame=self.fixture()
        for bend in (1,2,3):
            svg=step_svg(blank,bends,rows,bend,frame)
            root=ET.fromstring(svg)
            classes=[e.attrib.get('class','') for e in root]
            self.assertEqual('plate' in classes,bend!=3)
            self.assertEqual('gauge' in classes,bend!=3)
            self.assertEqual('active-tab' in ' '.join(classes),bend!=3)
            self.assertEqual('contact' in classes,bend==3)
            if bend!=3:
                line=next(e for e in root if e.attrib.get('class')=='gauge')
                self.assertAlmostEqual(-float(line.attrib['y1']),40)
                self.assertEqual(40+g.TIP_TO_FINGER-(-float(line.attrib['y1'])),50)

    def test_sequence_order_and_hidden_engineering_detail(self):
        blank,bends,rows,frame=self.fixture()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'review.html'
            preview(path,'Test <part>',blank,blank,bends,rows,2,[], '', 'part.step',[2,1,3])
            text=path.read_text()
            self.assertLess(text.index('data-step="2"'),text.index('data-step="1"'))
            self.assertIn('id="step-2"><h2>Step 1',text)
            self.assertIn('id="step-3" hidden',text)
            self.assertIn('Use backbar B1 / B2.',text)
            self.assertIn('DIRECT EDGE',text)
            self.assertIn('Test &lt;part&gt;',text)
            self.assertNotIn('tip_to_tab_mm',text)
            self.assertNotIn('<table',text)

    def test_bend_mapping_rejects_missing_duplicate_ids(self):
        self.assertEqual(bend_permutation('3,1,2',3,'--bend-map'),[3,1,2])
        for value in ('1,1,3','0,1,2','1,2','a,2,3'):
            with self.assertRaises(ValueError):bend_permutation(value,3,'--bend-map')

    def test_tab_conflict_in_another_bend_frame(self):
        turn=g.gp_Trsf()
        turn.SetTranslation(g.gp_Vec(0,10,0))
        ends=[dict(T=g.gp_Trsf(),tip=40),dict(T=turn,tip=45)]
        self.assertEqual(tab_conflicts(g.rect(0,35,5,40),g.gp_Trsf(),ends),[2])
        self.assertEqual(tab_conflicts(g.rect(0,30,5,35),g.gp_Trsf(),ends),[])


if __name__=='__main__':unittest.main()
