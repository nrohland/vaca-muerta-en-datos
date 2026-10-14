import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from resource_preflight import assess,STORAGE_BUDGET,MONTHLY_QUERY_BUDGET
from report_dbt_performance import budget_check
class ResourceBudgetTests(unittest.TestCase):
    def test_billing_unknown_or_enabled_blocks(self):
        for value in [True,None,'false',0]:
            with self.assertRaises(ValueError):assess(value,[],[],monthly_complete=True)
    def test_no_implicit_zero_for_incomplete_month(self):
        r=assess(False,[],[],monthly_complete=False)
        self.assertFalse(r['monthly_inventory_complete']);self.assertTrue(r['warnings'])
    def test_storage_and_monthly_compute_operating_limits(self):
        with self.assertRaises(ValueError):assess(False,[{'logical_bytes':STORAGE_BUDGET+1}],[],monthly_complete=True)
        with self.assertRaises(ValueError):assess(False,[],[{'bytes_billed':MONTHLY_QUERY_BUDGET+1}],monthly_complete=True)
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
