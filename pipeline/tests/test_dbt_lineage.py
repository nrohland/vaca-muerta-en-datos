import sys
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from render_dbt_lineage import graph,svg

class DbtLineage(unittest.TestCase):
    def test_graph_excludes_tests_packages_and_connection_metadata(self):
        base=dict(package_name='vaca_muerta_pulse',database='private_database',config={'credentials':'never-export'})
        manifest={'nodes':{'model.vm.fact':{**base,'name':'fact','resource_type':'model'},
            'test.vm.fact':{**base,'name':'test','resource_type':'test'},
            'model.package.x':{**base,'package_name':'other','name':'x','resource_type':'model'}},
            'sources':{'source.vm.raw':{**base,'name':'raw','resource_type':'source'}},
            'parent_map':{'model.vm.fact':['source.vm.raw','model.package.x']}}
        result=graph(manifest);self.assertEqual(result['edges'],[('source.vm.raw','model.vm.fact')])
        image=svg(result);ET.fromstring(image)
        self.assertNotIn('private_database',image);self.assertNotIn('never-export',str(result));self.assertEqual(len(result['nodes']),2)
    def test_cycle_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Cyclic'):
            svg({'nodes':{'x':{'name':'x','resource_type':'model'}},'edges':[('x','x')]})

if __name__=='__main__':unittest.main()
