"""The active historical loader must reject shared datasets before any cloud access."""
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'extraction/scripts'))
import source_history_pipeline as history

class HistoryGuard(unittest.TestCase):
    def test_shared_dev_and_prod_cannot_be_recreated(self):
        for project, dataset in [('vaca-muerta-pulse', d) for d in
                ['raw_cap4_dev', 'raw_cap4', 'other_candidate_dev']] + [('other-project', 'raw_cap4_candidate_dev')]:
            args = SimpleNamespace(project=project, dataset=dataset)
            with patch.object(history, 'validate_candidate') as validator:
                with self.assertRaisesRegex(ValueError, 'Writes restricted'):
                    history.load_stage(args)
                validator.assert_not_called()

    def test_only_reviewed_dedicated_candidate_reaches_client(self):
        cloud = ModuleType('google.cloud'); bq = ModuleType('google.cloud.bigquery')
        bq.Client = MagicMock(side_effect=RuntimeError('client-reached')); cloud.bigquery = bq
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); contract = root/'contract.json'; contract.write_text('{}')
            args = SimpleNamespace(project='vaca-muerta-pulse', dataset='raw_cap4_candidate_dev',
                                   contract=contract, candidate=root)
            with patch.dict(sys.modules, {'google.cloud': cloud, 'google.cloud.bigquery': bq}), \
                    patch.object(history, 'validate_candidate', return_value={'schema': {}}) as validator:
                with self.assertRaisesRegex(RuntimeError, 'client-reached'):
                    history.load_stage(args)
                validator.assert_called_once_with(root, {})
                bq.Client.assert_called_once_with(project='vaca-muerta-pulse', location='US')

if __name__ == '__main__': unittest.main()
