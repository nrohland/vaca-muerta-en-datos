"""Enforce least privilege and immutable dependencies for the security checks."""
from pathlib import Path
import re
import unittest
import yaml

ROOT=Path(__file__).resolve().parents[2]
class SecurityWorkflowTests(unittest.TestCase):
 def test_every_remote_action_is_pinned_and_checkout_does_not_persist_tokens(self):
  for path in (ROOT/'.github/workflows').glob('*.yml'):
   workflow=yaml.load(path.read_text(),Loader=yaml.BaseLoader)
   for job in workflow['jobs'].values():
    for step in job.get('steps',[]):
     action=step.get('uses','')
     if action and not action.startswith('./'):
      self.assertRegex(action,r'^[\w.-]+/[\w./-]+@[a-f0-9]{40}$',str(path))
     if action.startswith('actions/checkout@'):
      self.assertEqual(step['with']['persist-credentials'],'false',str(path))
 def test_security_checks_do_not_receive_cloud_identity_or_execute_pr_text(self):
  path=ROOT/'.github/workflows/security.yml';text=path.read_text()
  workflow=yaml.load(text,Loader=yaml.BaseLoader)
  self.assertEqual(workflow['permissions'],{'contents':'read'})
  for forbidden in ['pull_request_target','id-token','google-github-actions/auth','github.event.pull_request.title','github.event.pull_request.body']:
   self.assertNotIn(forbidden,text)
  self.assertNotRegex(text,r'\$\{\{[^}]*secrets\.')
  self.assertEqual(workflow['jobs']['codeql']['permissions'],{'contents':'read','security-events':'write'})
  for name in ['secrets','dependencies']:
   self.assertNotIn('security-events',workflow['jobs'][name].get('permissions',{}))
  self.assertIn('--redact=100',text);self.assertIn('sha256sum --check --status',text)
  self.assertNotIn('upload-artifact',text)
if __name__=='__main__':unittest.main()
