"""Regression checks for costing validation and BOM accounting."""
import copy
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from calculate import calculate
from compare import compare


def component(cid='root', parent=None, qty=1, mode='make'):
    return dict(id=cid,name=cid,parent_id=parent,quantity_per_parent=qty,make_buy=mode)


def fixed(cid='root', price=10, rid='cost'):
    return dict(id=rid,name=rid,kind='fixed',category='other',basis='Test price',component_id=cid,unit_price=price)


def data():
    return dict(schema_version=2,quantity=100,components=[component()],rows=[fixed()])


class CostingTests(unittest.TestCase):
    def test_margin(self):
        r=calculate(data()); self.assertAlmostEqual(r['selling_per_assembly'],10/.72)
        d=data();d['gross_margin']=0;self.assertEqual(calculate(d)['selling_per_assembly'],10)
    def test_nested_quantities(self):
        d=data();d['components'] += [component('bracket','root',2),component('stud','bracket',2,'buy')]
        d['rows'] += [fixed('bracket',3,'bracket'),fixed('stud',.85,'stud')]
        r=calculate(d);self.assertAlmostEqual(r['per_assembly'],19.4)
        self.assertAlmostEqual(next(c for c in r['bom'] if c['id']=='bracket')['unit_cost'],4.7)
    def test_required_quantities_and_typos(self):
        for change in ('missing','typo'):
            d=data();d['components'][0].pop('quantity_per_parent')
            if change=='typo': d['components'][0]['quantity_per_parrent']=1
            with self.assertRaises(ValueError): calculate(d)
        d=data();d['rows'][0]['units_per_asssembly']=2
        with self.assertRaises(ValueError):calculate(d)
    def test_buy_children(self):
        d=data();d['components'][0]['make_buy']='buy';d['components'].append(component('child','root'))
        with self.assertRaises(ValueError):calculate(d)
    def test_unpriced_types_and_conflicts(self):
        for v in ('false',1,None):
            d=data();d['rows'][0]['unpriced']=v
            with self.assertRaises(ValueError):calculate(d)
        d=data();d['rows'][0]['unpriced']=True
        with self.assertRaises(ValueError):calculate(d)
        d['rows'][0].pop('unit_price');self.assertEqual(calculate(d)['status'],'known-cost subtotal')
    def test_supplier_scope(self):
        d=data();d['components'] += [component('a','root'),component('b','root')]
        d['rows']=[dict(id='coat',name='Coat',kind='supplier_batch',category='assembly_finish',basis='One order',allocations={'a':.5,'b':.5},charge_scope='supplier-order-1',lines=[dict(component_id=c,quantity=100,unit_price=1,basis='100 pieces') for c in ('a','b')],minimum_batch_charge=150,batch_fee=0)]
        r=calculate(d);self.assertEqual(r['batch_cost'],200)
        self.assertEqual(next(c for c in r['bom'] if c['id']=='a')['own_batch_cost'],100)
        d['rows'].append(dict(d['rows'][0],id='duplicate'))
        with self.assertRaises(ValueError):calculate(d)
    def test_setup_quantity_cycle(self):
        d=data();d['components'].append(component('p','root',2))
        d['rows']=[dict(id='bend',name='Bend',kind='process',category='component_processing',basis='test',component_id='p',hourly_rate=100,rate_basis='test',setup_h=.5,setup_count=1,pcs_per_h=100,cycle_seconds={'handling':12,'bend':24},cycle_basis='estimate')]
        self.assertEqual(calculate(d)['per_assembly'],2.5)
        d['rows'][0]['cycle_seconds']['bend']=30
        with self.assertRaises(ValueError):calculate(d)
    def test_procurement(self):
        d=data();d['quantity']=12;d['rows']=[dict(id='mat',name='Material',kind='material',category='material',basis='Test',component_id='root',sheet_price=100,parts_per_sheet=10,sheet_size_mm=[1200,2400],procurement='fresh',stock_moq_sheets=5)]
        r=calculate(d);self.assertEqual(r['batch_cost'],120);self.assertEqual(r['procurement'][0]['fresh_purchase_outlay'],500)
    def test_one_off_and_scrap(self):
        d=data();d['rows'].append(dict(fixed(price=500,rid='tool'),one_off=True))
        d['rows'][0].update(extra_quantity=5,extra_quantity_basis='5 rejected purchased units')
        r=calculate(d);self.assertEqual(r['batch_cost'],1050);self.assertEqual(r['one_off_batch_cost'],500)
    def test_shared_nest(self):
        d=data();d['components'] += [component('a','root'),component('b','root',2)]
        d['rows']=[dict(id='nest',name='Nest',kind='shared_batch',category='material',basis='One shared material pool',charge_scope='nest1-material',allocations={'a':.4,'b':.6},batch_cost=200,procurement=dict(sheet_price=100,consumed_sheet_equivalents=2,purchase_sheets=5,basis='MOQ 5'))]
        r=calculate(d);self.assertEqual(r['batch_cost'],200);self.assertEqual(r['procurement'][0]['purchase_outlay'],500)
    def test_comparison(self):
        old=calculate(data());d=data();d['rows'][0]['unit_price']=12
        r=compare(old,calculate(d));self.assertEqual(r['cost_delta_per_assembly'],2)
        self.assertAlmostEqual(r['selling_delta_per_assembly'],2/.72)
    def test_cycles_orphans_and_uncovered(self):
        for c in (component('p','p'),component('p','missing'),component('p','root')):
            d=data();d['components'].append(c)
            with self.assertRaises(ValueError):calculate(d)
    def test_invalid_numbers(self):
        for value in (-1, True, float('nan'), '10'):
            d=data();d['rows'][0]['unit_price']=value
            with self.assertRaises(ValueError):calculate(d)
    def test_invalid_allocation(self):
        d=data();d['rows']=[dict(id='share',name='Shared',kind='shared_batch',category='other',basis='test',allocations={'root':.5},charge_scope='s1',batch_cost=100)]
        with self.assertRaises(ValueError):calculate(d)
    def test_unknown_one_off_separate(self):
        d=data();r=fixed(rid='tool');r.pop('unit_price');r.update(unpriced=True,one_off=True);d['rows'].append(r)
        result=calculate(d);self.assertEqual(result['status'],'estimated total');self.assertEqual(result['one_off_status'],'known-cost subtotal')
    def test_revision_quantity_and_one_off(self):
        d=data();d['rows'].append(dict(fixed(price=500,rid='tool'),one_off=True))
        old=calculate(d);d['quantity']=200;d['rows'][1]['unit_price']=600
        diff=compare(old,calculate(d));self.assertEqual(diff['cost_delta_per_assembly'],0);self.assertEqual(diff['one_off_cost_delta'],100)
    def test_frozen_resource(self):
        d=data();d['rows']=[dict(id='bend',name='Bend',kind='process',category='component_processing',basis='test',component_id='root',resource='bend',setup_h=.5,setup_count=1,pcs_per_h=100,cycle_seconds={'total measured':36},cycle_basis='measured test')]
        r=calculate(d);self.assertAlmostEqual(r['input_snapshot']['rows'][0]['hourly_rate'],149.81)
        self.assertNotIn('resource',r['input_snapshot']['rows'][0]);self.assertEqual(calculate(r['input_snapshot'])['batch_cost'],r['batch_cost'])
    def test_supplier_lines_match_owner_and_quantity(self):
        d=data();d['components'].append(component('a','root',2))
        coat=dict(id='coat',name='Coat',kind='supplier_batch',category='assembly_finish',basis='test',component_id='a',charge_scope='s1',lines=[dict(component_id='root',quantity=7,unit_price=1,basis='wrong owner')],minimum_batch_charge=0,batch_fee=0)
        d['rows'].append(coat)
        with self.assertRaises(ValueError):calculate(d)
        coat['lines']=[dict(component_id='a',quantity=150,unit_price=1,basis='short')]
        with self.assertRaises(ValueError):calculate(d)
        coat['lines'][0]['quantity']=205
        self.assertAlmostEqual(calculate(d)['per_assembly'],12.05)
        coat['lines'][0]['quantity']=100
        d['rows'].append(dict(coat,id='coat2',charge_scope='s2'))
        self.assertAlmostEqual(calculate(d)['per_assembly'],12)
        d['rows'].pop();coat['lines'][0]['quantity']=3
        d['rows'].append(dict(coat,id='coat2',charge_scope='s2',lines=[dict(component_id='a',quantity=200,unit_price=1,basis='full')]))
        coat['one_off']=True
        self.assertEqual(calculate(d)['one_off_batch_cost'],3)
    def test_kind_category(self):
        d=data();d['rows'][0]=dict(id='mat',name='Material',kind='material',category='other',basis='Test',component_id='root',sheet_price=100,parts_per_sheet=10,sheet_size_mm=[1200,2400],procurement='fresh',stock_moq_sheets=0)
        with self.assertRaises(ValueError):calculate(d)
        d=data();d['rows'].append(dict(id='bend',name='Bend',kind='process',category='material',basis='test',component_id='root',hourly_rate=100,rate_basis='test',setup_h=0,setup_count=0,pcs_per_h=100,cycle_seconds={'total measured':36},cycle_basis='measured'))
        with self.assertRaises(ValueError):calculate(d)
    def test_one_off_material_no_procurement(self):
        d=data();d['rows'].append(dict(id='mat',name='Trial',kind='material',category='material',basis='Test',component_id='root',sheet_price=100,parts_per_sheet=10,sheet_size_mm=[1200,2400],procurement='fresh',stock_moq_sheets=5,one_off=True))
        self.assertEqual(calculate(d)['procurement'],[])
    def absorbed(self,pph=120):
        return dict(id='pack',name='Inspect and pack',kind='process',category='assembly_finish',basis='Routine, absorbed',component_id='root',resource='manual',setup_h=0,setup_count=0,pcs_per_h=pph,cycle_seconds={'inspect':3600/pph/2,'pack':3600/pph/2},cycle_basis='Provisional default',absorbed_in_margin=True)
    def test_absorbed_in_margin(self):
        d=data();d['rows'].append(self.absorbed())
        r=calculate(d);labour=100/120*103.22
        self.assertAlmostEqual(r['per_assembly'],10);self.assertAlmostEqual(r['absorbed_batch_cost'],labour)
        self.assertAlmostEqual(r['effective_margin'],(1000/.72-1000-labour)/(1000/.72))
        for bad in (dict(kind='fixed'),dict(one_off=True)):
            d=data();row=self.absorbed()
            if 'kind' in bad: row=dict(fixed(),id='pack',absorbed_in_margin=True)
            else: row.update(bad)
            d['rows'].append(row)
            with self.assertRaises(ValueError):calculate(d)
    def test_absorbed_comparison(self):
        d=data();d['rows'].append(self.absorbed());old=calculate(d)
        d['rows'][1]=self.absorbed(60);r=compare(old,calculate(d))
        self.assertEqual(r['cost_delta_per_assembly'],0);self.assertAlmostEqual(r['absorbed_cost_delta_per_assembly'],103.22/120)
    def test_examples_run(self):
        for path in sorted((ROOT/'examples').glob('*/input.json')):
            with self.subTest(path.parent.name):
                r=calculate(json.loads(path.read_text()));report=(path.parent/'report.md').read_text()
                for key in ('per_assembly','selling_per_assembly'): self.assertIn(f'${r[key]:.2f}',report)
    def test_contract_example(self):
        text=(ROOT/'references/calculator-contract.md').read_text()
        calculate(json.loads(text.split('```json')[1].split('```')[0]))


if __name__=='__main__': unittest.main()
