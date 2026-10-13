import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from report_dbt_performance import summarize

class PerformanceReportTests(unittest.TestCase):
    def test_absent_metrics_are_null_and_excluded_not_zero_measurements(self):
        value={'metadata':{'invocation_id':'a'},'results':[
          {'unique_id':'model.x.a','status':'success','execution_time':2,'adapter_response':{'bytes_processed':100,'bytes_billed':200,'slot_ms':500}},
          {'unique_id':'unit_test.x.b','status':'pass','execution_time':3,'adapter_response':{}}]}
        r=summarize(value)
        self.assertIsNone(r['nodes'][1]['bytes_processed'])
        self.assertEqual(r['metrics_available']['bytes_processed'],1)
        self.assertEqual(r['totals']['bytes_processed'],100)
        self.assertEqual(r['totals']['bytes_billed'],200)
        self.assertEqual(r['models'][0]['resource_type'],'model')
    def test_wall_time_is_span_not_sum_of_parallel_node_times(self):
        rs=[{'unique_id':'model.x.'+name,'status':'success','execution_time':4,'timing':[{'started_at':'2026-10-13T10:00:00Z','completed_at':'2026-10-13T10:00:04Z'}]} for name in ['a','b']]
        r=summarize({'metadata':{'invocation_id':'a'},'results':rs})
        self.assertEqual(r['wall_seconds'],4)
        self.assertEqual(sum(n['seconds'] for n in r['nodes']),8)
