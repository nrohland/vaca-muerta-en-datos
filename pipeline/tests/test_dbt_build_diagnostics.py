import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dbt_build_diagnostics import await_budget,failure_report


class BuildDiagnosticsTests(unittest.TestCase):
    def test_over_budget_estimates_wait_and_accept_only_below_unchanged_limit(self):
        elapsed=[0];values=iter([120,110,90])
        def sleep(seconds):elapsed[0]+=seconds
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'readiness.json'
            report=await_budget(lambda:next(values),output,100,timeout=30,interval=15,clock=lambda:elapsed[0],sleep=sleep)
            self.assertEqual(json.loads(output.read_text()),report)
        self.assertEqual(report['status'],'pass')
        self.assertEqual([a['estimated_bytes'] for a in report['attempts']],[120,110,90])
        self.assertEqual(report['limit_bytes'],100)

    def test_persistent_overage_fails_without_indefinite_wait(self):
        elapsed=[0]
        def sleep(seconds):elapsed[0]+=seconds
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'readiness.json'
            with self.assertRaises(ValueError):
                await_budget(lambda:120,output,100,timeout=20,interval=15,clock=lambda:elapsed[0],sleep=sleep)
            report=json.loads(output.read_text())
        self.assertEqual(elapsed[0],20)
        self.assertEqual(report['failure'],'estimated_scan_exceeds_budget')
        self.assertEqual(report['status'],'fail')

    def test_missing_or_error_estimate_never_passes_or_exposes_details(self):
        def sensitive():raise RuntimeError('Bearer sensitive SQL with credentials')
        for estimate in (lambda:None,lambda:True,sensitive):
            with tempfile.TemporaryDirectory() as directory:
                output=Path(directory)/'readiness.json'
                with self.assertRaises(ValueError):await_budget(estimate,output,100)
                text=output.read_text()
                self.assertNotIn('Bearer',text);self.assertNotIn('credentials',text)
                self.assertEqual(json.loads(text)['failure'],'estimate_unavailable')

    def test_failure_report_keeps_budget_numbers_without_sql_or_exception_body(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)
            (target/'run_results.json').write_text(json.dumps({'args':{'secret':'sensitive'},'results':[
                {'unique_id':'model.vm.staging','status':'error','message':'Query exceeded limit for bytes billed: 1073741824. 1141899264 or higher required. SQL secret token'},
                {'unique_id':'test.vm.success','status':'pass'},
                {'unique_id':'test.vm.skip','status':'skipped','message':'secret token'}]}))
            report=failure_report(target,1)
        self.assertNotIn('secret',json.dumps(report))
        self.assertEqual(len(report['nodes']),2)
        self.assertEqual(report['nodes'][0]['required_bytes'],1141899264)
        self.assertEqual(report['status'],'fail')

    def test_no_results_does_not_claim_node_failure_or_success(self):
        with tempfile.TemporaryDirectory() as directory:
            report=failure_report(Path(directory),1)
        self.assertEqual(report['failure'],'dbt_results_unavailable')
        self.assertFalse(report['publication_approved'])
