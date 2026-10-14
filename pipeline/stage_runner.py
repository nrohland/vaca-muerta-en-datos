"""Sequential candidate stages with fail-closed gates and durable run evidence.

No shell, environment dump, credential capture, publishing or retry of writes.
Each run gets a new directory; gate reports must belong to that run.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Callable
import os
import re
import signal


@dataclass(frozen=True)
class Stage:
    name: str
    argv: tuple[str, ...]
    cwd: Path
    timeout_seconds: int
    environment: dict[str, str] = field(default_factory=dict)
    gate_report: Path | None = None


def now():
    return datetime.now(timezone.utc).isoformat()


def write_report(path, report):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, indent=2))
    temporary.replace(path)


def execute_owned_process(argv, *, cwd, env, stdout, stderr, timeout, check=False):
    # Singer/dbt may spawn children. A timeout must stop the whole owned group
    # before allowing a later candidate run to touch the same tables.
    process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
                               start_new_session=True)
    try:
        return subprocess.CompletedProcess(argv, process.wait(timeout=timeout))
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)
        except ProcessLookupError:
            pass
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        raise


def run(stages: list[Stage], run_directory: Path, execute: Callable = execute_owned_process):
    names = [stage.name for stage in stages]
    if len(set(names)) != len(names) or any(not re.fullmatch('[a-z][a-z0-9_-]{0,63}', name) for name in names):
        raise ValueError('Stage names must be unique safe log names')
    run_directory.mkdir(parents=True, exist_ok=False)
    report_path = run_directory/'run.json'
    report = {'started_at': now(), 'status': 'running', 'publication_approved': False,
              'stages': []}
    write_report(report_path, report)
    for stage in stages:
        result = {'name': stage.name, 'started_at': now(), 'status': 'running'}
        report['stages'].append(result)
        write_report(report_path, report)
        print(json.dumps({'stage':stage.name,'status':'started'}),flush=True)
        failure = None
        try:
            if stage.gate_report:
                # A previous run must never satisfy this run's gate.
                if stage.gate_report.exists():
                    raise ValueError('Gate report already exists; refusing stale evidence')
                if not stage.gate_report.resolve().is_relative_to(run_directory.resolve()):
                    raise ValueError('Gate evidence must belong to this run directory')
            with (run_directory/f'{stage.name}.log').open('w') as log:
                process = execute(list(stage.argv), cwd=stage.cwd,
                                  env={**os.environ, **stage.environment},
                                  stdout=log, stderr=subprocess.STDOUT,
                                  timeout=stage.timeout_seconds, check=False)
            result['returncode'] = process.returncode
            if process.returncode != 0:
                failure = 'command_failed'
            elif stage.gate_report:
                gate = json.loads(stage.gate_report.read_text())
                if gate.get('status') != 'pass' or gate.get('publication_approved') is not False:
                    failure = 'gate_rejected'
        except subprocess.TimeoutExpired:
            failure = 'timeout'
        except (OSError, ValueError, TypeError):
            failure = 'invalid_or_missing_evidence'
        result['finished_at'] = now()
        result['status'] = 'failed' if failure else 'passed'
        print(json.dumps({'stage':stage.name,'status':result['status'],'failure':failure}),flush=True)
        if failure:
            result['failure'] = failure
            report['status'] = 'failed'
            report['finished_at'] = now()
            write_report(report_path, report)
            return report
        write_report(report_path, report)
    report['status'] = 'passed'
    report['finished_at'] = now()
    write_report(report_path, report)
    return report
