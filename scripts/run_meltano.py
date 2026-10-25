#!/usr/bin/env python3
"""Meltano adapter for the reviewed candidate CLI. No deployment or promotion."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]


def candidate_commands(phase, run_id, run_root, source_inbound=None):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', run_id):
        raise ValueError('VM_RUN_ID must be a safe identifier of 1-80 characters')
    base = Path(run_root).resolve() / run_id
    common = [sys.executable, str(REPO/'pipeline/run_candidate.py')]
    scratch = ['--scratch-dir', str(base/'scratch')]
    phases = ['prepare', 'load', 'transform'] if phase == 'all' else [phase]
    result = []
    for step in phases:
        cmd = common + [step, '--history', '--run-dir', str(base/step)]
        if step in ('prepare', 'load'):
            cmd += scratch
        if step == 'prepare' and source_inbound:
            cmd += ['--source-inbound', str(Path(source_inbound).resolve())]
        if step == 'load':
            cmd += ['--prepared-artifact', str(base/'prepare')]
        if step == 'transform':
            cmd += ['--extract-artifact', str(base/'load')]
        result.append(cmd)
    return result


@contextmanager
def pipeline_lock(run_root):
    # One host-wide lock also prevents different run IDs writing candidate tables.
    run_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (run_root/'.pipeline.lock').open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another candidate pipeline is running on this host') from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare', 'load', 'transform', 'all'])
    parser.add_argument('--plan', action='store_true', help='Print commands; no downloads or cloud calls')
    args = parser.parse_args()
    run_id = os.environ.get('VM_RUN_ID')
    if not run_id and args.phase != 'all':
        parser.error('VM_RUN_ID is required for separate phases; reuse it across prepare/load/transform')
    run_id = run_id or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run_root = Path(os.environ.get('VM_RUN_ROOT', str(REPO/'.local/runs'))).resolve()
    commands = candidate_commands(args.phase, run_id, run_root, os.environ.get('VM_SOURCE_INBOUND'))
    if args.plan:
        print(json.dumps({'run_id': run_id, 'commands': commands, 'billing_changes': False,
                          'publication_approved': False}, indent=2))
        return 0
    # This adapter never enables billing. Existing CLI preflight verifies it is disabled.
    with pipeline_lock(run_root):
        for command in commands:
            subprocess.run(command, cwd=REPO, check=True)
    print(json.dumps({'status': 'passed', 'run_id': run_id, 'publication_approved': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
