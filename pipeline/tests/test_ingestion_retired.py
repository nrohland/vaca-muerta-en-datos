"""Retired entrypoints must fail before network, scratch files, or warehouse writes."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]

class IngestionRetiredTests(unittest.TestCase):
    def test_batch_scripts_fail_without_touching_input(self):
        for path in ['extraction/scripts/source_history_pipeline.py','extraction/scripts/source_csv_pipeline.py',
                     'scripts/prepare_reference_prices.py','scripts/load_reference_prices.py']:
            with self.subTest(path=path):
                result=subprocess.run([sys.executable,str(ROOT/path)],capture_output=True,text=True,timeout=10)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('Batch ingestion retired',result.stderr)

    def test_old_cli_phases_and_stage_bypass_fail_before_creating_run_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp)/'must_not_exist'
            for phase in ['prepare','load','extract','all']:
                result=subprocess.run([sys.executable,str(ROOT/'pipeline/run_candidate.py'),phase,
                    '--run-dir',str(run)],capture_output=True,text=True,timeout=10)
                self.assertNotEqual(result.returncode,0)
                self.assertFalse(run.exists())

if __name__=='__main__':unittest.main()
