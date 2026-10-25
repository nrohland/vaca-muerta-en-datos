"""Read-only bounded reconciliation of the exact reviewed annual CSV bundle."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re

PROJECT = 'vaca-muerta-pulse'
DATASET = 'raw_cap4_candidate_dev'


def check_artifact(source):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'extraction/scripts'))
    from source_history_pipeline import bundle_digest, validate_bundle
    validate_bundle(source)
    if source['source_sha256'] != bundle_digest(source['sources']):
        raise ValueError('Historical bundle fingerprint differs')
    return source


def verify(directory):
    from google.cloud import bigquery
    source = check_artifact(json.loads((directory/'source-evidence.json').read_text()))
    params = []
    hashes = []
    for value in source['sources']:
        year = value['year']
        params.append(bigquery.ScalarQueryParameter('sha_'+str(year), 'STRING', value['source_sha256']))
        hashes.append(f'(anio = {year} AND _source_sha256 = @sha_{year})')
    sql = '''WITH keys AS (
      SELECT idpozo, anio, mes, COUNT(*) n
      FROM `vaca-muerta-pulse.raw_cap4_candidate_dev.produccion_pozo_mes`
      GROUP BY 1,2,3
    ), raw AS (
      SELECT *, formacion = 'vaca muerta' AND tipo_de_recurso = 'NO CONVENCIONAL' AS is_vm
      FROM `vaca-muerta-pulse.raw_cap4_candidate_dev.produccion_pozo_mes`
    ) SELECT anio AS `year`, mes AS `month`, COUNT(*) AS `rows`,
      COUNTIF(NOT COALESCE(('''+' OR '.join(hashes)+'''), FALSE)) mismatched_hash_rows,
      COUNTIF(idpozo IS NULL OR idpozo <= 0 OR anio NOT BETWEEN 2023 AND 2026 OR mes NOT BETWEEN 1 AND 12
        OR periodo IS NULL OR periodo != SAFE.PARSE_DATE('%Y-%m-%d', FORMAT('%04d-%02d-01',anio,mes))) invalid_keys,
      COUNTIF(prod_pet IS NULL OR prod_gas IS NULL OR IS_NAN(prod_pet) OR IS_INF(prod_pet)
        OR IS_NAN(prod_gas) OR IS_INF(prod_gas)
        OR (is_vm AND (prod_pet < 0 OR prod_gas < 0))) invalid_volumes,
      COUNTIF(_sdc_batched_at IS NULL OR _sdc_extracted_at IS NULL
        OR _sdc_extracted_at > _sdc_batched_at OR _sdc_batched_at > CURRENT_TIMESTAMP()
        OR _sdc_extracted_at < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)) invalid_freshness,
      COUNTIF(NOT COALESCE(is_vm,FALSE) AND prod_pet < 0) +
      COUNTIF(NOT COALESCE(is_vm,FALSE) AND prod_gas < 0) negative_fields_outside_product,
      COUNTIF(is_vm) vm_rows, SUM(IF(is_vm, prod_pet, 0)) oil_m3, SUM(IF(is_vm, prod_gas, 0)) gas_km3,
      (SELECT COALESCE(SUM(n-1),0) FROM keys) duplicate_keys
      FROM raw GROUP BY anio,mes ORDER BY anio,mes'''
    client=bigquery.Client(project=PROJECT,location='US')
    job=client.query(sql,job_config=bigquery.QueryJobConfig(maximum_bytes_billed=1024**3,
        use_query_cache=False,query_parameters=params))
    rows=[dict(r) for r in job.result(timeout=180)]
    expected={period:count for s in source['sources'] for period,count in s['month_rows'].items()}
    checks=[]
    anchors={ (r['period'],r['fluid']):r for s in source['sources'] for r in s['review']['vm_reconciliation'] }
    for row in rows:
        period=f"{row['year']:04d}-{row['month']:02d}-01"
        valid=(row['rows']==expected.get(period) and all(row[k]==0 for k in
            ['mismatched_hash_rows','invalid_keys','invalid_volumes','invalid_freshness','duplicate_keys']))
        for fluid,field,factor in [('oil','oil_m3',6.289810770432105),('gas','gas_km3',0.001)]:
            anchor=anchors.get((period,fluid))
            if period in source['accepted_periods']:
                valid=valid and anchor is not None and row['vm_rows']==anchor['rows'] and math.isclose(
                    row[field]*factor,anchor['volume'],rel_tol=1e-9,abs_tol=1e-6)
        expected_warnings=sum(1 for v in source['sources'] for w in v['review']['warnings']
            if f"{int(w['year']):04d}-{int(w['month']):02d}-01" == period)
        valid=valid and row['negative_fields_outside_product']==expected_warnings
        checks.append({'period':period,'status':'pass' if valid else 'fail',**row})
    valid=(len(rows)==len(expected) and sum(r['rows'] for r in rows)==source['total_rows'] and
        all(r['status']=='pass' for r in checks) and set(source['accepted_periods']).issubset(
            {r['period'] for r in checks}))
    return {'status':'pass' if valid else 'fail','results':checks,'job_id':job.job_id,
        'bytes_processed':job.total_bytes_processed,'publication_approved':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact',type=Path,required=True)
    result=verify(parser.parse_args().artifact)
    print(json.dumps(result))
    raise SystemExit(result['status']!='pass')
