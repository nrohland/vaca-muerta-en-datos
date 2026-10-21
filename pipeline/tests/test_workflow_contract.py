"""Security and sequencing contract for the disabled candidate workflow."""
from pathlib import Path
import unittest
import yaml

class WorkflowContract(unittest.TestCase):
    def test_manual_resource_check_skips_all_loads_and_transform(self):
        self.assertEqual(self.workflow['on']['workflow_dispatch']['inputs']['resource_check_only']['default'],'false')
        steps=self.workflow['jobs']['extract']['steps']
        for marker in ('run_candidate.py prepare ','run_candidate.py load '):
            step=next(s for s in steps if marker in s.get('run',''))
            self.assertEqual(step['if'],'${{ !inputs.resource_check_only }}')
        check=next(s for s in steps if 'pipeline/resource_preflight.py --output' in s.get('run',''))
        self.assertEqual(check['if'],'${{ inputs.resource_check_only }}')
        self.assertEqual(self.workflow['jobs']['transform']['if'],'${{ !inputs.resource_check_only }}')

    def setUp(self):
        path=Path(__file__).resolve().parents[2]/'.github/workflows/data-pipeline.yml'
        self.workflow=yaml.load(path.read_text(),Loader=yaml.BaseLoader)

    def test_main_opt_in_and_separate_identities_without_publication(self):
        jobs=self.workflow['jobs'];guard=jobs['extract']['if']
        self.assertIn("DATA_PIPELINE_ENABLED == 'true'",guard)
        self.assertIn("refs/heads/main",guard)
        self.assertEqual(jobs['transform']['needs'],'extract')
        self.assertEqual(self.workflow['permissions'],{'contents':'read'})
        accounts=[]
        for name in ('extract','transform'):
            self.assertEqual(jobs[name]['permissions']['contents'],'read')
            self.assertEqual(jobs[name]['permissions']['id-token'],'write')
            auth=[s for s in jobs[name]['steps'] if s.get('uses','').startswith('google-github-actions/auth@')]
            self.assertEqual(len(auth),1)
            self.assertNotIn('credentials_json',auth[0]['with'])
            accounts.append(auth[0]['with']['service_account'])
            for step in jobs[name]['steps']:
                if step.get('uses','').startswith('actions/upload-artifact@'):
                    self.assertTrue(step['with']['path'].endswith('/*.json') or step['with']['name']=='candidate-public-preparation')
                    self.assertNotIn('dashboard',step['with']['path'])
        self.assertNotEqual(*accounts)
        self.assertFalse(any('deploy' in s.get('uses','') for j in jobs.values() for s in j['steps']))

    def test_manual_main_run_does_not_enable_schedule_or_branch_access(self):
        guard=self.workflow['jobs']['extract']['if']
        for ref, event, enabled, expected in [
            ('refs/heads/main','workflow_dispatch','false',True),
            ('refs/heads/main','schedule','false',False),
            ('refs/heads/main','schedule','true',True),
            ('refs/heads/feat/dashboard-integrated','workflow_dispatch','true',False),
            ('refs/heads/feat/dashboard-integrated','workflow_dispatch','false',False)]:
            expression=guard.replace('github.ref',repr(ref)).replace('github.event_name',repr(event)).replace('vars.DATA_PIPELINE_ENABLED',repr(enabled)).replace('&&',' and ').replace('||',' or ')
            self.assertEqual(eval(expression,{'__builtins__':{}}),expected)

    def test_public_preparation_precedes_auth_and_frontend_follows_transform(self):
        extract=self.workflow['jobs']['extract']['steps']
        prep=next(i for i,s in enumerate(extract) if 'run_candidate.py prepare ' in s.get('run',''))
        auth=next(i for i,s in enumerate(extract) if s.get('uses','').startswith('google-github-actions/auth@'))
        load=next(i for i,s in enumerate(extract) if 'run_candidate.py load ' in s.get('run',''))
        self.assertLess(prep,auth);self.assertLess(auth,load)
        transform=self.workflow['jobs']['transform']['steps']
        build=next(i for i,s in enumerate(transform) if 'run_candidate.py transform --history' in s.get('run',''))
        frontend=next(i for i,s in enumerate(transform) if 'npm --prefix apps/web run build' in s.get('run',''))
        self.assertLess(build,frontend)
        self.assertIn('vm-transform/dashboard/release.json',transform[frontend]['run'])

    def test_pr_checks_have_no_cloud_identity_or_publication(self):
        path=Path(__file__).resolve().parents[2]/'.github/workflows/dbt-transform.yml'
        workflow=yaml.load(path.read_text(),Loader=yaml.BaseLoader)
        self.assertEqual(workflow['permissions'],{'contents':'read'})
        self.assertIn('pull_request',workflow['on'])
        steps=workflow['jobs']['validate']['steps']
        text=path.read_text()
        for forbidden in ('id-token','google-github-actions/auth','secrets.','deploy','git push'):
            self.assertNotIn(forbidden,text)
        self.assertFalse(any('dbt build' in step.get('run','') for step in steps))
        audit=workflow['jobs']['architecture']['steps']
        self.assertTrue(any('profiles-audit.yml.example' in step.get('run','') and '--select package:dbt_project_evaluator' in step.get('run','') for step in audit))
        self.assertTrue(any('dbt parse' in step.get('run','') for step in steps))
        self.assertTrue(any('check_snapshot.mjs' in step.get('run','') for step in steps))

if __name__=='__main__':unittest.main()
