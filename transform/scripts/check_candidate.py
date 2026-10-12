#!/usr/bin/env python3
"""Read-only candidate gate. Technical validation never grants publication approval."""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timestamp requires an explicit timezone')
    return parsed.astimezone(timezone.utc)


def period_index(value):
    parsed = datetime.strptime(value, '%Y-%m-%d')
    if parsed.day != 1:
        raise ValueError('period must be first calendar day')
    return parsed.year * 12 + parsed.month


def validate(release, manifest, *, now, extraction_warn_days=40, extraction_error_days=70,
             period_warn_months=2, period_error_months=3, ingestion_max_hours=24):
    errors, warnings = [], []
    def require(condition, message):
        if not condition:
            errors.append(message)
    source = manifest['source']
    periods = source['accepted_periods']
    indexes = sorted(period_index(p) for p in periods)
    require(bool(indexes), 'no technically accepted periods')
    require(len(set(periods)) == len(periods), 'duplicate accepted periods')
    if indexes:
        require(indexes == list(range(indexes[0], indexes[-1] + 1)), 'accepted history has calendar gaps')
        require(period_index(source['approved_period']) == indexes[-1], 'cutoff differs from accepted history')
    resources = source['resources']
    require(bool(resources), 'no source resources')
    for resource in resources:
        extracted = timestamp(resource['extracted_at'])
        age = (now - extracted).total_seconds() / 86400
        require(age >= 0, 'extraction timestamp is in future')
        if age > extraction_error_days:
            errors.append('source extraction exceeds error freshness')
        elif age > extraction_warn_days:
            warnings.append('source extraction exceeds warning freshness')
    ingested = timestamp(source['ingested_at'])
    generated = timestamp(manifest['generated_at'])
    require(ingested <= generated <= now, 'ingestion/generation chronology invalid')
    require((generated-ingested).total_seconds() <= ingestion_max_hours*3600,
            'release generation delayed after ingestion')
    if resources:
        require(max(timestamp(r['extracted_at']) for r in resources) <= ingested,
                'ingestion predates latest extraction')
    if indexes:
        lag = now.year * 12 + now.month - indexes[-1]
        if lag > period_error_months:
            errors.append('accepted economic period exceeds error lag')
        elif lag > period_warn_months:
            warnings.append('accepted economic period exceeds warning lag')
    totals = {}
    for row in release['production']:
        key = (row['fluid'], row['periodo'])
        require(key not in totals, 'duplicate total grain')
        totals[key] = row
        require(row['fluid'] in ('oil', 'gas') and row['periodo'] in periods, 'unaccepted total grain')
        require(row['coverage'] == 1 and row['is_complete'] is True and
                row['acceptance_basis'] == 'approved_complete_snapshot', 'total not technically complete')
        require(isinstance(row['volume'], (int,float)) and math.isfinite(row['volume']) and row['volume'] >= 0,
                'invalid total volume')
    require(set(totals) == {(fluid, period) for period in periods for fluid in ('oil','gas')},
            'accepted total month/fluid missing')
    entities, sums = set(), {}
    for row in release['entities']:
        key = (row['fluid'], row['periodo'], row['dimension'], row['entity_id'])
        require(key not in entities, 'duplicate entity grain')
        entities.add(key)
        require((row['fluid'],row['periodo']) in totals and row['dimension'] in ('company','area'),
                'entity outside accepted total grain')
        require(isinstance(row['volume'], (int,float)) and math.isfinite(row['volume']) and row['volume'] >= 0,
                'invalid entity volume')
        group = key[:3]
        sums[group] = sums.get(group,0) + row['volume']
    for key, row in totals.items():
        for dimension in ('company','area'):
            require(key+(dimension,) in sums, 'complete entity ranking missing')
            require(math.isclose(sums.get(key+(dimension,),0), row['volume'], rel_tol=1e-10, abs_tol=1e-7),
                    'entity volume does not reconcile total')
    return {'status': 'fail' if errors else 'warn' if warnings else 'pass',
            'errors': sorted(set(errors)), 'warnings': sorted(set(warnings)),
            'publication_approved': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--now', help='Explicit timezone ISO timestamp; default current UTC')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    content = args.release.read_bytes()
    if hashlib.sha256(content).hexdigest() != manifest['data_sha256']:
        print(json.dumps({'status':'fail','errors':['release hash differs from manifest'],'publication_approved':False}))
        return 1
    try:
        result = validate(json.loads(content),manifest,now=timestamp(args.now) if args.now else datetime.now(timezone.utc))
    except (KeyError, ValueError, TypeError) as exc:
        result = {'status':'fail','errors':['invalid gate input: '+str(exc)],'publication_approved':False}
    print(json.dumps(result))
    return int(result['status']=='fail')

if __name__ == '__main__':
    raise SystemExit(main())
