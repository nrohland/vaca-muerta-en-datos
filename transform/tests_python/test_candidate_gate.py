import importlib.util
from pathlib import Path
import unittest
from datetime import datetime,timezone
s=importlib.util.spec_from_file_location('candidate',Path(__file__).parents[1]/'scripts/check_candidate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class CandidateGate(unittest.TestCase):
 def setUp(self):
  period='2026-08-01'
  self.release={'production':[{'fluid':f,'periodo':period,'volume':10,'coverage':1,'is_complete':True,'acceptance_basis':'approved_complete_snapshot'} for f in ('oil','gas')],'entities':[{'fluid':f,'periodo':period,'dimension':d,'entity_id':'a','volume':10} for f in ('oil','gas') for d in ('company','area')]}
  self.manifest={'generated_at':'2026-10-09T19:18:00Z','source':{'accepted_periods':[period],'approved_period':period,'ingested_at':'2026-10-09T19:14:00Z','resources':[{'extracted_at':'2026-10-09T19:07:00Z'}]}}
  self.now=datetime(2026,10,12,tzinfo=timezone.utc)
 def gate(self):return m.validate(self.release,self.manifest,now=self.now)
 def test_candidate_pass_never_grants_approval(self):self.assertEqual(self.gate()['status'],'pass');self.assertFalse(self.gate()['publication_approved'])
 def test_unreconciled_ranking_fails(self):self.release['entities'][0]['volume']=9;self.assertIn('entity volume does not reconcile total',self.gate()['errors'])
 def test_unaccepted_partial_and_duplicate_fail(self):
  self.release['production'].append({**self.release['production'][0],'periodo':'2026-09-01'});self.assertEqual(self.gate()['status'],'fail')
  self.release['entities'].append(self.release['entities'][0]);self.assertIn('duplicate entity grain',self.gate()['errors'])
if __name__=='__main__':unittest.main()
