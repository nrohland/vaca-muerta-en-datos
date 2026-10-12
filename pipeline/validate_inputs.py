"""Validate configuration before cloud auth/load. Input strings never become code."""
import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

def validate(env, root):
    resource = env.get('RESOURCE_ID', '')
    if not re.fullmatch(r'[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}', resource):
        raise ValueError('Reviewed resource UUID required')
    year, month = int(env.get('SOURCE_YEAR', '')), int(env.get('REQUIRED_MONTH', ''))
    now = datetime.now(timezone.utc)
    if not 1900 <= year <= now.year or not 1 <= month <= 12 or (year, month) > (now.year, now.month):
        raise ValueError('Invalid or future requested period')
    directory = (root/'pipeline/contracts').resolve()
    supplied = Path(env.get('REVIEWED_EVIDENCE', ''))
    if supplied.is_absolute(): raise ValueError('Evidence must be repository-relative')
    evidence_path = (root/supplied).resolve()
    if not evidence_path.is_relative_to(directory) or evidence_path.suffix != '.json':
        raise ValueError('Evidence must be a JSON under pipeline/contracts')
    evidence = json.loads(evidence_path.read_text())
    period = f'{year:04d}-{month:02d}-01'
    if evidence.get('resource_id') != resource or evidence.get('year') != year:
        raise ValueError('Reviewed source identity differs')
    if evidence.get('hash_scope') != 'ckan_metadata_counts' or evidence.get('coverage_status') != 'reviewed_complete_snapshot':
        raise ValueError('Reviewed CKAN coverage required; CSV evidence cannot substitute')
    if period not in evidence.get('accepted_periods', []) or evidence.get('month_rows', {}).get(period, 0) <= 0:
        raise ValueError('Requested month has no reviewed complete coverage')
    if not 0 < evidence.get('year_rows', 0) <= 2_000_000:
        raise ValueError('Annual source outside reviewed candidate size budget')
    if not re.fullmatch('[a-f0-9]{64}', evidence.get('source_sha256', '')):
        raise ValueError('Source metadata fingerprint required')
    return evidence_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--vars-output', type=Path, required=True)
    args = parser.parse_args()
    validate(os.environ, Path.cwd())
    args.vars_output.parent.mkdir(parents=True, exist_ok=True)
    period = f"{int(os.environ['SOURCE_YEAR']):04d}-{int(os.environ['REQUIRED_MONTH']):02d}-01"
    args.vars_output.write_text(json.dumps({'candidate_period': period}))
    print('Candidate configuration valid; publication_approved=false')
