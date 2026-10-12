import copy
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import icl
from presentation import pack_views


class DrawingLabels(unittest.TestCase):
    def setUp(self):
        self.spec={'checks':[{'key':'slot','id':'L1','feature':'slot','unit':'mm',
                             'measurements':[{'key':'width','nominal':6.1},{'key':'length','nominal':10}]}],
                   'drawing':{'width':600,'height':400,'dimensions':[],
                              'balloons':[{'checks':['slot'],'target':[100,250],'badge_xy':[100,50],
                                           'show_value':True,'value_xy':[300,50]}]}}
        self.geometry=b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400"/>'

    def test_balloon_dimensions_follow_check_values(self):
        rendered=icl.render_svg(self.spec,self.geometry)
        self.assertIn('6.1 × 10 mm',rendered)
        self.spec['checks'][0]['measurements'][1]['nominal']=11.2
        rendered=icl.render_svg(self.spec,self.geometry)
        self.assertIn('6.1 × 11.2 mm',rendered)
        self.assertNotIn('6.1 × 10 mm',rendered)

    def test_balloon_value_shares_view_transform(self):
        s=copy.deepcopy(self.spec);d=s['drawing'];d.update(source_width=600,source_height=400,views=[{'key':'flat','source_box':[0,0,600,400],'box':[0,0,300,200]}])
        d['balloons'][0].update(view='flat',value_xy=[420,60],badge_xy=[100,60])
        wire=self.geometry.replace(b'/>',b'><g data-view="flat"/></svg>')
        mapped,_=pack_views(s,wire)
        self.assertEqual(mapped['drawing']['balloons'][0]['value_xy'],[210,30])
        self.assertIn('x="210.0" y="38.0"',icl.render_svg(s,wire))

    def test_linear_dimension_uses_two_arrows_without_slash_ticks(self):
        self.spec['checks']=[{'key':'height','id':'B2','nominal':13,'unit':'mm'}]
        self.spec['drawing']['balloons']=[]
        self.spec['drawing']['dimensions']=[{'check':'height','kind':'vertical','a':[100,100],'b':[100,250],
                                            'offset':300,'badge_xy':[380,50],'value_xy':[380,180]}]
        root=ET.fromstring(icl.render_svg(self.spec,self.geometry));ns={'s':icl.SVG}
        self.assertEqual(len(root.findall('.//s:polygon',ns)),2)
        self.assertEqual(len(root.findall('.//s:g[@data-check]/s:line',ns)),3)

    def test_balloon_value_cannot_cover_its_own_leader(self):
        self.spec['drawing']['balloons'][0]['value_xy']=[100,170]
        with self.assertRaisesRegex(ValueError,'intersects'):
            icl.render_svg(self.spec,self.geometry)

    def test_print_label_scale_enlarges_ids_and_values_together(self):
        self.spec['presentation']={'balloon_scale':2}
        self.spec['drawing']['balloons'][0].update(badge_xy=[100,60],value_xy=[360,60])
        root=ET.fromstring(icl.render_svg(self.spec,self.geometry));ns={'s':icl.SVG}
        texts=root.findall('.//s:g[@data-checks]/s:text',ns)
        self.assertEqual([t.get('font-size')for t in texts],['40','48'])
        self.assertEqual([t.text for t in texts],['L1','6.1 × 10 mm'])
        self.assertEqual(root.find('.//s:g[@data-checks]/s:rect',ns).get('height'),'100')
        self.spec['presentation']['balloon_scale']=0.4
        with self.assertRaisesRegex(ValueError,'balloon_scale'):
            icl.render_svg(self.spec,self.geometry)


if __name__=='__main__':unittest.main()
