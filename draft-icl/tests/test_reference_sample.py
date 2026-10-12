import copy
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from presentation import normalize


class ReferenceSample(unittest.TestCase):
    def spec(self,process):
        return {'process':process,'checks':[{'key':'thickness','description':'Thickness','gauge':'Vernier','nominal':3,'unit':'mm','group':'setup'if process=='laser'else'main'},
                                           {'key':'hole','description':'Hole','gauge':'Vernier','nominal':6,'unit':'mm','group':'hourly'if process=='laser'else'main'}]}

    def test_all_processes_receive_one_sample_without_upstream_measurements(self):
        for process,prefix in [('laser','L'),('bending','B'),('welding','W')]:
            with self.subTest(process=process):
                result=normalize(self.spec(process));samples=[c for c in result['checks']if c['key']=='reference_sample']
                self.assertEqual(len(samples),1);sample=samples[0]
                self.assertEqual([sample[k]for k in ['description','limits','gauge']],['Check part to Reference sample','Reference Sample','Visual'])
                self.assertNotIn('nominal',sample)
                self.assertEqual(result['checks'][1 if process=='laser'else 0]['key'],'reference_sample')
                self.assertEqual([c['id']for c in result['checks']],[prefix+str(i)for i in range(1,4)])
                self.assertEqual(normalize(result),result)

    def test_existing_sample_preserves_stable_key_evidence_and_method(self):
        result=normalize(self.spec('bending'));sample=result['checks'][0]
        sample.update(key='shop_sample',source='Controlled sample S12, revision C',method='Compare external profile against S12-C.')
        again=normalize(result)
        self.assertEqual(again['checks'][0],sample)
        self.assertEqual(len(again['checks']),3)

    def test_duplicates_and_changed_criteria_fail(self):
        result=normalize(self.spec('bending'));duplicate=copy.deepcopy(result['checks'][0]);duplicate['key']='second_sample';result['checks'].append(duplicate)
        with self.assertRaisesRegex(ValueError,'Duplicate reference'):normalize(result)
        for field,value in [('limits','TBC'),('gauge','Vernier'),('nominal',1),('tolerance',.5)]:
            with self.subTest(field=field):
                result=normalize(self.spec('bending'));result['checks'][0][field]=value
                with self.assertRaisesRegex(ValueError,'criteria were altered'):normalize(result)
        result=normalize(self.spec('bending'));result['checks'][0].update(key='shop_sample',gauge='Vernier')
        with self.assertRaisesRegex(ValueError,'criteria were altered'):normalize(result)

    def test_laser_profile_has_large_labels_and_unique_final_sop(self):
        layout=json.loads((ROOT/'processes/laser/layout.json').read_text());result=normalize(self.spec('laser'),layout)
        self.assertEqual(result['presentation']['balloon_scale'],2)
        self.assertEqual(result['checks'][1]['key'],'reference_sample')
        self.assertEqual(result['checks'][-1]['limits'],'SOP008')
        self.assertEqual(normalize(result,layout),result)
        result['presentation']['balloon_scale']=1.5
        self.assertEqual(normalize(result,layout)['presentation']['balloon_scale'],1.5)

    def test_explicit_profile_exception_does_not_add_sample(self):
        spec=self.spec('bending');result=normalize(spec,{'profile':{'reference_sample_check':False}})
        self.assertEqual(len(result['checks']),2)


if __name__=='__main__':unittest.main()
