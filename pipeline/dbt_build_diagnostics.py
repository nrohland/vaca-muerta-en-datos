"""Bounded read-only budget readiness and reduced dbt failures; no SQL in reports."""
import json
from pathlib import Path
import re
import time


def await_budget(estimate, output, limit, *, timeout=300, interval=15,
                 clock=time.monotonic, sleep=time.sleep):
    started=clock()
    report={'status':'fail','publication_approved':False,'limit_bytes':limit,'attempts':[]}
    while True:
        try:
            value=estimate()
            if type(value) is not int or value<0:raise ValueError('Missing estimate')
        except Exception:
            report['failure']='estimate_unavailable'
            output.write_text(json.dumps(report,indent=2)+'\n')
            raise ValueError('Cannot verify staging scan budget') from None
        elapsed=clock()-started
        report['attempts'].append({'estimated_bytes':value,'elapsed_seconds':round(elapsed,3)})
        if value<=limit:
            report['status']='pass'
        elif elapsed>=timeout:
            report['failure']='estimated_scan_exceeds_budget'
        output.write_text(json.dumps(report,indent=2)+'\n')
        if report['status']=='pass':return report
        if 'failure' in report:raise ValueError('Staging scan still exceeds unchanged query budget')
        # Retry only dry runs. Never submit or retry a table write here.
        sleep(min(interval,timeout-elapsed))


def check_staging_budget(run_dir, project, limit):
    from google.cloud import bigquery
    compiled=run_dir/'dbt-target/compiled/vaca_muerta_pulse/models/staging/stg_produccion_pozo_mes.sql'
    sql=compiled.read_text()
    client=bigquery.Client(project=project,location='US')
    def estimate():
        job=client.query(sql,job_config=bigquery.QueryJobConfig(dry_run=True,use_query_cache=False))
        return job.total_bytes_processed
    return await_budget(estimate,run_dir/'dbt-build-readiness.json',limit)


def failure_report(target, returncode):
    report={'status':'fail','publication_approved':False,'returncode':returncode,'nodes':[]}
    try:raw=json.loads((target/'run_results.json').read_text())
    except (OSError,ValueError):
        report['failure']='dbt_results_unavailable'
        return report
    for result in raw.get('results',[]):
        node=result.get('unique_id','')
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,512}',node):continue
        status=result.get('status')
        if status in ('pass','success'):continue
        entry={'node':node,'status':status if status in ('error','fail','skipped','warn') else 'unknown'}
        message=result.get('message') or ''
        if 'Query exceeded limit for bytes billed' in message:
            entry['reason']='bytes_billed_limit_exceeded'
            match=re.search(r'bytes billed:\s*(\d+)\.\s*(\d+) or higher required',message)
            if match:entry.update(limit_bytes=int(match[1]),required_bytes=int(match[2]))
        elif 'Access Denied' in message or 'Permission denied' in message:
            entry['reason']='access_denied'
        else:entry['reason']='dbt_node_failed'
        report['nodes'].append(entry)
    return report
