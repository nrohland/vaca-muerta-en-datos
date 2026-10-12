"""Exercise the command's guard before it can construct a warehouse client."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import MagicMock, patch

class HistoryGuard(unittest.TestCase):
    def command(self, dataset):
        google = ModuleType('google'); cloud = ModuleType('google.cloud')
        exceptions = ModuleType('google.api_core.exceptions')
        exceptions.Forbidden = type('Forbidden', (Exception,), {})
        exceptions.NotFound = type('NotFound', (Exception,), {})
        bq = ModuleType('google.cloud.bigquery'); bq.Client = MagicMock(side_effect=RuntimeError('client-reached'))
        cloud.bigquery = bq; google.cloud = cloud
        modules = {'google': google, 'google.cloud': cloud, 'google.cloud.bigquery': bq,
                   'google.api_core': ModuleType('google.api_core'), 'google.api_core.exceptions': exceptions}
        path = Path(__file__).resolve().parents[2]/'extraction/scripts/prepare_year_load.py'
        spec = importlib.util.spec_from_file_location('prepare', path)
        script = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, modules), patch.object(sys, 'argv', ['prepare', '--dataset', dataset, '--recreate']):
            spec.loader.exec_module(script)
            try: script.main()
            except (RuntimeError, SystemExit) as error: return error, bq.Client
        raise AssertionError('Expected command to stop without warehouse writes')
    def test_shared_dev_and_prod_cannot_be_recreated(self):
        for dataset in ['raw_cap4_dev', 'raw_cap4', 'other_candidate_dev']:
            error, client = self.command(dataset)
            self.assertIsInstance(error, SystemExit); self.assertEqual(error.code, 2)
            client.assert_not_called()
    def test_only_dedicated_candidate_reaches_client(self):
        error, client = self.command('raw_cap4_candidate_dev')
        self.assertEqual(str(error), 'client-reached'); client.assert_called_once()
