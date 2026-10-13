"""Same fail-closed candidate CLI locally and in GitHub; no publication stage."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.request import HTTPRedirectHandler, build_opener

from verify_loaded_lineage import validate_price_manifest
from stage_runner import Stage, run, write_report

PROJECT = 'vaca-muerta-pulse'
DATASET = 'raw_cap4_candidate_dev'
RESOURCE = 'fb7a47a0-cba9-4667-a004-6f6c1c346c23'
CUTOFF = '2026-08-01'
BUDGET = 1024**3
SELECTION = ('+fct_company_month', '+fct_area_month', '+fct_production_rate',
             '+fct_reference_valuation_entity_month', '+dim_company', '+dim_area')


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    return json.loads(path.read_text())


def run_json(argv, cwd):
    """Only public helper result JSON reaches the reduced gate artifact."""
    process = subprocess.run(argv, cwd=cwd, check=False, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True)
    if process.returncode:
        # The child may include SQL/paths in its diagnostics; retain them only
        # in the private stage log, never in the public summary JSON.
        sys.stderr.write(process.stderr)
        raise ValueError('Candidate helper failed')
    for line in reversed(process.stdout.splitlines()):
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError('Helper did not return a JSON object')


def assert_extract_artifact(directory, history=False):
    evidence = load_json(directory/'source-evidence.json')
    manifest = load_json(directory/'source-manifest.json')
    receipt = load_json(directory/'source-load.json')
    price = load_json(directory/'price-manifest.json')
    price_receipt = load_json(directory/'price-load.json')
    if history:
        from check_raw_history import check_artifact
        check_artifact(evidence)
        expected_hashes = {str(v['year']):v['source_sha256'] for v in evidence['sources']}
        if (manifest.get('status') != 'pass' or manifest.get('schema_version') != 2
            or manifest.get('source_hashes') != expected_hashes
            or manifest.get('source_sha256') != evidence['source_sha256']
            or receipt.get('status') != 'pass' or receipt.get('source_sha256') != evidence['source_sha256']
            or receipt.get('source_hashes') != expected_hashes
            or receipt.get('rows') != evidence['total_rows']
            or not receipt.get('job_id')
            or receipt.get('destination') != f'{PROJECT}.{DATASET}.produccion_pozo_mes'
            or receipt.get('publication_approved') is not False):
            raise ValueError('Historical extraction artifact source lineage differs')
    else:
        if (evidence.get('resource_id') != RESOURCE or evidence.get('year') != 2026
            or evidence.get('hash_scope') != 'official_csv_bytes'
            or evidence.get('coverage_status') != 'reviewed_complete_snapshot'
            or evidence.get('accepted_periods') != [f'2026-{m:02d}-01' for m in range(1,9)]
            or manifest.get('status') != 'pass' or receipt.get('status') != 'pass'
            or receipt.get('source_sha256') != evidence.get('source_sha256')
            or manifest.get('sha256_csv') != evidence.get('source_sha256')
            or receipt.get('rows') != evidence.get('year_rows')
            or receipt.get('destination') != f'{PROJECT}.{DATASET}.produccion_pozo_mes'
            or receipt.get('publication_approved') is not False):
            raise ValueError('Extraction artifact source lineage differs')
    products = validate_price_manifest(price)
    if (price_receipt.get('table') != f'{PROJECT}.{DATASET}.monthly_reference_price'
        or price_receipt.get('rows') != price['row_count']
        or not price_receipt.get('job_id')
        or price_receipt.get('source_hashes') != {k:v['response_sha256'] for k,v in products.items()}
        or price_receipt.get('rows_sha256') != price['rows_sha256']):
        raise ValueError('Extraction artifact pricing lineage differs')
    extracted = datetime.fromisoformat(evidence['extracted_at'])
    if extracted.tzinfo is None or not 0 <= (datetime.now(timezone.utc)-extracted).total_seconds() <= 7*86400:
        raise ValueError('Source evidence stale/future')
    return evidence


def configure_profile(run_dir):
    directory = run_dir/'profiles'
    directory.mkdir(exist_ok=False)
    # ADC resolves a local login or short-lived WIF automatically. Never write
    # credential paths, tokens or private keys into an artifact.
    directory.joinpath('profiles.yml').write_text('''vaca_muerta_pulse:
  target: candidate
  outputs:
    candidate:
      type: bigquery
      method: oauth
      project: vaca-muerta-pulse
      dataset: stg_cap4_candidate_dev
      location: US
      threads: 1
      maximum_bytes_billed: 1073741824
      job_execution_timeout_seconds: 300
      job_retries: 0
''')
    return directory


def normalized_report(value):
    return {**value, 'status':'pass', 'publication_approved':False}


def execute_stage(args):
    root = args.repo.resolve()
    out = args.run_dir.resolve()
    scratch = args.scratch_dir.resolve()
    candidate = scratch/'source'
    artifact = args.extract_artifact.resolve() if args.extract_artifact else out
    contract = root/'extraction/contracts/production_csv.json'
    python = args.python
    report = {}
    history = getattr(args, 'history', False)
    if args.stage == 'source-prepare':
        if history:
            argv = [python,str(root/'extraction/scripts/source_history_pipeline.py'),'prepare',
                '--contract',str(contract),'--anchor-release',str(root/'docs/evidence/historical-source/physical-anchors.json'),
                '--output',str(candidate)]
            if getattr(args, 'source_inbound', None):
                argv += ['--inbound',str(args.source_inbound.resolve())]
            report = run_json(argv,root)
        else:
            report = run_json([python,str(root/'extraction/scripts/source_csv_pipeline.py'),'prepare',
            '--resource-id',RESOURCE,'--year','2026','--month','8','--contract',str(contract),
            '--anchor-release',str(root/'apps/web/public/data/release.json'),'--output',str(candidate)],root)
        if report.get('status') != 'pass' or report.get('publication_approved') is not False:
            raise ValueError('Source prepare gate rejected')
        write_report(out/'source-evidence.json',load_json(candidate/'evidence.json'))
        write_report(out/'source-manifest.json',load_json(candidate/'manifest.json'))
    elif args.stage == 'source-load':
        report = run_json([python,str(root/('extraction/scripts/source_history_pipeline.py' if history else 'extraction/scripts/source_csv_pipeline.py')),'load',
            '--project',PROJECT,'--dataset',DATASET,'--candidate',str(candidate),'--contract',str(contract)],root)
        if report.get('status') != 'pass' or report.get('publication_approved') is not False:
            raise ValueError('Source load gate rejected')
        write_report(out/'source-load.json',report)
    elif args.stage == 'price-prepare':
        from verify_loaded_lineage import PRICE_URL, GAS_URL
        scripts = root/'scripts'
        downloaded = {}
        for name, allowed in [('brent',PRICE_URL),('henry_hub',GAS_URL)]:
            class SameOfficialURL(HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    if newurl != allowed:
                        raise ValueError('Unexpected EIA redirect')
                    return super().redirect_request(req,fp,code,msg,headers,newurl)
            with build_opener(SameOfficialURL()).open(allowed,timeout=30) as response:
                if response.url != allowed:
                    raise ValueError('Unexpected EIA URL')
                raw = response.read(5*1024**2+1)
                if len(raw)>5*1024**2:
                    raise ValueError('EIA response exceeds budget')
            response_path = scratch/(name+'.html'); response_path.write_bytes(raw)
            downloaded[name] = (response_path,utc_now(),hashlib.sha256(raw).hexdigest())
        rows = scratch/'price.ndjson'
        manifest = run_json([python,str(scripts/'prepare_reference_prices.py'),
            '--source',str(downloaded['brent'][0]),'--cutoff',CUTOFF,
            '--retrieved-at',downloaded['brent'][1],
            '--gas-source',str(downloaded['henry_hub'][0]),
            '--gas-retrieved-at',downloaded['henry_hub'][1],'--output',str(rows)],root)
        products = validate_price_manifest(manifest)
        for product, name in [('oil','brent'),('gas','henry_hub')]:
            if products[product]['response_sha256'] != downloaded[name][2]:
                raise ValueError('Price preparation differs from downloaded bytes')
        write_report(out/'price-manifest.json',manifest)
        report = normalized_report({'rows':manifest['row_count'],
                   'source_hashes':{k:v['response_sha256'] for k,v in products.items()}})
    elif args.stage == 'price-load':
        rows = scratch/'price.ndjson'
        receipt = run_json([python,str(root/'scripts/load_reference_prices.py'),'--rows',str(rows),
            '--manifest',str(rows.with_suffix('.manifest.json')),'--apply'],root)
        manifest = load_json(out/'price-manifest.json')
        if receipt.get('rows') != manifest['row_count'] or receipt.get('table') != f'{PROJECT}.{DATASET}.monthly_reference_price' or not receipt.get('job_id'):
            raise ValueError('Price load receipt differs')
        receipt['source_hashes'] = {k:v['response_sha256'] for k,v in validate_price_manifest(manifest).items()}
        receipt['rows_sha256'] = manifest['rows_sha256']
        write_report(out/'price-load.json',receipt)
        report = normalized_report(receipt)
    elif args.stage == 'artifact-check':
        assert_extract_artifact(artifact, history=history)
        # Only reviewed metadata crosses runner boundaries, never raw data.
        for name in ('source-evidence','source-manifest','source-load','price-manifest','price-load'):
            write_report(out/f'{name}.json',load_json(artifact/f'{name}.json'))
        configure_profile(out)
        report = normalized_report({'phase':'transform','candidate_period':CUTOFF})
    elif args.stage in ('raw-gate','raw-revalidate'):
        if history:
            report = run_json([python,str(root/'pipeline/check_raw_history.py'),'--artifact',str(out)],root)
        else:
            report = run_json([python,str(root/'extraction/scripts/check_raw_snapshot.py'),
            '--project',PROJECT,'--dataset',DATASET,'--resource-id',RESOURCE,'--year','2026','--month','8',
            '--evidence',str(out/'source-evidence.json'),'--max-bytes',str(BUDGET)],root)
        if report.get('status') != 'pass' or report.get('publication_approved') is not False:
            raise ValueError('Raw gate rejected')
    elif args.stage in ('loaded-lineage', 'loaded-revalidate'):
        report = run_json([python,str(root/'pipeline/verify_loaded_lineage.py'),
                           '--artifact',str(out)],root)
        if report.get('status') != 'pass' or report.get('publication_approved') is not False:
            raise ValueError('Warehouse content lineage rejected')
    elif args.stage.startswith('dbt-'):
        action = args.stage.removeprefix('dbt-')
        project = args.dbt_project_dir.resolve() if args.dbt_project_dir else root/'transform'
        command = ['source','freshness'] if action == 'source-freshness' else [action]
        argv = [args.dbt_bin,*command,'--project-dir',str(project),'--profiles-dir',str(out/'profiles'),
                '--target','candidate','--target-path',str(out/'dbt-target'),'--log-path',str(out/'dbt-logs'),
                '--vars',json.dumps({'candidate_period':CUTOFF,'enable_candidate_pricing':True,
                    **({'candidate_start_period':'2023-01-01','enable_dashboard_export':True} if history else {})})]
        if action == 'source-freshness':
            argv += ['--select','source:raw_cap4.produccion_pozo_mes','source:candidate_pricing.monthly_reference_price']
        if action in ('compile','build'):
            argv += ['--select',*SELECTION,*(['+fct_dashboard_month'] if history else [])]
        result = subprocess.run(argv,cwd=project,check=False)
        if result.returncode:
            raise ValueError('dbt stage failed')
        if action == 'source-freshness':
            freshness = load_json(out/'dbt-target/sources.json')
            if len(freshness.get('results',[])) != 2 or any(r['status'] != 'pass' for r in freshness['results']):
                raise ValueError('dbt source freshness must pass for both production and prices')
            write_report(out/'source-freshness.json',normalized_report({'results':[{k:r.get(k) for k in ('unique_id','status','max_loaded_at','snapshotted_at')} for r in freshness['results']]}))
        if action == 'build':
            raw = load_json(out/'dbt-target/run_results.json')
            results = [{k:r.get(k) for k in ('unique_id','status','execution_time')} for r in raw['results']]
            if not results or any(r['status'] not in ('success','pass') for r in results):
                raise ValueError('dbt result contains errors/skips/warnings')
            from report_dbt_performance import summarize, render
            performance = summarize(raw)
            write_report(out/'performance.json',performance)
            (out/'performance.html').write_text(render(performance))
            evidence = load_json(out/'source-evidence.json') if history else {}
            price = load_json(out/'price-manifest.json') if history else {}
            write_report(out/'dbt-summary.json',normalized_report({'results':results,
                **({'inputs':{'source_sha256':evidence['source_sha256'],
                             'price_rows_sha256':price['rows_sha256']}} if history else {})}))
        report = normalized_report({'action':action})
    else:
        raise ValueError('Unknown candidate stage')
    write_report(out/f'{args.stage}.gate.json',report)


def plan(args):
    stages = []
    extract = ['source-prepare','source-load','price-prepare','price-load','raw-gate','loaded-lineage']
    transform = ['artifact-check','raw-revalidate','loaded-revalidate','dbt-source-freshness','dbt-parse','dbt-compile','dbt-build']
    names = extract if args.phase == 'extract' else transform if args.phase == 'transform' else extract+transform
    for name in names:
        argv = [args.python,str(Path(__file__).resolve()),args.phase,'--repo',str(args.repo.resolve()),
                '--run-dir',str(args.run_dir.resolve()),'--scratch-dir',str(args.scratch_dir.resolve()),
                '--python',args.python,'--dbt-bin',args.dbt_bin,'--stage',name]
        if getattr(args, 'history', False):
            argv += ['--history']
        if getattr(args, 'source_inbound', None):
            argv += ['--source-inbound',str(args.source_inbound.resolve())]
        if args.extract_artifact:
            argv += ['--extract-artifact',str(args.extract_artifact.resolve())]
        if args.dbt_project_dir:
            argv += ['--dbt-project-dir',str(args.dbt_project_dir.resolve())]
        stages.append(Stage(name=name,argv=tuple(argv),cwd=args.repo.resolve(),
            timeout_seconds=1200 if name.startswith('dbt-') else 600,
            environment={'BIGQUERY_PROJECT':PROJECT,'BIGQUERY_LOCATION':'US','DBT_RAW_DATASET':DATASET,
                         'DBT_TARGET':'candidate','DBT_BQ_DATASET':'stg_cap4_candidate_dev',
                         'DBT_SEND_ANONYMOUS_USAGE_STATS':'false'},
            gate_report=args.run_dir.resolve()/f'{name}.gate.json'))
    return stages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['extract','transform','all'])
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--extract-artifact',type=Path)
    parser.add_argument('--scratch-dir',type=Path)
    parser.add_argument('--python',default=sys.executable)
    parser.add_argument('--dbt-bin',default='dbt')
    parser.add_argument('--dbt-project-dir',type=Path)
    parser.add_argument('--history',action='store_true',help='Explicit reviewed 2023-01 through 2026-08 history candidate')
    parser.add_argument('--source-inbound',type=Path,help='Retained official annual CSV bytes with original retrieval metadata')
    parser.add_argument('--stage',help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.phase == 'transform' and not args.extract_artifact:
        parser.error('transform requires --extract-artifact metadata directory')
    if args.scratch_dir is None:
        args.scratch_dir = Path(tempfile.mkdtemp(prefix='vm-candidate-'))
    else:
        args.scratch_dir.mkdir(parents=True,exist_ok=True)
    if args.stage:
        execute_stage(args)
        return 0
    report = run(plan(args),args.run_dir.resolve())
    print(json.dumps({'status':report['status'],'publication_approved':False,'run_directory':str(args.run_dir.resolve())}))
    return int(report['status'] != 'passed')


if __name__ == '__main__':
    raise SystemExit(main())
