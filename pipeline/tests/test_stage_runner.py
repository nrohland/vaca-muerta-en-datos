import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

path = Path(__file__).resolve().parents[1]/'stage_runner.py'
spec = importlib.util.spec_from_file_location('stage_runner', path)
runner = importlib.util.module_from_spec(spec); sys.modules[spec.name] = runner
spec.loader.exec_module(runner)


class StageRunner(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.run = self.root/'new-run'
    def stage(self, name, gate=None):
        return runner.Stage(name, ('python', name), self.root, 10, gate_report=gate)
    def test_failed_extract_never_invokes_transform(self):
        calls = []
        def execute(argv, **kwargs):
            calls.append(argv); return SimpleNamespace(returncode=1)
        report = runner.run([self.stage('extract'), self.stage('transform')], self.run, execute)
        self.assertEqual(len(calls), 1); self.assertEqual(report['status'], 'failed')
        self.assertFalse(report['publication_approved'])
    def test_exit_zero_with_rejected_gate_never_invokes_transform(self):
        gate = self.run/'raw-gate.json'; calls = []
        def execute(argv, **kwargs):
            calls.append(argv); gate.write_text(json.dumps({'status':'fail', 'publication_approved':False}))
            return SimpleNamespace(returncode=0)
        report = runner.run([self.stage('raw-check', gate), self.stage('transform')], self.run, execute)
        self.assertEqual(len(calls), 1); self.assertEqual(report['stages'][0]['failure'], 'gate_rejected')
    def test_passed_gate_runs_transform_and_records_no_approval(self):
        gate = self.run/'raw-gate.json'; calls = []
        def execute(argv, **kwargs):
            calls.append(argv)
            if argv[-1]=='raw-check': gate.write_text(json.dumps({'status':'pass', 'publication_approved':False}))
            return SimpleNamespace(returncode=0)
        report = runner.run([self.stage('raw-check', gate), self.stage('transform')], self.run, execute)
        self.assertEqual(len(calls), 2); self.assertEqual(report['status'], 'passed')
        self.assertFalse(report['publication_approved'])
    def test_timeout_and_missing_evidence_stop_the_run(self):
        for name, execute in [('timeout', lambda *a, **k: (_ for _ in ()).throw(subprocess.TimeoutExpired(a[0],10))),
                              ('missing', lambda *a, **k: SimpleNamespace(returncode=0))]:
            directory = self.root/name; gate = directory/'gate.json'
            report = runner.run([self.stage('raw-check', gate)], directory, execute)
            self.assertEqual(report['status'], 'failed')
    def test_reusing_a_run_directory_is_rejected(self):
        self.run.mkdir()
        with self.assertRaises(FileExistsError): runner.run([], self.run)
