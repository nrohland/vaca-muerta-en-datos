"""Bind candidate warehouse contents to reviewed extraction/price metadata.

Only SELECTs on the two literal candidate tables, each bounded by 1 GiB.
No credentials or individual records are exported.
"""
import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re

PRICE_URL = 'https://www.eia.gov/dnav/pet/hist/leafhandler.ashx?f=m&n=pet&s=rbrte'


def verify(directory):
    from google.cloud import bigquery
    source = json.loads((directory/'source-evidence.json').read_text())
    price = json.loads((directory/'price-manifest.json').read_text())
    for digest in (source['source_sha256'], price['response_sha256']):
        if not re.fullmatch('[a-f0-9]{64}', digest):
            raise ValueError('Reviewed content fingerprint required')
    if price.get('source_url') != PRICE_URL or price.get('cutoff') != '2026-08-01':
        raise ValueError('Reviewed source URL and cutoff required')
    retrieved = datetime.fromisoformat(price['retrieved_at'])
    updated = date.fromisoformat(price['source_updated_at'])
    if (retrieved.tzinfo is None or updated > retrieved.date()
        or not 0 <= (datetime.now(timezone.utc)-retrieved).total_seconds() <= 7*86400):
        raise ValueError('Price source chronology invalid, future or stale')
    client = bigquery.Client(project='vaca-muerta-pulse', location='US')
    config = bigquery.QueryJobConfig(maximum_bytes_billed=1024**3, use_query_cache=False,
        query_parameters=[bigquery.ScalarQueryParameter('source_sha', 'STRING', source['source_sha256']),
                          bigquery.ScalarQueryParameter('price_sha', 'STRING', price['response_sha256']),
                          bigquery.ScalarQueryParameter('cutoff', 'DATE', price['cutoff']),
                          bigquery.ScalarQueryParameter('price_url', 'STRING', PRICE_URL),
                          bigquery.ScalarQueryParameter('source_updated', 'DATE', updated),
                          bigquery.ScalarQueryParameter('retrieved', 'TIMESTAMP', retrieved)])
    sql = '''WITH source AS (
      SELECT COUNT(*) n, COUNTIF(_source_sha256 IS NULL OR _source_sha256 != @source_sha) mismatched
      FROM `vaca-muerta-pulse.raw_cap4_candidate_dev.produccion_pozo_mes`
    ), price AS (
      SELECT COUNT(*) n,
        COUNTIF(source_sha256 IS NULL OR source_sha256 != @price_sha
          OR snapshot_id IS NULL OR snapshot_id != @price_sha
          OR accepted_cutoff IS NULL OR accepted_cutoff != @cutoff
          OR product IS NULL OR product != 'oil'
          OR benchmark IS NULL OR benchmark != 'EIA_BRENT_MONTHLY'
          OR currency IS NULL OR currency != 'USD'
          OR price_unit IS NULL OR price_unit != 'bbl' OR energy_basis IS NOT NULL
          OR source_url IS NULL OR source_url != @price_url
          OR source_updated_at IS NULL OR source_updated_at != @source_updated
          OR retrieved_at IS NULL OR retrieved_at != @retrieved
          OR price IS NULL OR price <= 0 OR IS_NAN(price) OR IS_INF(price)
          OR periodo > @cutoff OR periodo IS NULL) mismatched,
        COUNTIF(periodo = @cutoff) required_month,
        COUNT(*) - COUNT(DISTINCT periodo) duplicate_period_rows
      FROM `vaca-muerta-pulse.raw_cap4_candidate_dev.monthly_reference_price`
    ) SELECT source.n source_rows, source.mismatched source_mismatched_rows,
      price.n price_rows, price.mismatched price_mismatched_rows,
      price.required_month required_price_rows,
      price.duplicate_period_rows duplicate_price_period_rows FROM source CROSS JOIN price'''
    job = client.query(sql, job_config=config)
    row = dict(next(iter(job.result(timeout=120))))
    passed = (row['source_rows'] == source['year_rows'] and row['price_rows'] == price['row_count']
              and row['source_mismatched_rows'] == 0 and row['price_mismatched_rows'] == 0
              and row['required_price_rows'] == 1 and row['duplicate_price_period_rows'] == 0)
    return {'status': 'pass' if passed else 'fail', 'results': row,
            'job_id': job.job_id, 'bytes_processed': job.total_bytes_processed,
            'publication_approved': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.artifact)
    print(json.dumps(result))
    raise SystemExit(result['status'] != 'pass')
