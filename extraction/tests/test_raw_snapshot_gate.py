import copy
import importlib.util
from pathlib import Path
import unittest
from datetime import datetime,timezone
spec=importlib.util.spec_from_file_location('gate',Path(__file__).parents[1]/'scripts/check_raw_snapshot.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
class RawGate(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,10,12,tzinfo=timezone.utc)
  self.profile={'year_rows':663675,'total_table_rows':663675,'outside_year_rows':0,'invalid_year_rows':0,'month_rows':79576,'duplicate_keys':0,'invalid_periods':0,'invalid_volumes':0,'null_ingestion_rows':0,'null_keys':0,'oldest_loaded_at':'2026-10-09T19:14:00Z','loaded_at':'2026-10-09T19:15:00Z'}
  self.evidence={'resource_id':'official2026','year':2026,'source_sha256':'a'*64,'hash_scope':'official_csv_bytes','extracted_at':'2026-10-09T19:07:00Z','coverage_status':'reviewed_complete_snapshot','accepted_periods':['2026-08-01'],'year_rows':663675,'month_rows':{'2026-08-01':79576,'2026-09-01':4108}}
 def run_gate(self,month=8):return gate.validate_policy(self.profile,self.evidence,resource_id='official2026',year=2026,month=month,now=self.now)
 def test_exact_reloaded_snapshot_passes_without_publication(self):
  result=self.run_gate();self.assertEqual(result['status'],'pass');self.assertFalse(result['publication_approved'])
 def test_partial_month_fails_even_when_counts_exact(self):
  self.profile['month_rows']=4108;self.assertIn('required month has no reviewed complete coverage',self.run_gate(9)['errors'])
 def test_both_annual_and_month_counts_reconcile(self):
  for column in ('year_rows','month_rows'):
   with self.subTest(column=column):
    self.setUp();self.profile[column]-=1;self.assertEqual(self.run_gate()['status'],'fail')
 def test_stale_member_cannot_be_hidden_by_new_batch(self):
  self.profile['oldest_loaded_at']='2026-09-01T00:00:00Z';self.evidence['extracted_at']='2026-08-31T00:00:00Z'
  self.assertIn('snapshot ingestion older than 7 days',self.run_gate()['errors'])
 def test_duplicates_invalid_volumes_dates_and_null_ingestion_fail(self):
  for col in ('duplicate_keys','invalid_periods','invalid_volumes','null_ingestion_rows','null_keys'):
   with self.subTest(col=col):
    self.setUp();self.profile[col]=1;self.assertEqual(self.run_gate()['status'],'fail')
 def test_future_load_and_wrong_resource_fail(self):
  self.profile['loaded_at']='2026-10-13T00:00:00Z';self.assertIn('source/load chronology invalid',self.run_gate()['errors'])
  self.setUp();self.evidence['resource_id']='different';self.assertIn('source identity mismatch',self.run_gate()['errors'])
 def test_other_year_rows_fail_even_when_selected_year_and_month_reconcile(self):
  self.profile['total_table_rows']+=1;self.profile['outside_year_rows']=1
  result=self.run_gate()
  self.assertIn('raw contains rows outside requested year',result['errors'])
  self.assertEqual(self.profile['year_rows'],self.evidence['year_rows'])
  self.assertEqual(self.profile['month_rows'],self.evidence['month_rows']['2026-08-01'])
 def test_invalid_year_aggregation_fails_without_hiding_good_selected_counts(self):
  # Query aggregates null, malformed, fractional and future years into this bucket.
  self.profile['total_table_rows']+=1;self.profile['outside_year_rows']=1;self.profile['invalid_year_rows']=1
  self.assertIn('raw contains null malformed or invalid year',self.run_gate()['errors'])
 def test_table_count_alone_cannot_pass_with_missing_year_rows(self):
  self.profile['year_rows']-=1;self.profile['outside_year_rows']=1
  self.assertIn('raw table is not exclusively the requested year',self.run_gate()['errors'])
 def test_naive_timestamp_fails_closed(self):
  self.profile['loaded_at']='2026-10-09T19:15:00'
  with self.assertRaises(ValueError):self.run_gate()
if __name__=='__main__':unittest.main()
