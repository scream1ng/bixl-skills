"""Regression: operation labels and valid solids cannot prove commonised CAD."""
import json,sys,tempfile,unittest
from pathlib import Path
from test_backbar import bent,write
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import geometry as g
from backbar import merge_step_faces
from completion import verify_common_step,seal_delivery,change_failures,digest
from package_delivery import package_run
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox


def two_ears(root,offset):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    bent(root/'seed.step',w=12,sym=True)
    r=g.STEPControl_Reader();r.ReadFile(str(root/'seed.step'));r.TransferRoots()
    source=next(s for s in g.sub(r.OneShape(),g.TopAbs_SOLID,g.TopoDS.Solid_s) if not g.flat_info(s))
    move=g.gp_Trsf();move.SetTranslation(g.gp_Vec(30,offset,0))
    other=g.moved(source,move)
    bridge=BRepPrimAPI_MakeBox(g.gp_Pnt(310,20,0),24,10,2).Shape()
    joined=g.BRepAlgoAPI_Fuse(g.BRepAlgoAPI_Fuse(source,bridge).Shape(),other).Shape()
    joined,_=merge_step_faces(joined);path=root/'part.step';write(path,joined)
    return path


class Completion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.bad=two_ears(cls.root/'bad',.091);cls.good=two_ears(cls.root/'good',0)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def report(self,path):
        (path.parent/'review.html').write_text('<h1>B1+B2 common operation</h1>')
        return dict(part='Fixture',step=path.name,deliverables=['part.step','review.html'],operations=[[1,2]],
                    verification={'strict_geometry_valid':True},gauging_status=[])
    def requirements(self):
        return {'reviewed':True,'changes':[dict(id='C1',kind='common_bend',bends=[1,2],description='Make B1 and B2 common in CAD')]}
    def test_offset_valid_solid_rejected_after_step_export(self):
        with self.assertRaisesRegex(ValueError,'axes differ'):verify_common_step(self.bad,[[1,2]])
        report=self.report(self.bad);seal_delivery(self.bad.parent,report,self.requirements())
        (self.bad.parent/'report.json').write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError,'Incomplete CAD'):package_run(self.bad.parent,self.bad.parent/'complete.zip')
        self.assertFalse((self.bad.parent/'complete.zip').exists())
    def test_corrected_geometry_passes_and_stale_file_rejected(self):
        report=self.report(self.good);record=seal_delivery(self.good.parent,report,self.requirements())
        self.assertEqual(record['status'],'cad_changes_verified')
        self.assertLess(record['common_readback']['checks'][0]['formed_axis_offset_mm'],.001)
        (self.good.parent/'report.json').write_text(json.dumps(report))
        package_run(self.good.parent,self.good.parent/'complete.zip')
        (self.good.parent/'review.html').write_text('stale replacement')
        with self.assertRaisesRegex(ValueError,'changed after verification'):package_run(self.good.parent,self.good.parent/'stale.zip')
    def test_cannot_relax_completion_tolerance(self):
        with self.assertRaisesRegex(ValueError,'only tighten'):verify_common_step(self.bad,[[1,2]],line_tolerance=.1)

    def test_inventory_and_physical_measurements(self):
        self.assertTrue(change_failures({'reviewed':False,'changes':[]},'abc'))
        change=dict(id='C2',kind='extension',description='Extend edge by 0.3 mm',step_sha256='abc',checks=[dict(name='extension depth',unit='mm',min=.299,max=.301,measured=0)])
        req={'reviewed':True,'changes':[change]}
        self.assertTrue(change_failures(req,'abc'))
        change['checks'][0]['measured']=.3
        self.assertFalse(change_failures(req,'abc'))
        self.assertTrue(change_failures(req,'different STEP'))
    def test_missing_common_requirement_and_interim_label(self):
        report=self.report(self.bad);seal_delivery(self.bad.parent,report,{'reviewed':True,'changes':[]})
        self.assertIn('missing from agreed-change',str(report['completion']['unresolved']))
        (self.bad.parent/'report.json').write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError,'INCOMPLETE'):package_run(self.bad.parent,self.bad.parent/'review.zip',interim=True)
        package_run(self.bad.parent,self.bad.parent/'INCOMPLETE_review.zip',interim=True)

if __name__=='__main__':unittest.main()
