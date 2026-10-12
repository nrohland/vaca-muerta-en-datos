#!/usr/bin/env python3
"""Read-only BigQuery raw gate; requires reviewed source evidence, never publishes."""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def utc(value):
    d = datetime.fromisoformat(value.replace('Z','+00:00')) if isinstance(value,str) else value
    if d.tzinfo is None:
        raise ValueError('timestamp timezone required')
    return d.astimezone(timezone.utc)


def validate_policy(profile, evidence, *, resource_id, year, month, now):
    errors=[]
    def check(condition,message):
        if not condition: errors.append(message)
    period=f'{year:04}-{month:02}-01'
    check(1<=month<=12 and 1900<=year<=now.year, 'invalid year/month')
    check(datetime(year,month,1,tzinfo=timezone.utc)<=now, 'requested period in future')
    check(evidence['resource_id']==resource_id and evidence['year']==year, 'source identity mismatch')
    check(evidence['coverage_status']=='reviewed_complete_snapshot' and period in evidence['accepted_periods'],
          'required month has no reviewed complete coverage')
    check(evidence['hash_scope'] in ('official_csv_bytes','ckan_metadata_counts'), 'unknown source fingerprint scope')
    check(re.fullmatch('[a-f0-9]{64}',evidence['source_sha256']) is not None, 'source fingerprint missing')
    check(profile['total_table_rows']==evidence['year_rows'], 'raw table count differs from exact annual source snapshot')
    check(profile['outside_year_rows']==0, 'raw contains rows outside requested year')
    check(profile['invalid_year_rows']==0, 'raw contains null malformed or invalid year')
    check(profile['total_table_rows']==profile['year_rows'], 'raw table is not exclusively the requested year')
    check(profile['year_rows']==evidence['year_rows'], 'raw annual count differs from exact source snapshot')
    check(profile['month_rows']==evidence['month_rows'][period] and profile['month_rows']>0,
          'required month count differs from exact source snapshot')
    check(profile['duplicate_keys']==0, 'duplicate well/year/month keys')
    check(profile['invalid_periods']==0, 'invalid or future raw period')
    check(profile['invalid_volumes']==0, 'invalid raw volume')
    check(profile['null_keys']==0, 'missing well/year/month key')
    check(profile['null_ingestion_rows']==0, 'missing raw ingestion timestamps')
    newest=utc(profile['loaded_at']);oldest=utc(profile['oldest_loaded_at']);extracted=utc(evidence['extracted_at'])
    check(extracted<=oldest<=newest<=now, 'source/load chronology invalid')
    check((now-oldest).total_seconds()<=7*86400, 'snapshot ingestion older than 7 days')
    check((now-extracted).total_seconds()<=7*86400, 'source extraction older than 7 days')
    return {'status':'fail' if errors else 'pass','errors':errors,'publication_approved':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',required=True);p.add_argument('--dataset',required=True)
    p.add_argument('--resource-id',required=True);p.add_argument('--year',required=True,type=int)
    p.add_argument('--month',required=True,type=int);p.add_argument('--evidence',required=True,type=Path)
    p.add_argument('--observation',type=Path,help='Fresh CKAN observation matching reviewed fingerprint; supplies actual extraction timestamp')
    p.add_argument('--max-bytes',type=int,default=1024**3);p.add_argument('--dry-run',action='store_true')
    args=p.parse_args()
    for value in (args.project,args.dataset):
        if not re.fullmatch('[A-Za-z0-9_-]+',value): p.error('invalid project/dataset identifier')
    if args.max_bytes<=0 or not 1<=args.month<=12: p.error('positive byte budget and month1..12 required')
    from google.cloud import bigquery
    client=bigquery.Client(project=args.project)
    sql=f'''WITH all_rows AS (
 SELECT idpozo,anio,mes,prod_pet,prod_gas,_sdc_batched_at,
 SAFE_CAST(anio AS INT64) year_int,
 SAFE_CAST(anio AS NUMERIC) year_numeric,
 SAFE_CAST(mes AS INT64) month_int,
 SAFE_CAST(mes AS NUMERIC) month_numeric
 FROM `{args.project}.{args.dataset}.produccion_pozo_mes`
), keys AS (SELECT idpozo,anio,mes,COUNT(*) n FROM all_rows GROUP BY 1,2,3)
SELECT COUNT(*) total_table_rows,
 COUNTIF(year_int=@year AND year_numeric=@year) year_rows,
 COUNTIF(year_int IS NULL OR year_numeric IS NULL OR year_int!=@year OR year_numeric!=@year) outside_year_rows,
 COUNTIF(year_int IS NULL OR year_numeric IS NULL OR year_numeric!=year_int
 OR year_int<1900 OR year_int>EXTRACT(YEAR FROM CURRENT_DATE('UTC'))) invalid_year_rows,
 COUNTIF(year_int=@year AND year_numeric=@year AND month_int=@month AND month_numeric=@month) month_rows,
 MIN(_sdc_batched_at) oldest_loaded_at,MAX(_sdc_batched_at) loaded_at,
 COUNTIF(_sdc_batched_at IS NULL) null_ingestion_rows,
 COUNTIF(idpozo IS NULL OR anio IS NULL OR mes IS NULL) null_keys,
 COUNTIF(month_int NOT BETWEEN 1 AND 12 OR month_int IS NULL OR month_numeric IS NULL
 OR month_numeric!=month_int OR year_int IS NULL OR year_numeric IS NULL OR year_numeric!=year_int
 OR (year_int*12+month_int)>EXTRACT(YEAR FROM CURRENT_DATE('UTC'))*12+EXTRACT(MONTH FROM CURRENT_DATE('UTC'))) invalid_periods,
 COUNTIF(SAFE_CAST(prod_pet AS FLOAT64) IS NULL OR SAFE_CAST(prod_gas AS FLOAT64) IS NULL
 OR SAFE_CAST(prod_pet AS FLOAT64)<0 OR SAFE_CAST(prod_gas AS FLOAT64)<0
 OR IS_NAN(SAFE_CAST(prod_pet AS FLOAT64)) OR IS_INF(SAFE_CAST(prod_pet AS FLOAT64))
 OR IS_NAN(SAFE_CAST(prod_gas AS FLOAT64)) OR IS_INF(SAFE_CAST(prod_gas AS FLOAT64))) invalid_volumes,
 (SELECT COALESCE(SUM(n-1),0) FROM keys WHERE n>1) duplicate_keys FROM all_rows'''
    config=bigquery.QueryJobConfig(dry_run=args.dry_run,use_query_cache=False,maximum_bytes_billed=args.max_bytes,
      query_parameters=[bigquery.ScalarQueryParameter('year','INT64',args.year),bigquery.ScalarQueryParameter('month','INT64',args.month)])
    if args.dry_run:
        job=client.query(sql,job_config=config)
        print(json.dumps({'status':'dry_run_only','estimated_bytes':job.total_bytes_processed,'max_bytes':args.max_bytes,'publication_approved':False}));return 0
    evidence=json.loads(args.evidence.read_text())
    if evidence.get('hash_scope')=='ckan_metadata_counts':
        if not args.observation: p.error('CKAN gate requires fresh --observation')
        observation=json.loads(args.observation.read_text())
        for key in ('resource_id','year','year_rows','source_sha256','hash_scope'):
            if evidence.get(key)!=observation.get(key):p.error('observation differs from reviewed evidence: '+key)
        period=f'{args.year:04}-{args.month:02}-01'
        if evidence.get('month_rows',{}).get(period)!=observation.get('month_rows',{}).get(period):p.error('observation month count differs')
        evidence={**evidence,'extracted_at':observation['extracted_at']}
    row=dict(next(iter(client.query(sql,job_config=config).result(timeout=120))))
    try:
        result=validate_policy(row,evidence,resource_id=args.resource_id,year=args.year,month=args.month,now=datetime.now(timezone.utc))
    except (KeyError,ValueError,TypeError) as exc:
        result={'status':'fail','errors':['invalid source evidence/profile: '+str(exc)],'publication_approved':False}
    print(json.dumps(result));return int(result['status']=='fail')

if __name__=='__main__':raise SystemExit(main())
