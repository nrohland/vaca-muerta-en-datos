import importlib.util
from pathlib import Path
import unittest
s=importlib.util.spec_from_file_location('ckan',Path(__file__).parents[1]/'scripts/check_ckan_snapshot.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class CkanGate(unittest.TestCase):
 def setUp(self):
  self.before={'resource_id':'id','year':2026,'month':8,'year_rows':100,'month_rows':{'2026-08-01':10},'resource_total':100,'schema':[{'id':'anio','type':'numeric'}],'source_last_modified':'unknown','hash_scope':'ckan_metadata_counts','extracted_at':'2026-10-12T00:00:00Z'}
  self.before['source_sha256']=m.fingerprint(self.before)
  self.evidence={**self.before,'coverage_status':'reviewed_complete_snapshot','accepted_periods':['2026-08-01']}
 def test_timestamp_change_is_not_source_revision(self):
  after={**self.before,'extracted_at':'2026-10-12T01:00:00Z'}
  self.assertEqual(m.fingerprint(after),self.before['source_sha256']);self.assertEqual(m.compare(self.before,after,self.evidence),[])
 def test_source_revision_during_extract_fails(self):
  after={**self.before,'source_last_modified':'changed'};after['source_sha256']=m.fingerprint(after)
  self.assertIn('source changed during extraction',m.compare(self.before,after,self.evidence))
 def test_metadata_fingerprint_is_not_csv_checksum(self):
  self.evidence['hash_scope']='official_csv_bytes';self.assertIn('reviewed evidence differs: hash_scope',m.compare(self.before,self.before,self.evidence))
 def test_partial_month_no_acceptance_fails(self):
  self.evidence['accepted_periods']=[];self.assertIn('month not technically accepted',m.compare(self.before,self.before,self.evidence))
 def test_schema_revision_changes_fingerprint(self):
  self.assertNotEqual(m.fingerprint({**self.before,'schema':[]}),self.before['source_sha256'])
if __name__=='__main__':unittest.main()
