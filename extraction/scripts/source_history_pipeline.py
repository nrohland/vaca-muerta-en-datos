"""Official 2023–2026 CSV bundle, isolated raw candidate only; no promotion.

The ingestion stamp means arrival in the prepared staging file. loaded_at records
completion of the actual BigQuery load; no source retrieval timestamp is renewed.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import threading
import time
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import HTTPRedirectHandler, build_opener
from urllib.error import HTTPError, URLError
from http.client import IncompleteRead
import ssl

if __package__:
    from .prepare_csv_candidate import prepare
    from .source_csv_pipeline import review_csv, digest
else:
    from prepare_csv_candidate import prepare
    from source_csv_pipeline import review_csv, digest

PROJECT = 'vaca-muerta-pulse'
DATASET = 'raw_cap4_candidate_dev'
DESTINATION = f'{PROJECT}.{DATASET}.produccion_pozo_mes'
START_PERIOD = '2023-01-01'
CUTOFF = '2026-08-01'
RESOURCES = {2023:'231c39b3-e81e-4398-af8d-b115807f2c25',
             2024:'43a09dce-1742-44d0-bc13-f193deaab563',
             2025:'d774b5d7-0756-48fe-88f2-8729b57b22da',
             2026:'fb7a47a0-cba9-4667-a004-6f6c1c346c23'}
PACKAGE = 'c846e79c-026c-4040-897f-1ad3543b407c'
MAX_ROWS_YEAR = 2_000_000
MAX_BYTES = 1024**3
MAX_ROWS = MAX_ROWS_YEAR * len(RESOURCES)
HASH_SCOPE = 'official_csv_bundle'


def now():
    return datetime.now(timezone.utc).isoformat()


def accepted_periods():
    return [f'{y}-{m:02d}-01' for y in RESOURCES for m in range(1, 9 if y == 2026 else 13)]


def bundle_digest(sources):
    return hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def fresh(timestamp):
    moment = datetime.fromisoformat(timestamp)
    if moment.tzinfo is None or not 0 <= (datetime.now(timezone.utc)-moment).total_seconds() <= 7*86400:
        raise ValueError('Source retrieval stale, future or timezone missing')
    return moment


def official_url(url, year):
    if year not in RESOURCES:
        raise ValueError('Unreviewed annual source')
    p = urlparse(url)
    if (p.scheme not in ('http','https') or p.hostname != 'datos.energia.gob.ar'
        or p.username or p.password or p.port not in (None,80,443) or p.fragment):
        raise ValueError('Only exact public official portal is allowed')
    resource = RESOURCES[year]
    metadata = p.path == '/api/3/action/resource_show' and parse_qs(p.query) == {'id':[resource]}
    download = (p.path == f'/dataset/{PACKAGE}/resource/{resource}/download/produccin-de-pozos-de-gas-y-petrleo-{year}.csv'
                and not p.query)
    if not (metadata or download):
        raise ValueError('URL differs from exact reviewed annual resource')
    return url


class AnnualRedirect(HTTPRedirectHandler):
    def __init__(self, year):
        super().__init__(); self.year = year

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        official_url(newurl,self.year)
        return super().redirect_request(request,fp,code,msg,headers,newurl)


def read_metadata(year, opener):
    url = f'https://datos.energia.gob.ar/api/3/action/resource_show?id={RESOURCES[year]}'
    with opener.open(official_url(url,year), timeout=30) as response:
        official_url(response.url,year)
        value = json.load(response)
    if value.get('success') is not True or not isinstance(value.get('result'),dict):
        raise ValueError('Official metadata response failed')
    metadata = value['result']
    if metadata.get('id') != RESOURCES[year]:
        raise ValueError('Official resource identity differs')
    official_url(metadata['url'],year)
    return metadata


def stable_metadata(before, after, year):
    if before.get('id') != RESOURCES[year] or after.get('id') != RESOURCES[year]:
        raise ValueError('Unreviewed annual resource identity')
    for field in ('id','url','size','last_modified'):
        if before.get(field) != after.get(field):
            raise ValueError('Official resource changed during download')
    official_url(before['url'],year)


def _retrieve_once(year, csv_path):
    opener = build_opener(AnnualRedirect(year))
    before = read_metadata(year,opener)
    source_url = before['url'].replace('http://','https://',1)
    with opener.open(official_url(source_url,year),timeout=30) as response, csv_path.open('xb') as target:
        official_url(response.url,year)
        final_url = response.url
        count = 0
        while chunk := response.read(1024**2):
            count += len(chunk)
            if count > MAX_BYTES:
                raise ValueError('Annual source exceeds 1 GiB download budget')
            target.write(chunk)
    downloaded_at = now()
    after = read_metadata(year,opener)
    stable_metadata(before,after,year)
    return {'year':year,'resource_id':RESOURCES[year],'before':before,'after':after,
            'source_url':source_url,'final_url':final_url,'downloaded_at':downloaded_at,
            'transport_security':'https' if urlparse(final_url).scheme=='https' else 'official_public_http_redirect',
            'sha256':digest(csv_path)}


def retrieve(year, csv_path):
    """Bounded retries; discard partial bytes and retain actual retrieval time."""
    if csv_path.exists():
        raise ValueError('Fresh destination required')
    partial = csv_path.with_suffix(csv_path.suffix + '.partial')
    if partial.exists():
        raise ValueError('Fresh partial destination required')
    for attempt in range(3):
        try:
            receipt = _retrieve_once(year, partial)
            partial.replace(csv_path)
            return receipt
        except (HTTPError, URLError, TimeoutError, ConnectionError, IncompleteRead) as error:
            partial.unlink(missing_ok=True)
            reason = error.reason if isinstance(error, URLError) else error
            retryable = (not isinstance(reason, ssl.SSLError)
                         and (not isinstance(error, HTTPError)
                              or error.code in (429, 500, 502, 503, 504)))
            if not retryable or attempt == 2:
                raise
            time.sleep(2 ** attempt)
        except Exception:
            partial.unlink(missing_ok=True)
            raise


def normalize_retained(year, value):
    if 'before' in value and 'after' in value:
        return value
    resource=value.get('resource',{})
    if value.get('year')!=year or resource.get('id')!=RESOURCES[year]:
        raise ValueError('Retained annual resource identity differs')
    # This retained format records one resource snapshot. Recheck it now, without
    # claiming a retained before/after pair or renewing original retrieval time.
    current=read_metadata(year,build_opener(AnnualRedirect(year)))
    stable_metadata(resource,current,year)
    return {**value,'resource_id':resource['id'],'before':resource,'after':current,
            'downloaded_at':value['extracted_at'],'sha256':value['source_sha256'],
            'transport_security':'https' if urlparse(value['final_url']).scheme=='https' else 'official_public_http_redirect'}


def validate_bundle(evidence):
    if (evidence.get('schema_version')!=2 or evidence.get('start_period')!=START_PERIOD
        or evidence.get('cutoff')!=CUTOFF or evidence.get('hash_scope')!=HASH_SCOPE
        or evidence.get('coverage_status')!='reviewed_complete_snapshot'
        or evidence.get('publication_approved') is not False
        or evidence.get('accepted_periods')!=accepted_periods()):
        raise ValueError('Reviewed history bundle contract differs')
    sources=evidence.get('sources')
    if not isinstance(sources,list) or len(sources)!=4 or [s.get('year') for s in sources]!=list(RESOURCES):
        raise ValueError('Exact four reviewed annual sources required')
    for source in sources:
        year=source['year']
        review=source.get('review',{})
        expected=[p for p in accepted_periods() if p.startswith(str(year))]
        if (source.get('resource_id')!=RESOURCES[year]
            or not re.fullmatch('[a-f0-9]{64}',source.get('source_sha256',''))
            or not isinstance(source.get('year_rows'),int) or not 0<source['year_rows']<=MAX_ROWS_YEAR
            or not isinstance(source.get('month_rows'),dict)
            or any(not re.fullmatch(f'{year}-((0[1-9])|(1[012]))-01',p) or not isinstance(n,int) or n<=0 for p,n in source['month_rows'].items())
            or sum(source['month_rows'].values())!=source['year_rows']
            or review.get('accepted_periods')!=expected or review.get('source_rows')!=source['year_rows']
            or not re.fullmatch('[a-f0-9]{64}',review.get('anchor_sha256',''))):
            raise ValueError('Annual history identity/coverage differs')
        anchors=review.get('vm_reconciliation',[])
        if len(anchors)!=2*len(expected) or {(a.get('period'),a.get('fluid')) for a in anchors}!={(p,f) for p in expected for f in ('oil','gas')}:
            raise ValueError('Exactly both-fluid reviewed anchors required')
        official_url(source['source_url'],year)
        official_url(source['final_url'],year)
        fresh(source['extracted_at'])
    if (evidence.get('source_sha256')!=bundle_digest(sources)
        or evidence.get('total_rows')!=sum(s['year_rows'] for s in sources)
        or evidence.get('extracted_at')!=min(s['extracted_at'] for s in sources)):
        raise ValueError('History bundle digest/counts/timestamp differ')
    return evidence


def validate_retrieval(year, csv_path, retrieval):
    if retrieval.get('year') != year or retrieval.get('resource_id') != RESOURCES[year]:
        raise ValueError('Retained annual source identity differs')
    stable_metadata(retrieval['before'],retrieval['after'],year)
    official_url(retrieval['source_url'],year)
    official_url(retrieval['final_url'],year)
    fresh(retrieval['downloaded_at'])
    if csv_path.stat().st_size > MAX_BYTES or digest(csv_path) != retrieval.get('sha256'):
        raise ValueError('Retained annual source bytes differ or exceed budget')


def review_annual_source(year, inbound, contract, output, anchor_release, measure=None):
    """Download/validate one source; shared by batch CLI and Singer tap."""
    measure = measure or (lambda phase, year, action: action())
    if inbound:
        csv_path = inbound/f'{year}.csv'
        retrieval = normalize_retained(year,json.loads((inbound/f'{year}.retrieval.json').read_text()))
    else:
        csv_path = output/f'{year}.csv'
        retrieval = measure('download',year,lambda:retrieve(year,csv_path))
        (output/f'{year}.retrieval.json').write_text(json.dumps(retrieval,indent=2)+'\n')
    measure('retrieval-validation',year,lambda:validate_retrieval(year,csv_path,retrieval))
    with csv_path.open(encoding='utf-8-sig',newline='') as stream:
        header = next(csv.reader(stream))
    extra = set(header)-set(contract)
    if (len(header)!=len(set(header)) or set(contract)-set(header)
        or extra not in (set(), {'id'} if year==2024 else set())):
        raise ValueError('Annual CSV fields differ from reviewed historical contract')
    annual_contract = {**contract, **({'id':'numeric'} if extra else {})}
    contract_path = output/f'{year}.contract.json'
    contract_path.write_text(json.dumps(annual_contract,sort_keys=True)+'\n')
    review = measure('anchor-review',year,lambda:review_csv(csv_path,anchor_release,year,8 if year==2026 else 12,allow_out_of_scope_negative=True))
    return csv_path,retrieval,review,contract_path

def prepare_stage(args):
    if args.start_period != START_PERIOD or args.cutoff != CUTOFF:
        raise ValueError('Reviewed history fixed to 2023–August 2026')
    if args.output.exists():
        raise ValueError('New candidate directory required')
    args.output.mkdir(parents=True)
    sources, reviews, periods, hashes, total = [], [], {}, {}, 0
    combined = args.output/'history.raw.parquet'
    contract = json.loads(args.contract.read_text())
    # Only public downloads/reviews overlap, with two workers; one Parquet writer preserves order.
    metrics={'schema_version':1,'started_at':now(),'phases':[],'publication_approved':False}
    metrics_path=getattr(args,'metrics_output',None) or args.output/'preparation-metrics.json'
    metrics_lock=threading.Lock()
    def checkpoint():
        temporary=metrics_path.with_suffix('.partial')
        temporary.write_text(json.dumps(metrics,indent=2)+'\n');temporary.replace(metrics_path)
    def measure(phase,year,action):
        event={'phase':phase,'year':year,'started_at':now(),'status':'running'}
        with metrics_lock:metrics['phases'].append(event);checkpoint()
        start=time.perf_counter()
        try:
            result=action()
            with metrics_lock:
                event['status']='passed'
                if isinstance(result,dict):
                    for name in ('rows','source_rows'):
                        if name in result:event['rows']=result[name]
            return result
        except Exception as error:
            with metrics_lock:event['status']='failed';event['error_type']=type(error).__name__
            raise
        finally:
            with metrics_lock:event.update(seconds=round(time.perf_counter()-start,3),finished_at=now());checkpoint()
    def review_year(year):
        return review_annual_source(year, args.inbound, contract, args.output, args.anchor_release, measure)
    with ThreadPoolExecutor(max_workers=1) as executor:
        futures={year:executor.submit(review_year,year) for year in RESOURCES}
        try:reviewed={year:future.result() for year,future in futures.items()}
        except Exception:
            for future in futures.values():future.cancel()
            raise
    contract = {**contract, 'id':'numeric'}
    if __package__:
        from .parquet_candidate import arrow_schema, append_csv
    else:
        from parquet_candidate import arrow_schema, append_csv
    import pyarrow.parquet as pq
    with pq.ParquetWriter(combined, arrow_schema(contract), compression='zstd',
                          use_dictionary=True, write_statistics=True) as writer:
        for year, resource_id in RESOURCES.items():
            csv_path,retrieval,review,_ = reviewed[year]
            source_hash = retrieval['sha256']
            stamp=now()
            annual = measure('parquet-conversion',year,lambda:append_csv(writer,csv_path,contract,year,source_hash,retrieval['downloaded_at'],stamp))
            if annual['rows'] != review['source_rows'] or not 0 < annual['rows'] <= MAX_ROWS_YEAR:
                raise ValueError('Normalized annual source differs from reviewed bytes')
            source = {'year':year,'resource_id':resource_id,'source_sha256':source_hash,
                      'extracted_at':retrieval['downloaded_at'],'year_rows':annual['rows'],
                      'month_rows':annual['period_rows'],'review':review,
                      'source_url':retrieval['source_url'],'final_url':retrieval['final_url'],
                      'transport_security':retrieval.get('transport_security','official_public_http_redirect')}
            sources.append(source); reviews.append({'year':year,**review})
            periods.update(annual['period_rows']);hashes[str(year)] = source_hash;total += annual['rows']
    if len({p for r in reviews for p in r['accepted_periods']}) != 44:
        raise ValueError('All 44 independently reviewed periods required')
    source_sha = bundle_digest(sources)
    oldest = min(s['extracted_at'] for s in sources)
    evidence = {'schema_version':2,'start_period':START_PERIOD,'cutoff':CUTOFF,
                'sources':sources,'total_rows':total,'accepted_periods':accepted_periods(),
                'source_sha256':source_sha,'extracted_at':oldest,'hash_scope':HASH_SCOPE,
                'coverage_status':'reviewed_complete_snapshot','reviews':reviews,'publication_approved':False}
    manifest = {'schema_version':2,'status':'pass','schema':contract,'rows':total,'total_rows':total,
                'source_hashes':hashes,'source_sha256':source_sha,'sources':sources,
                'extracted_at':oldest,'normalized_at':now(),'period_rows':dict(sorted(periods.items())),
                'start_period':START_PERIOD,'cutoff':CUTOFF,'hash_scope':HASH_SCOPE,
                'sha256_payload':digest(combined),'payload':'history.raw.parquet','payload_format':'parquet',
                'payload_bytes':combined.stat().st_size,'compression':'zstd',
                'ingestion_stamp_basis':'arrival_in_prepared_staging_file; loaded_at is actual BigQuery load completion',
                'limitations':['Public official portal may redirect to HTTP; digest identifies bytes, not authenticated transport.',
                               'Acceptance is technical review against retained snapshot; no publication approval.'],
                'publication_approved':False}
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (args.output/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    return {'status':'pass','rows':total,'source_sha256':source_sha,'publication_approved':False}


def validate_candidate(candidate, contract):
    contract = {**contract, 'id':'numeric'}
    manifest = json.loads((candidate/'manifest.json').read_text())
    evidence = json.loads((candidate/'evidence.json').read_text())
    validate_bundle(evidence)
    if (manifest.get('schema_version') != 2 or manifest.get('status')!='pass'
        or manifest.get('schema') != contract or manifest.get('publication_approved') is not False
        or evidence.get('publication_approved') is not False or evidence.get('schema_version') != 2
        or manifest.get('start_period')!=START_PERIOD or evidence.get('start_period')!=START_PERIOD
        or manifest.get('cutoff')!=CUTOFF or evidence.get('cutoff')!=CUTOFF
        or evidence.get('hash_scope')!=HASH_SCOPE or manifest.get('hash_scope')!=HASH_SCOPE
        or evidence.get('coverage_status')!='reviewed_complete_snapshot'
        or evidence.get('accepted_periods')!=accepted_periods()
        or manifest.get('sources') != evidence.get('sources')
        or manifest.get('payload')!='history.raw.parquet' or manifest.get('payload_format')!='parquet'):
        raise ValueError('History manifest/evidence/schema contract differs')
    sources = manifest['sources']
    if not isinstance(sources,list) or len(sources)!=4 or [s.get('year') for s in sources] != list(RESOURCES):
        raise ValueError('Exact four reviewed annual sources required')
    for source in sources:
        year=source['year']
        if (source.get('resource_id')!=RESOURCES[year]
            or not re.fullmatch('[a-f0-9]{64}',source.get('source_sha256',''))
            or not isinstance(source.get('year_rows'),int) or not 0<source['year_rows']<=MAX_ROWS_YEAR
            or not isinstance(source.get('month_rows'),dict)
            or any(not re.fullmatch(f'{year}-((0[1-9])|(1[012]))-01',p) or not isinstance(n,int) or n<=0 for p,n in source['month_rows'].items())
            or sum(source['month_rows'].values())!=source['year_rows']):
            raise ValueError('Annual identity/hash/row counts differ')
        fresh(source['extracted_at'])
    expected_hashes={str(s['year']):s['source_sha256'] for s in sources}
    oldest=min(s['extracted_at'] for s in sources)
    expected_rows=sum(s['year_rows'] for s in sources)
    expected_periods={p:n for s in sources for p,n in s['month_rows'].items()}
    if (manifest.get('source_hashes')!=expected_hashes or manifest.get('source_sha256')!=bundle_digest(sources)
        or evidence.get('source_sha256')!=bundle_digest(sources)
        or manifest.get('extracted_at')!=oldest or evidence.get('extracted_at')!=oldest
        or manifest.get('rows')!=expected_rows or manifest.get('total_rows')!=expected_rows
        or evidence.get('total_rows')!=expected_rows or manifest.get('period_rows')!=expected_periods
        or not re.fullmatch('[a-f0-9]{64}',manifest.get('sha256_payload',''))):
        raise ValueError('History bundle identity/counts differ')
    fresh(manifest['normalized_at'])
    if datetime.fromisoformat(manifest['normalized_at']) < max(datetime.fromisoformat(s['extracted_at']) for s in sources):
        raise ValueError('Normalization precedes source retrieval')
    payload=candidate/'history.raw.parquet'
    if digest(payload)!=manifest['sha256_payload'] or payload.stat().st_size!=manifest.get('payload_bytes'):
        raise ValueError('Combined payload bytes differ')
    if __package__:
        from .parquet_candidate import arrow_schema, timestamp
    else:
        from parquet_candidate import arrow_schema, timestamp
    import pyarrow.parquet as pq
    parquet = pq.ParquetFile(payload)
    if not parquet.schema_arrow.equals(arrow_schema(contract)) or parquet.metadata.num_rows!=expected_rows:
        raise ValueError('Parquet schema/counts differ')
    counts={str(year):0 for year in RESOURCES}; period_counts={}
    by_year={str(s['year']):s for s in sources}
    fields=['anio','periodo','_source_sha256','_sdc_extracted_at','_sdc_batched_at','_sdc_received_at']
    normalized_at=timestamp(manifest['normalized_at'])
    for batch in parquet.iter_batches(batch_size=32768,columns=fields):
        for record in batch.to_pylist():
            year=str(record['anio']); source=by_year.get(year)
            if source is None or record['_source_sha256']!=expected_hashes[year]:
                raise ValueError('Payload annual lineage differs')
            if record['_sdc_extracted_at']!=timestamp(source['extracted_at']):
                raise ValueError('Payload retrieval timestamp differs')
            period=record['periodo']
            if period is None or period.year!=int(year) or period.day!=1:
                raise ValueError('Payload business period differs')
            period_counts[period.isoformat()]=period_counts.get(period.isoformat(),0)+1
            for stamp in ('_sdc_batched_at','_sdc_received_at'):
                if not timestamp(source['extracted_at'])<=record[stamp]<=normalized_at:
                    raise ValueError('Payload ingestion chronology differs')
            counts[year]+=1
    if counts!={str(s['year']):s['year_rows'] for s in sources} or period_counts!=expected_periods:
        raise ValueError('Payload row counts differ')
    return manifest


def load_stage(args):
    if args.project != PROJECT or args.dataset != DATASET:
        raise ValueError('Writes restricted to exact candidate project/dataset')
    contract=json.loads(args.contract.read_text())
    manifest=validate_candidate(args.candidate,contract)
    contract=manifest['schema']
    from google.cloud import bigquery
    client=bigquery.Client(project=PROJECT,location='US')
    integers={'id','idpozo','anio','mes','idusuario'}
    schema=[bigquery.SchemaField(k,'STRING' if v=='text' else 'TIMESTAMP' if v=='timestamp' else 'INT64' if k in integers else 'FLOAT64') for k,v in contract.items()]
    schema += [bigquery.SchemaField('periodo','DATE')]
    schema += [bigquery.SchemaField(k,'TIMESTAMP') for k in ('_sdc_extracted_at','_sdc_batched_at','_sdc_received_at')]
    schema += [bigquery.SchemaField('_source_sha256','STRING')]
    config=bigquery.LoadJobConfig(schema=schema,source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,max_bad_records=0,
        time_partitioning=bigquery.TimePartitioning(type_=bigquery.TimePartitioningType.MONTH,field='_sdc_batched_at'),
        clustering_fields=['empresa','idpozo','cuenca'])
    run_key=hashlib.sha256(manifest['normalized_at'].encode()).hexdigest()[:12]
    with (args.candidate/'history.raw.parquet').open('rb') as stream:
        job=client.load_table_from_file(stream,DESTINATION,job_config=config,
            job_id='parquet_history_candidate_'+manifest['source_sha256'][:24]+'_'+run_key,location='US')
        job.result(timeout=600)
    if str(job.destination) != DESTINATION:
        raise ValueError('Actual load destination differs from isolated candidate')
    if job.output_rows != manifest['rows']:
        raise ValueError('Actual load rows differ from reviewed bundle')
    result={'schema_version':2,'status':'pass','job_id':job.job_id,'source_sha256':manifest['source_sha256'],
            'source_hashes':manifest['source_hashes'],'rows':job.output_rows,'destination':str(job.destination),
            'loaded_at':now(),'publication_approved':False}
    (args.candidate/'load-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='stage',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('--start-period',default=START_PERIOD);prep.add_argument('--cutoff',default=CUTOFF)
    prep.add_argument('--metrics-output',type=Path);prep.add_argument('--inbound',type=Path);prep.add_argument('--contract',type=Path,required=True)
    prep.add_argument('--anchor-release',type=Path,required=True);prep.add_argument('--output',type=Path,required=True)
    load=sub.add_parser('load');load.add_argument('--project',required=True);load.add_argument('--dataset',required=True)
    load.add_argument('--candidate',type=Path,required=True);load.add_argument('--contract',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(prepare_stage(args) if args.stage=='prepare' else load_stage(args)))


if __name__=='__main__':
    main()
