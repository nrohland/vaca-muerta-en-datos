import sys
from pathlib import Path
import unittest
import tempfile
import json
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from resource_preflight import assess,checked,run_check,global_jobs_visible,PreflightFailure,STORAGE_BUDGET,MONTHLY_QUERY_BUDGET
from report_dbt_performance import budget_check
class ResourceBudgetTests(unittest.TestCase):
    def test_global_usage_requires_explicit_existing_permission(self):
        session=Mock()
        for ok,permissions,expected in [(True,[],False),(False,['bigquery.jobs.listAll'],False),(True,['bigquery.jobs.list'],False),(True,['bigquery.jobs.listAll'],True)]:
            session.post.return_value.ok=ok
            session.post.return_value.json.return_value={'permissions':permissions}
            self.assertEqual(global_jobs_visible(session),expected)
        session.post.side_effect=RuntimeError('sensitive request details')
        self.assertFalse(global_jobs_visible(session))

    def test_failed_inspection_persists_safe_diagnostic_and_exits_failed(self):
        def denied():
            raise PreflightFailure('billing-verification',http_status=403,
                                   api_status='PERMISSION_DENIED',api_reason='SERVICE_DISABLED')
        with tempfile.TemporaryDirectory() as directory,patch('builtins.print'):
            output=Path(directory)/'new'/'resource-preflight.json'
            self.assertEqual(run_check(output,denied),1)
            report=json.loads(output.read_text())
        self.assertEqual(report['status'],'fail')
        self.assertFalse(report['publication_approved'])
        self.assertEqual(report['failure'],{'phase':'billing-verification','http_status':403,
            'api_status':'PERMISSION_DENIED','api_reason':'SERVICE_DISABLED'})

    def test_exception_details_never_reach_report_and_never_pass(self):
        def secret():raise RuntimeError('Bearer sensitive-token path/to/credential.json')
        for inspector in (secret,lambda:checked('table-inventory',secret)):
            with tempfile.TemporaryDirectory() as directory,patch('builtins.print'):
                output=Path(directory)/'resource-preflight.json'
                self.assertEqual(run_check(output,inspector),1)
                text=output.read_text()
                self.assertNotIn('sensitive-token',text)
                self.assertNotIn('credential.json',text)
                self.assertEqual(json.loads(text)['status'],'fail')

    def test_successful_inspection_keeps_report(self):
        expected=assess(False,[],[],monthly_complete=False)
        with tempfile.TemporaryDirectory() as directory,patch('builtins.print'):
            output=Path(directory)/'resource-preflight.json'
            self.assertEqual(run_check(output,lambda:expected),0)
            self.assertEqual(json.loads(output.read_text()),expected)

    def test_billing_unknown_or_enabled_blocks(self):
        for value in [True,None,'false',0]:
            with self.assertRaises(ValueError):assess(value,[],[],monthly_complete=True)
    def test_no_implicit_zero_for_incomplete_month(self):
        r=assess(False,[],[],monthly_complete=False)
        self.assertFalse(r['monthly_inventory_complete']);self.assertTrue(r['warnings']);self.assertIsNone(r['query_bytes_billed'])
    def test_storage_and_monthly_compute_operating_limits(self):
        with self.assertRaises(ValueError):assess(False,[{'logical_bytes':STORAGE_BUDGET+1}],[],monthly_complete=True)
        with self.assertRaises(ValueError):assess(False,[],[{'bytes_billed':MONTHLY_QUERY_BUDGET+1}],monthly_complete=True)
        with self.assertRaises(ValueError):assess(False,[],[{'bytes_billed':MONTHLY_QUERY_BUDGET+1}],monthly_complete=False)
    def test_script_parents_are_not_double_counted(self):
        r=assess(False,[],[{'bytes_billed':10,'statement_type':'SCRIPT'},{'bytes_billed':10,'statement_type':'SELECT'}],monthly_complete=True)
        self.assertEqual(r['query_bytes_billed'],10)
    def test_dbt_metrics_required_and_overage_blocks(self):
        policy={'dbt_bytes_billed':100,'query_bytes_billed':90,'wall_seconds_warning':300}
        for value in [None,101]:
            r={'nodes':[{'resource_type':'model','bytes_billed':value}],'totals':{'bytes_billed':value or 0},'wall_seconds':1}
            with self.assertRaises(ValueError):budget_check(r,policy)
        r={'nodes':[{'resource_type':'model','bytes_billed':50},{'resource_type':'seed','bytes_billed':None}],'totals':{'bytes_billed':50},'wall_seconds':1}
        self.assertEqual(budget_check(r,policy)['status'],'pass')
