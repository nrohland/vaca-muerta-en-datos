"""Load reviewed immutable price snapshot into the isolated candidate table.

Explicit --apply required; no IAM changes, keys, production or dev writes.
"""
import argparse
import hashlib
import json
import math
import re
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from import_brent import URL
from import_henry_hub import URL as GAS_URL, BENCHMARK as GAS_BENCHMARK, ENERGY_BASIS

TABLE = 'vaca-muerta-pulse.raw_cap4_candidate_dev.monthly_reference_price'


def validate(payload, manifest):
    if hashlib.sha256(payload).hexdigest() != manifest['rows_sha256']:
        raise ValueError('Rows checksum mismatch')
    version = manifest.get('schema_version')
    if version == 1:
        if manifest.get('gas_valuation_enabled') is not False:
            raise ValueError('Legacy snapshot cannot enable gas')
        products = {'oil': dict(product='oil', benchmark='EIA_BRENT_MONTHLY', currency='USD',
            price_unit='bbl', source_url=URL, response_sha256=manifest['response_sha256'],
            snapshot_id=manifest['response_sha256'], retrieved_at=manifest['retrieved_at'],
            source_updated_at=manifest['source_updated_at'], row_count=manifest['row_count'],
            cutoff=manifest['cutoff'], energy_basis=None)}
    elif version == 2:
        products = manifest['products']
        if set(products) != {'oil','gas'} or manifest.get('gas_valuation_enabled') is not True or manifest.get('gas_valuation_kind') != 'international_reference_scenario':
            raise ValueError('Combined snapshot requires both reviewed benchmarks and explicit scenario')
    else:
        raise ValueError('Unknown manifest version')
    cutoff = date.fromisoformat(manifest['cutoff'])
    if cutoff.day != 1:
        raise ValueError('Invalid cutoff')
    expected = {'oil': ('EIA_BRENT_MONTHLY', 'bbl', URL, None),
                'gas': (GAS_BENCHMARK, 'MMBTU', GAS_URL, ENERGY_BASIS)}
    now = datetime.now(timezone.utc)
    for product, meta in products.items():
        benchmark, unit, url, energy_basis = expected[product]
        if (meta.get('product') != product or meta.get('benchmark') != benchmark
            or meta.get('currency') != 'USD' or meta.get('price_unit') != unit
            or meta.get('source_url') != url or meta.get('energy_basis') != energy_basis
            or meta.get('cutoff') != manifest['cutoff']):
            raise ValueError('Invalid source contract')
        sha = meta['response_sha256']
        if not isinstance(sha, str) or not re.fullmatch('[a-f0-9]{64}', sha) or meta['snapshot_id'] != sha:
            raise ValueError('Invalid source hash')
        observed = datetime.fromisoformat(meta['retrieved_at'])
        if observed.tzinfo is None or observed > now + timedelta(minutes=5) or observed < now - timedelta(days=7):
            raise ValueError('Source retrieval is future or stale')
        if date.fromisoformat(meta['source_updated_at']) > observed.date():
            raise ValueError('Release after source retrieval')
    if version == 2 and manifest['retrieved_at'] != min(products.values(), key=lambda p: datetime.fromisoformat(p['retrieved_at']))['retrieved_at']:
        raise ValueError('Combined timestamp must reflect oldest source')
    rows = [json.loads(line) for line in payload.splitlines()]
    if len(rows) != manifest['row_count'] or not rows:
        raise ValueError('Row count mismatch')
    keys = set()
    counts = {product:0 for product in products}
    for r in rows:
        product = r['product']
        if product not in products:
            raise ValueError('Unreviewed product')
        meta = products[product]
        period = date.fromisoformat(r['periodo'])
        key = (product, r['periodo'])
        if period.day != 1 or key in keys or period > cutoff:
            raise ValueError('Invalid period or duplicate')
        keys.add(key); counts[product] += 1
        for field in ('benchmark','currency','price_unit','source_url','energy_basis','retrieved_at','source_updated_at','snapshot_id'):
            if r[field] != meta[field]:
                raise ValueError('Snapshot metadata mismatch: '+field)
        if r['source_sha256'] != meta['response_sha256'] or r['accepted_cutoff'] != manifest['cutoff']:
            raise ValueError('Source hash or cutoff mismatch')
        if isinstance(r['price'], bool) or not isinstance(r['price'], (int, float)) or not math.isfinite(r['price']) or r['price'] <= 0:
            raise ValueError('Invalid price')
    for product, meta in products.items():
        if counts[product] != meta['row_count'] or (product,manifest['cutoff']) not in keys:
            raise ValueError('Product row count or required cutoff missing')
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
