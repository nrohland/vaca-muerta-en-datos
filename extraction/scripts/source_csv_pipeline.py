"""Immutable official CSV candidate stages. Never touches shared raw or publishes."""
import argparse
import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import HTTPRedirectHandler, build_opener

from prepare_csv_candidate import prepare

RESOURCE = 'fb7a47a0-cba9-4667-a004-6f6c1c346c23'
PROJECT = 'vaca-muerta-pulse'
DATASET = 'raw_cap4_candidate_dev'
MAX_ROWS = 2_000_000
MAX_BYTES = 1024**3


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def official_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('https', 'http') or parsed.hostname != 'datos.energia.gob.ar' or parsed.username or parsed.password or parsed.port not in (None,80,443):
        raise ValueError('Only the exact public official energy portal is allowed')
    metadata = parsed.path == '/api/3/action/resource_show' and parse_qs(parsed.query) == {'id': [RESOURCE]}
    download = parsed.path == f'/dataset/c846e79c-026c-4040-897f-1ad3543b407c/resource/{RESOURCE}/download/produccin-de-pozos-de-gas-y-petrleo-2026.csv' and not parsed.query
    if not (metadata or download):
        raise ValueError('URL must match the exact reviewed annual resource path')
    return url


class OfficialRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        official_url(newurl)
        return super().redirect_request(request, fp, code, msg, headers, newurl)


opener = build_opener(OfficialRedirect())


def urlopen(url, timeout=30):
    official_url(url)
    return opener.open(url, timeout=timeout)


def fetch(url, output):
    official_url(url)
    with urlopen(url, timeout=30) as response, output.open('xb') as target:
        official_url(response.url)
        count = 0
        while chunk := response.read(1024**2):
            count += len(chunk)
            if count > MAX_BYTES:
                raise ValueError('Source exceeds 1 GiB download budget')
            target.write(chunk)
    return {'downloaded_at': datetime.now(timezone.utc).isoformat(), 'final_url': response.url,
            'transport_security': 'https' if urlparse(response.url).scheme == 'https' else 'official_public_http_redirect'}


def review_csv(source, release, year, cutoff, *, allow_out_of_scope_negative=False):
    """Accepted snapshot anchors VM counts and volumes; no newest-month inference."""
    rows = defaultdict(lambda: {'rows': 0, 'oil_m3': 0.0, 'gas_km3': 0.0})
    total = 0
    anomalies = []
    with source.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            total += 1
            if total > MAX_ROWS:
                raise ValueError('Source exceeds 2 million row budget')
            is_vm = row['formacion'] == 'vaca muerta' and row['tipo_de_recurso'] == 'NO CONVENCIONAL'
            for field in ('prod_pet', 'prod_gas'):
                value = float(row[field])
                if (not math.isfinite(value) or (value < 0 and is_vm)
                    or (value < -1e-12 and not allow_out_of_scope_negative)):
                    raise ValueError('Invalid raw production volume')
                if value < 0:
                    anomalies.append({'field':field, 'raw_value':row[field], 'idpozo':row.get('idpozo'),
                                      'year':row['anio'], 'month':row['mes'], 'formation':row['formacion'],
                                      'resource_type':row['tipo_de_recurso'], 'scope':'outside_vm_noconv',
                                      'action':('preserved_unchanged_outside_product_negative' if allow_out_of_scope_negative
                                                else 'preserved_unchanged_nonvm_floating_point_warning')})
            if is_vm:
                period = f"{int(row['anio']):04d}-{int(row['mes']):02d}-01"
                metric = rows[period]
                metric['rows'] += 1
                metric['oil_m3'] += float(row['prod_pet'])
                metric['gas_km3'] += float(row['prod_gas'])
    expected = json.loads(release.read_text())['production']
    accepted = [f'{year:04d}-{month:02d}-01' for month in range(1, cutoff+1)]
    compared = []
    for period in accepted:
        for fluid, unit_field, factor in [('oil', 'oil_m3', 6.289810770432105), ('gas', 'gas_km3', 0.001)]:
            anchors = [r for r in expected if r['periodo'] == period and r['fluid'] == fluid]
            if len(anchors) != 1 or not anchors[0].get('is_complete'):
                raise ValueError('Missing independently accepted snapshot anchor')
            anchor = anchors[0]
            actual = rows[period]
            if actual['rows'] != anchor['reported_well_rows'] or not math.isclose(actual[unit_field]*factor, anchor['volume'], rel_tol=1e-9, abs_tol=1e-6):
                raise ValueError('Official source differs from accepted VM snapshot; independent review required')
            compared.append({'period': period, 'fluid': fluid, 'volume': anchor['volume'], 'rows': actual['rows']})
    return {'accepted_periods': accepted, 'vm_reconciliation': compared,
            'source_rows': total, 'anchor_sha256': digest(release),
            'basis': 'VM counts and both-fluid totals reconciled to independently reviewed snapshot; raw revisions outside VM retained',
            'excluded_periods': sorted(set(rows)-set(accepted)), 'warnings':anomalies,
            'warning_count':len(anomalies), 'negative_tolerance_nonvm':None if allow_out_of_scope_negative else 1e-12,
            'negative_policy': 'strict_vm_preserve_flag_outside_product' if allow_out_of_scope_negative else 'strict_all_with_nonvm_roundoff_tolerance'}


