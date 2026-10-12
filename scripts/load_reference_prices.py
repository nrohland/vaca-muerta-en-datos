"""Load reviewed immutable price snapshot into the isolated candidate table.

Explicit --apply required; no IAM changes, keys, production or dev writes.
"""
import argparse
import hashlib
import json
import math
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from import_brent import URL

TABLE = 'vaca-muerta-pulse.raw_cap4_candidate_dev.monthly_reference_price'


def validate(payload, manifest):
    if hashlib.sha256(payload).hexdigest() != manifest['rows_sha256']:
        raise ValueError('Rows checksum mismatch')
    observed = datetime.fromisoformat(manifest['retrieved_at'])
    if observed.tzinfo is None or observed > datetime.now(timezone.utc) + timedelta(minutes=5) or observed < datetime.now(timezone.utc) - timedelta(days=7):
        raise ValueError('Source retrieval is future or stale')
    rows = [json.loads(line) for line in payload.splitlines()]
    if len(rows) != manifest['row_count'] or not rows:
        raise ValueError('Row count mismatch')
    months = set()
    for r in rows:
        if r['product'] != 'oil' or r['benchmark'] != 'EIA_BRENT_MONTHLY':
            raise ValueError('Unreviewed benchmark')
        period = date.fromisoformat(r['periodo'])
        if period.day != 1 or r['periodo'] in months or r['periodo'] > manifest['cutoff']:
            raise ValueError('Invalid period or duplicate')
        months.add(r['periodo'])
        if r['currency'] != 'USD' or r['price_unit'] != 'bbl' or r['source_url'] != URL:
            raise ValueError('Invalid reference units or URL')
        if isinstance(r['price'], bool) or not isinstance(r['price'], (int, float)) or not math.isfinite(r['price']) or r['price'] <= 0:
            raise ValueError('Invalid price')
        if r['source_sha256'] != manifest['response_sha256'] or r['snapshot_id'] != r['source_sha256'] or len(r['source_sha256']) != 64:
            raise ValueError('Snapshot hash mismatch')
        if r['accepted_cutoff'] != manifest['cutoff'] or r['retrieved_at'] != manifest['retrieved_at'] or r['source_updated_at'] != manifest['source_updated_at']:
            raise ValueError('Snapshot metadata mismatch')
        if datetime.fromisoformat(r['retrieved_at']).tzinfo is None or date.fromisoformat(r['source_updated_at']) > datetime.fromisoformat(r['retrieved_at']).date():
            raise ValueError('Invalid source timestamp')
        if r['energy_basis'] is not None:
            raise ValueError('Unreviewed energy basis')
    if manifest['cutoff'] not in months:
        raise ValueError('Required cutoff missing')
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--rows', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    payload = a.rows.read_bytes()
    manifest = json.loads(a.manifest.read_text())
    rows = validate(payload, manifest)
    if not a.apply:
        print(json.dumps({'table': TABLE, 'rows': len(rows), 'apply': False}))
    else:
        from google.cloud import bigquery
        fields = [('product', 'STRING'), ('periodo', 'DATE'), ('benchmark', 'STRING'), ('price', 'FLOAT64'),
                  ('currency', 'STRING'), ('price_unit', 'STRING'), ('source_url', 'STRING'),
                  ('source_sha256', 'STRING'), ('source_updated_at', 'DATE'), ('retrieved_at', 'TIMESTAMP'),
                  ('accepted_cutoff', 'DATE'), ('snapshot_id', 'STRING'), ('energy_basis', 'STRING')]
        client = bigquery.Client(project='vaca-muerta-pulse')
        job = client.load_table_from_json(rows, TABLE, job_config=bigquery.LoadJobConfig(
            schema=[bigquery.SchemaField(n, t) for n, t in fields],
            write_disposition='WRITE_TRUNCATE'), location='US')
        job.result(timeout=120)
        print(json.dumps({'table': TABLE, 'rows': job.output_rows, 'job_id': job.job_id}))
