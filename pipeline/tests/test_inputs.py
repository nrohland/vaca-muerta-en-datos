import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

module = Path(__file__).resolve().parents[1]/'validate_inputs.py'
spec = importlib.util.spec_from_file_location('inputs', module)
inputs = importlib.util.module_from_spec(spec); spec.loader.exec_module(inputs)

class Inputs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        path = self.root/'pipeline/contracts/source.json'; path.parent.mkdir(parents=True)
        self.evidence = {'resource_id': 'd774b5d7-0756-48fe-88f2-8729b57b22da', 'year': 2025,
            'hash_scope': 'ckan_metadata_counts', 'coverage_status': 'reviewed_complete_snapshot',
            'accepted_periods': ['2025-12-01'], 'month_rows': {'2025-12-01': 1},
            'year_rows': 12, 'source_sha256': 'a'*64}
        self.path = path; self.save()
        self.env = {'RESOURCE_ID': self.evidence['resource_id'], 'SOURCE_YEAR': '2025',
            'REQUIRED_MONTH': '12', 'REVIEWED_EVIDENCE': 'pipeline/contracts/source.json'}
    def save(self): self.path.write_text(json.dumps(self.evidence))
    def test_valid_configuration(self):
        self.assertEqual(inputs.validate(self.env, self.root), self.path.resolve())
    def test_outside_contract_and_symlink_are_rejected(self):
        for path in ['../../outside.json', '/tmp/source.json']:
            self.env['REVIEWED_EVIDENCE'] = path
            with self.assertRaises(ValueError): inputs.validate(self.env, self.root)
        outside = self.root/'outside.json'; outside.write_text(json.dumps(self.evidence))
        link = self.root/'pipeline/contracts/link.json'; link.symlink_to(outside)
        self.env['REVIEWED_EVIDENCE'] = 'pipeline/contracts/link.json'
        with self.assertRaises(ValueError): inputs.validate(self.env, self.root)
    def test_csv_evidence_and_oversized_source_are_rejected(self):
        for key, value in [('hash_scope', 'source_bytes'), ('year_rows', 2_000_001)]:
            original = self.evidence[key]; self.evidence[key] = value; self.save()
            with self.assertRaises(ValueError): inputs.validate(self.env, self.root)
            self.evidence[key] = original
    def test_unreviewed_month_and_injected_resource_are_rejected(self):
        self.env['REQUIRED_MONTH'] = '11'
        with self.assertRaises(ValueError): inputs.validate(self.env, self.root)
        self.env['REQUIRED_MONTH'] = '12'; self.env['RESOURCE_ID'] = '$(touch /tmp/test)'
        with self.assertRaises(ValueError): inputs.validate(self.env, self.root)
