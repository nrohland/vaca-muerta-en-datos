"""Retirement blocks every legacy BigQuery write, including a formerly valid candidate."""
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'extraction/scripts'))
import source_history_pipeline as history

class HistoryGuard(unittest.TestCase):
    def test_no_destination_can_reach_legacy_payload_validation_or_cloud(self):
        for project,dataset in [('vaca-muerta-pulse',d) for d in
            ['raw_cap4_dev','raw_cap4','raw_cap4_candidate_dev']] + [('other','raw_cap4_candidate_dev')]:
            with self.subTest(project=project,dataset=dataset),patch.object(history,'validate_candidate') as validator:
                with self.assertRaisesRegex(ValueError,'Batch load retired'):
                    history.load_stage(SimpleNamespace(project=project,dataset=dataset))
                validator.assert_not_called()

if __name__=='__main__':unittest.main()
