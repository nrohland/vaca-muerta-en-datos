import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('meltano_adapter', ROOT/'scripts/run_meltano.py')
adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)


class MeltanoAdapterTests(unittest.TestCase):
    def test_all_reuses_scratch_and_binds_artifacts(self):
        cmds=adapter.candidate_commands('all','test-run',Path('/tmp/vm-runs'))
        self.assertEqual([cmd[2] for cmd in cmds],['prepare','load','transform'])
        self.assertIn(str(Path('/tmp/vm-runs/test-run/prepare').resolve()),cmds[1])
        self.assertIn(str(Path('/tmp/vm-runs/test-run/load').resolve()),cmds[2])
        self.assertIn('--history',cmds[2])
        self.assertNotIn('--source-inbound',cmds[2])

    def test_unsafe_run_id_rejected_before_execution(self):
        for run_id in ['../escape','/absolute','.','', 'a/b']:
            with self.subTest(run_id=run_id),self.assertRaises(ValueError):
                adapter.candidate_commands('all',run_id,Path('/tmp'))

    def test_lock_prevents_overlapping_warehouse_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            with adapter.pipeline_lock(Path(tmp)):
                with self.assertRaisesRegex(RuntimeError,'Another candidate'):
                    with adapter.pipeline_lock(Path(tmp)):self.fail('second lock admitted')

    def test_plan_neither_creates_run_directory_nor_invokes_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_root=Path(tmp)/'uncreated'
            result=subprocess.run([sys.executable,str(ROOT/'scripts/run_meltano.py'),'all','--plan'],
                env={**os.environ,'VM_RUN_ROOT':str(run_root),'VM_RUN_ID':'offline-check'},capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('"billing_changes": false',result.stdout)
            self.assertFalse(run_root.exists())

    def test_first_failure_stops_following_phases_and_releases_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ,{'VM_RUN_ROOT':tmp,'VM_RUN_ID':'failure'}), patch.object(sys,'argv',['adapter','all']), \
                 patch.object(adapter.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['prepare'])) as execute:
                with self.assertRaises(subprocess.CalledProcessError):adapter.main()
            self.assertEqual(execute.call_count,1)
            with adapter.pipeline_lock(Path(tmp)):pass
