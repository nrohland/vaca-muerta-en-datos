"""Read-only sandbox guard. Billing must stay disabled; never changes IAM or quotas."""
import argparse
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
PROJECT='vaca-muerta-pulse'
STORAGE_BUDGET=8*1024**3
MONTHLY_QUERY_BUDGET=int(.8*1024**4)


def assess(billing, tables, jobs, *, monthly_complete):
    if billing is not False: raise ValueError('No-cost policy requires verified billingEnabled=false')
    storage=sum(t.get('logical_bytes') or 0 for t in tables)
    if storage>STORAGE_BUDGET: raise ValueError('Accessible storage exceeds 8 GiB operating budget')
    usage=sum(j.get('bytes_billed') or 0 for j in jobs if j.get('statement_type')!='SCRIPT')
    if monthly_complete and usage>MONTHLY_QUERY_BUDGET: raise ValueError('Monthly query usage exceeds 80% operating budget')
    return {'status':'pass','billing_enabled':False,'storage_logical_bytes':storage,
        'storage_scope':'datasets accessible to the current identity; not quota remaining',
        'query_bytes_billed':usage,'monthly_inventory_complete':monthly_complete,
        'warnings':[] if monthly_complete else ['Global monthly usage unavailable; not interpreted as zero.'],
        'expiring_within_14_days':[t for t in tables if t.get('expires') and
          datetime.fromisoformat(t['expires'])<datetime.now(timezone.utc)+timedelta(days=14)],
        'publication_approved':False}


def inspect():
    import google.auth
    from google.auth.transport.requests import AuthorizedSession
    from google.cloud import bigquery
    credentials,_=google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    response=AuthorizedSession(credentials).get(f'https://cloudbilling.googleapis.com/v1/projects/{PROJECT}/billingInfo',timeout=30)
    if not response.ok: raise ValueError('Cannot verify disabled billing; refusing warehouse stages')
    billing=response.json().get('billingEnabled')
    # Reject before any query/load. Tables and jobs below are metadata API calls only.
    if billing is not False: raise ValueError('No-cost policy requires verified billingEnabled=false')
    client=bigquery.Client(project=PROJECT,credentials=credentials,location='US');tables=[]
    for dataset in client.list_datasets(timeout=30):
        for item in client.list_tables(dataset.reference,timeout=30):
            t=client.get_table(item.reference,timeout=30)
            tables.append({'table':f'{t.dataset_id}.{t.table_id}','logical_bytes':t.num_bytes,
                          'expires':t.expires.isoformat() if t.expires else None})
    jobs=[];complete=False
    try:
        start=datetime.now(timezone.utc).replace(day=1,hour=0,minute=0,second=0,microsecond=0)
        inventory=list(client.list_jobs(all_users=True,min_creation_time=start,max_results=10000,page_size=1000,timeout=30))
        complete=len(inventory)<10000
        for j in inventory:
            if j.job_type=='query':
                if not j.error_result and j.total_bytes_billed is None and j.state=='DONE':complete=False
                jobs.append({'bytes_billed':j.total_bytes_billed,'statement_type':j.statement_type})
    except Exception:
        # A least-privilege identity may not read all users' jobs. Billing-off remains mandatory.
        complete=False
    return assess(billing,tables,jobs,monthly_complete=complete)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=inspect();a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
