"""Bind both candidate benchmarks to immutable per-product source metadata.
Only bounded SELECTs; no raw records or credentials exported.
"""
import argparse
import json
from pathlib import Path
import re
from datetime import date, datetime, timezone

PRICE_URL = 'https://www.eia.gov/dnav/pet/hist/leafhandler.ashx?f=m&n=pet&s=rbrte'
GAS_URL = 'https://www.eia.gov/dnav/ng/hist/rngwhhdm.htm'
ENERGY_BASIS = 'EIA_US_AVERAGE_1036_BTU_PER_CUBIC_FOOT_SCENARIO_V1'
REFERENCES = {'oil': ('EIA_BRENT_MONTHLY', 'bbl', PRICE_URL, None),
              'gas': ('EIA_HENRY_HUB_MONTHLY', 'MMBTU', GAS_URL, ENERGY_BASIS)}


def validate_price_manifest(price):
    if (price.get('schema_version') != 2 or price.get('cutoff') != '2026-08-01'
        or price.get('gas_valuation_enabled') is not True
        or price.get('gas_valuation_kind') != 'international_reference_scenario'
        or set(price.get('products', {})) != set(REFERENCES)
        or not re.fullmatch('[a-f0-9]{64}', str(price.get('rows_sha256', '')))):
        raise ValueError('Reviewed dual benchmark pricing lineage required')
    total = 0
    timestamps = []
    for product, (benchmark, unit, url, basis) in REFERENCES.items():
        value = price['products'][product]
        if (value.get('product') != product or value.get('benchmark') != benchmark
            or value.get('currency') != 'USD' or value.get('price_unit', '').upper() != unit.upper()
            or value.get('source_url') != url or value.get('energy_basis') != basis
            or value.get('cutoff') != price['cutoff']
            or not re.fullmatch('[a-f0-9]{64}', str(value.get('response_sha256', '')))
            or value.get('snapshot_id') != value['response_sha256']
            or type(value.get('row_count')) is not int or value['row_count'] <= 0):
            raise ValueError('Reviewed source URL, units, basis and snapshot required')
        retrieved = datetime.fromisoformat(value['retrieved_at'])
        updated = date.fromisoformat(value['source_updated_at'])
        if (retrieved.tzinfo is None or updated > retrieved.date()
            or not 0 <= (datetime.now(timezone.utc)-retrieved).total_seconds() <= 7*86400):
            raise ValueError('Pricing evidence stale/future or invalid source chronology')
        total += value['row_count']; timestamps.append(retrieved)
    if type(price.get('row_count')) is not int or price['row_count'] != total:
        raise ValueError('Per-product row counts differ')
    if datetime.fromisoformat(price['retrieved_at']) != min(timestamps):
        raise ValueError('Combined freshness must preserve oldest source retrieval')
    return price['products']


def verify(directory):
    from google.cloud import bigquery
    source = json.loads((directory/'source-evidence.json').read_text())
    price = json.loads((directory/'price-manifest.json').read_text())
    products = validate_price_manifest(price)
    if not re.fullmatch('[a-f0-9]{64}', source['source_sha256']):
        raise ValueError('Reviewed content fingerprint required')
    parameters = [bigquery.ScalarQueryParameter('source_sha', 'STRING', source['source_sha256']),
                  bigquery.ScalarQueryParameter('cutoff', 'DATE', price['cutoff'])]
    clauses = []
    for product, (benchmark, unit, url, basis) in REFERENCES.items():
        meta = products[product]
        for name, kind, value in [('sha', 'STRING', meta['response_sha256']), ('url', 'STRING', url),
            ('updated', 'DATE', date.fromisoformat(meta['source_updated_at'])),
            ('retrieved', 'TIMESTAMP', datetime.fromisoformat(meta['retrieved_at']))]:
            parameters.append(bigquery.ScalarQueryParameter(product+'_'+name, kind, value))
        energy = 'energy_basis IS NULL' if basis is None else "energy_basis = '"+ENERGY_BASIS+"'"
        # COALESCE prevents nullable comparisons from escaping COUNTIF.
        clauses.append(f"(product = '{product}' AND benchmark = '{benchmark}' AND UPPER(price_unit) = '{unit.upper()}' AND {energy} AND source_sha256 = @{product}_sha AND snapshot_id = @{product}_sha AND source_url = @{product}_url AND source_updated_at = @{product}_updated AND retrieved_at = @{product}_retrieved)")
    valid_reference = ' OR '.join(clauses)
    sql = """WITH source AS (
      SELECT COUNT(*) n, COUNTIF(_source_sha256 IS NULL OR _source_sha256 != @source_sha) mismatched
      FROM `vaca-muerta-pulse.raw_cap4_candidate_dev.produccion_pozo_mes`
    ), price AS (
      SELECT COUNT(*) n,
        COUNTIF(NOT COALESCE((""" + valid_reference + """), FALSE)
          OR currency IS NULL OR currency != 'USD'
          OR accepted_cutoff IS NULL OR accepted_cutoff != @cutoff
          OR price IS NULL OR price <= 0 OR IS_NAN(price) OR IS_INF(price)
          OR periodo > @cutoff OR periodo IS NULL) mismatched,
        COUNTIF(product = 'oil') oil_rows, COUNTIF(product = 'gas') gas_rows,
        COUNTIF(product = 'oil' AND periodo = @cutoff) required_oil_rows,
        COUNTIF(product = 'gas' AND periodo = @cutoff) required_gas_rows,
        COUNT(*) - COUNT(DISTINCT product || ':' || CAST(periodo AS STRING)) duplicate_period_rows
      FROM `vaca-muerta-pulse.raw_cap4_candidate_dev.monthly_reference_price`
    ) SELECT source.n source_rows, source.mismatched source_mismatched_rows,
      price.n price_rows, price.mismatched price_mismatched_rows,
      price.oil_rows, price.gas_rows, price.required_oil_rows, price.required_gas_rows,
      price.duplicate_period_rows duplicate_price_period_rows FROM source CROSS JOIN price"""
    client = bigquery.Client(project='vaca-muerta-pulse', location='US')
    job = client.query(sql, job_config=bigquery.QueryJobConfig(maximum_bytes_billed=1024**3,
                       use_query_cache=False, query_parameters=parameters))
    row = dict(next(iter(job.result(timeout=120))))
    passed = (row['source_rows'] == source['year_rows'] and row['price_rows'] == price['row_count']
              and row['source_mismatched_rows'] == 0 and row['price_mismatched_rows'] == 0
              and row['oil_rows'] == products['oil']['row_count']
              and row['gas_rows'] == products['gas']['row_count']
              and row['required_oil_rows'] == 1 and row['required_gas_rows'] == 1
              and row['duplicate_price_period_rows'] == 0)
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
