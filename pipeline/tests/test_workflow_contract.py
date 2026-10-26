"""Only Meltano may ingest; source readiness cannot be bypassed by a manual dispatch."""
from pathlib import Path
import unittest
import yaml

ROOT=Path(__file__).resolve().parents[2]

class WorkflowContract(unittest.TestCase):
    def setUp(self):
        self.path=ROOT/'.github/workflows/data-pipeline.yml'
        self.workflow=yaml.load(self.path.read_text(),Loader=yaml.BaseLoader)

    def test_default_is_offline_and_no_schedule_is_armed(self):
        self.assertEqual(self.workflow['on']['workflow_dispatch']['inputs']['mode']['default'],'verify')
        self.assertNotIn('schedule',self.workflow['on'])
        verify=self.workflow['jobs']['verify']
        self.assertNotIn('environment',verify)
        self.assertNotIn('id-token',verify.get('permissions',{}))
        self.assertFalse(any('auth@' in s.get('uses','') for s in verify['steps']))

    def test_ingestion_requires_main_and_both_readiness_flags(self):
        guard=self.workflow['jobs']['extract']['if']
        for clause in ["github.ref == 'refs/heads/main'","inputs.mode == 'ingest'",
            "vars.DATA_PIPELINE_ENABLED == 'true'","vars.SOURCE_CONNECTIVITY_VERIFIED == 'true'"]:
            self.assertIn(clause,guard)
        self.assertNotIn('||',guard)
        self.assertEqual(self.workflow['jobs']['extract']['environment'],'data-dev-extract')
        self.assertEqual(self.workflow['jobs']['extract']['permissions'],{'contents':'read','id-token':'write'})

    def test_no_legacy_load_or_implicit_transformation_publication(self):
        text=self.path.read_text()
        for forbidden in ['run_candidate.py','source_history_pipeline.py','source_csv_pipeline.py',
            'load_reference_prices.py','dbt build','upload-artifact','git push','deploy']:
            self.assertNotIn(forbidden,text)
        self.assertIn('meltano run candidate-history',text)
        self.assertNotIn('transform',self.workflow['jobs'])

    def test_dependencies_and_public_connectivity_precede_auth(self):
        steps=self.workflow['jobs']['extract']['steps']
        auth=next(i for i,s in enumerate(steps) if s.get('uses','').startswith('google-github-actions/auth@'))
        ready=next(i for i,s in enumerate(steps) if 'check_public_sources.py' in s.get('run',''))
        install=next(i for i,s in enumerate(steps) if 'meltano install' in s.get('run',''))
        run=next(i for i,s in enumerate(steps) if 'meltano run candidate-history' in s.get('run',''))
        self.assertLess(install,auth);self.assertLess(ready,auth);self.assertLess(auth,run)
        self.assertIn("report.get('origin_status') != 'reachable'",steps[ready]['run'])
        self.assertEqual(self.workflow['permissions'],{'contents':'read'})

    def test_pr_checks_have_no_cloud_identity_or_publication(self):
        path=ROOT/'.github/workflows/dbt-transform.yml';text=path.read_text()
        workflow=yaml.load(text,Loader=yaml.BaseLoader)
        self.assertEqual(workflow['permissions'],{'contents':'read'})
        self.assertIn('pull_request',workflow['on'])
        for forbidden in ('id-token','google-github-actions/auth','secrets.','deploy','git push'):
            self.assertNotIn(forbidden,text)
        self.assertIn('meltano invoke tap-eia-prices --discover',text)

if __name__=='__main__':unittest.main()
