"""End-to-end contract tests on generated, non-part-specific STEP fixtures."""
import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from test_backbar import bent,write
SCRIPT=Path(__file__).resolve().parent.parent/'scripts'/'backbar.py'
sys.path.insert(0,str(SCRIPT.parent))
import geometry as g

class Workflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(tempfile.mkdtemp())
        bent(cls.root/'nearly_parallel.step',drop=.2)
        for name,square in [('angled',False),('parallel',True)]:
            path=cls.root/(name+'.step');bent(path,sym=square)
            r=g.STEPControl_Reader();r.ReadFile(str(path));r.TransferRoots()
            solids=g.sub(r.OneShape(),g.TopAbs_SOLID,g.TopoDS.Solid_s)
            formed=[s for s in solids if not g.flat_info(s)][0]
            write(cls.root/(name+'_formed.step'),formed)
    def run_case(self,name,*opts):
        out=Path(tempfile.mkdtemp(dir=self.root))
        r=subprocess.run([sys.executable,str(SCRIPT),str(self.root/(name+'.step')),str(out),*opts],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        return json.loads(r.stdout),out
    def check_files(self,r,out):
        self.assertTrue((out/r['step']).is_file());self.assertTrue((out/r['preview']).is_file())
        self.assertFalse(any('flat' in f.name for f in out.iterdir()))
        self.assertEqual(r['trims'],[])
    def test_supplied_flat_angled(self):
        r,out=self.run_case('angled');self.check_files(r,out)
        self.assertFalse(r['estimated_unfold']);self.assertEqual(len(list(out.glob('*.dxf'))),1)
        self.assertFalse(r['plates'][0]['gauging']['direct'])
    def test_parallel_supplied_flat_no_backbar(self):
        r,out=self.run_case('parallel');self.check_files(r,out)
        self.assertTrue(r['plates'][0]['gauging']['direct']);self.assertEqual(list(out.glob('*.dxf')),[])
    def test_formed_only_angled(self):
        r,out=self.run_case('angled_formed');self.check_files(r,out)
        self.assertTrue(r['estimated_unfold']);self.assertEqual(len(list(out.glob('*.dxf'))),1)
    def test_formed_only_parallel(self):
        r,out=self.run_case('parallel_formed');self.check_files(r,out)
        self.assertTrue(r['estimated_unfold']);self.assertEqual(list(out.glob('*.dxf')),[])
    def test_nearly_parallel_does_not_trim(self):
        r,out=self.run_case('nearly_parallel');self.check_files(r,out)
        self.assertFalse(r['plates'][0]['gauging']['direct']);self.assertEqual(len(list(out.glob('*.dxf'))),1)
    def test_invalid_option_no_deliverables(self):
        out=self.root/'invalid';r=subprocess.run([sys.executable,str(SCRIPT),str(self.root/'angled.step'),str(out),'--trim-for','99'],capture_output=True,text=True)
        self.assertNotEqual(r.returncode,0);self.assertFalse(out.exists())

if __name__=='__main__':unittest.main()
