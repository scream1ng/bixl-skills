"""Common operations, short contacts, physical differences and delivery isolation."""
import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from zipfile import ZipFile
from test_backbar import bent
import test_sequence_preview
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import geometry as g
from operations import operation_sequence,validate_common_groups
from physical_changes import compare_blanks
from package_delivery import package_run
from sequence_preview import preview

class Revision15(unittest.TestCase):
    def test_group_sequence(self):
        ends=[dict(between=[4]),dict(between=[3]),dict(between=[]),dict(between=[]),dict(between=[])]
        self.assertEqual(operation_sequence('1+4,2+3,5',ends),[[1,4],[2,3],[5]])
        for value in ('1+4,2+3','1+4,2+3,4','4,1,2,3,5'):
            with self.assertRaises(ValueError):operation_sequence(value,ends)
    def test_common_axes(self):
        bends=[dict(d=[1,0,0],p=[0,0,0],angle_deg=90),dict(d=[-1,0,0],p=[20,.05,0],angle_deg=90)]
        with self.assertRaises(ValueError):validate_common_groups([[1,2]],bends)
        self.assertAlmostEqual(validate_common_groups([[1,2]],bends,.1)[0]['line_offset_mm'],.05)
        bends[1]['angle_deg']=45
        with self.assertRaises(ValueError):validate_common_groups([[1,2]],bends,.1)
    def test_physical_overlay_and_group(self):
        original=g.rect(0,0,20,20);revised=g.rect(0,.2,20,20.3)
        changes=compare_blanks(original,revised)
        self.assertEqual([c['kind'] for c in changes],['added','removed'])
        self.assertAlmostEqual(changes[0]['sampled_max_offset_mm'],.3,places=5)
        self.assertAlmostEqual(changes[1]['sampled_max_offset_mm'],.2,places=5)
        self.assertEqual(compare_blanks(original,original),[])
        blank,bends,rows,frame=test_sequence_preview.SequencePreview().fixture()
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'review.html'
            preview(file,'Review',blank,blank,bends,rows,2,[],'','part.step',operations=[[1,2],[3]],original_blank=g.rect(-20,-40.2,20,39.7))
            text=file.read_text()
            self.assertIn('B1 + B2',text);self.assertNotIn('id="step-2"',text)
            self.assertIn('Physical part changes',text);self.assertIn('C1',text);self.assertIn('C2',text)
            self.assertIn('Approx. maximum local offset',text)
            self.assertLess(text.index('<section class="physical-changes">'),text.index('<div class="layout">'))
    def test_short_contact_cli_and_manifest(self):
        script=Path(__file__).resolve().parents[1]/'scripts/backbar.py'
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'short.step';bent(source,w=9,sym=True)
            requirements=root/'requirements.json';requirements.write_text(json.dumps({'reviewed':True,'changes':[]}))
            for trial in (False,True):
                out=root/str(trial)
                args=[sys.executable,str(script),str(source),str(out),'--package','--requirements',str(requirements)]
                if trial:args+=['--direct-trial','1']
                run=subprocess.run(args,capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stderr)
                report=json.loads(run.stdout);row=report['plates'][0]
                self.assertTrue(row['gauging']['short_contact_candidate'])
                self.assertEqual(row['gauging']['direct'],trial)
                self.assertNotIn('width_mm',row['tab'])
                self.assertEqual(report['gauging_status'][0]['method'],'DIRECT EDGE TRIAL' if trial else 'BACKBAR OPTION')
                (out/'stale.dxf').write_text('stale')
                archive=package_run(out,out/'check.zip')
                with ZipFile(archive) as z:
                    self.assertNotIn('stale.dxf',z.namelist());self.assertNotIn('report.json',z.namelist())
                    self.assertEqual(set(z.namelist()),set(report['deliverables'])|{'README.txt'})

if __name__=='__main__':unittest.main()