def prepare_stage(args):
    if args.year != 2026 or args.month != 8 or args.resource_id != RESOURCE:
        raise ValueError('This reviewed contract is restricted to annual 2026 and August cutoff')
    if args.output.exists():
        raise ValueError('New candidate directory required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    download = args.output.with_suffix('.csv')
    metadata_url = f'https://datos.energia.gob.ar/api/3/action/resource_show?id={RESOURCE}'
    with urlopen(metadata_url, timeout=30) as response:
        official_url(response.url)
        metadata_transport = response.url
        before = json.load(response)['result']
    source_url = before['url'].replace('http://', 'https://', 1)
    transport = fetch(source_url, download)
    extracted_at = transport['downloaded_at']
    with urlopen(metadata_url, timeout=30) as response:
        after = json.load(response)['result']
    if any(before.get(k) != after.get(k) for k in ('id', 'url', 'size', 'last_modified')):
        raise ValueError('Resource changed during download')
    reviewed = review_csv(download, args.anchor_release, args.year, args.month)
    manifest = prepare(download, args.contract, args.output, args.year, before)
    manifest['normalized_at'] = manifest.pop('extracted_at')
    manifest['extracted_at'] = extracted_at
    manifest['downloaded_at'] = extracted_at
    manifest['source_url'] = source_url
    manifest['download_transport'] = transport
    manifest['metadata_final_url'] = metadata_transport
    manifest['limitations'] += ['The public portal redirects to HTTP; SHA-256 binds retained bytes and VM reconciliation, not authenticated in-transit provenance.']
    manifest['review'] = reviewed
    manifest['status'] = 'pass'
    manifest['year'] = args.year
    evidence = {'resource_id': RESOURCE, 'year': args.year, 'source_sha256': manifest['sha256_csv'],
                'hash_scope': 'official_csv_bytes', 'extracted_at': extracted_at,
                'year_rows': manifest['rows'], 'month_rows': manifest['period_rows'],
                'coverage_status': 'reviewed_complete_snapshot', 'accepted_periods': reviewed['accepted_periods'],
                'review': reviewed, 'publication_approved': False}
    (args.output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (args.output/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    return {'status': 'pass', 'rows': manifest['rows'], 'source_sha256': manifest['sha256_csv'], 'publication_approved': False}


def load_stage(args):
    if args.project != PROJECT or args.dataset != DATASET:
        raise ValueError('Writes restricted to exact candidate project/dataset')
    manifest = json.loads((args.candidate/'manifest.json').read_text())
    evidence = json.loads((args.candidate/'evidence.json').read_text())
    contract = json.loads(args.contract.read_text())
    if manifest.get('status') != 'pass' or not manifest.get('review') or not 0 < manifest['rows'] <= MAX_ROWS:
        raise ValueError('Validated source manifest required')
    if (manifest.get('year') != 2026 or manifest.get('resource',{}).get('id') != RESOURCE
        or manifest.get('schema') != contract or evidence.get('resource_id') != RESOURCE
        or evidence.get('year') != 2026 or evidence.get('year_rows') != manifest['rows']
        or evidence.get('source_sha256') != manifest.get('sha256_csv')
        or evidence.get('month_rows') != manifest.get('period_rows')
        or evidence.get('hash_scope') != 'official_csv_bytes'
        or evidence.get('coverage_status') != 'reviewed_complete_snapshot'
        or evidence.get('accepted_periods') != [f'2026-{m:02d}-01' for m in range(1,9)]
        or not re.fullmatch('[a-f0-9]{64}', manifest.get('sha256_csv',''))
        or not re.fullmatch('[a-f0-9]{64}', manifest.get('sha256_normalized_ndjson',''))):
        raise ValueError('Manifest/evidence/resource/schema contract differs')
    extracted = datetime.fromisoformat(manifest['extracted_at'])
    if extracted.tzinfo is None or not 0 <= (datetime.now(timezone.utc)-extracted).total_seconds() <= 7*86400:
        raise ValueError('Source download stale or future')
    year = manifest['year']
    source = args.candidate/f'{year}.raw.ndjson'
    csv_source = args.candidate.with_suffix('.csv')
    if digest(csv_source) != manifest['sha256_csv']:
        raise ValueError('Retained CSV content digest differs')
    if digest(source) != manifest['sha256_normalized_ndjson']:
        raise ValueError('Normalized content digest differs')
    from google.cloud import bigquery
    client = bigquery.Client(project=PROJECT, location='US')
    fields = manifest['schema']
    integers = {'idpozo', 'anio', 'mes', 'idusuario'}
    schema = [bigquery.SchemaField(k, 'STRING' if v == 'text' else 'TIMESTAMP' if v == 'timestamp' else 'INT64' if k in integers else 'FLOAT64') for k,v in fields.items()]
    schema += [bigquery.SchemaField('periodo', 'DATE')]
    schema += [bigquery.SchemaField(k, 'TIMESTAMP') for k in ('_sdc_extracted_at','_sdc_batched_at','_sdc_received_at')]
    schema += [bigquery.SchemaField('_source_sha256','STRING')]
    stamped = args.candidate/'load.ndjson'
    batched = datetime.now(timezone.utc).isoformat()
    with source.open() as stream, stamped.open('x') as target:
        for line in stream:
            record = json.loads(line)
            record.update(_sdc_extracted_at=manifest['extracted_at'], _sdc_batched_at=batched,
                          _sdc_received_at=batched, _source_sha256=manifest['sha256_csv'])
            target.write(json.dumps(record, ensure_ascii=False, allow_nan=False)+'\n')
    config = bigquery.LoadJobConfig(schema=schema, source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE, max_bad_records=0,
        time_partitioning=bigquery.TimePartitioning(type_=bigquery.TimePartitioningType.MONTH,field='_sdc_batched_at'),
        clustering_fields=['empresa','idpozo','cuenca'])
    run_key = hashlib.sha256(manifest['downloaded_at'].encode()).hexdigest()[:12]
    with stamped.open('rb') as stream:
        job = client.load_table_from_file(stream, f'{PROJECT}.{DATASET}.produccion_pozo_mes', job_config=config,
            job_id='csv_candidate_'+manifest['sha256_csv'][:24]+'_'+run_key, location='US')
        job.result(timeout=300)
    result = {'status':'pass','job_id':job.job_id,'source_sha256':manifest['sha256_csv'],
              'rows':job.output_rows,'destination':str(job.destination),'loaded_at':batched,'publication_approved':False}
    if job.output_rows != manifest['rows']:
        raise ValueError('Load rows differ from source')
    (args.candidate/'load-receipt.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='stage', required=True)
    source = commands.add_parser('prepare')
    source.add_argument('--resource-id', required=True)
    source.add_argument('--year', type=int, required=True)
    source.add_argument('--month', type=int, required=True)
    source.add_argument('--contract', type=Path, required=True)
    source.add_argument('--anchor-release', type=Path, required=True)
    source.add_argument('--output', type=Path, required=True)
    load = commands.add_parser('load')
    load.add_argument('--project', required=True)
    load.add_argument('--dataset', required=True)
    load.add_argument('--candidate', type=Path, required=True)
    load.add_argument('--contract', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare_stage(args) if args.stage == 'prepare' else load_stage(args)))


if __name__ == '__main__':
    main()
