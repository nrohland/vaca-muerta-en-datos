"""Read-only sandbox guard. Billing must stay disabled; never changes IAM or quotas."""
import argparse
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
PROJECT='vaca-muerta-pulse'
STORAGE_BUDGET=8*1024**3
MONTHLY_QUERY_BUDGET=int(.8*1024**4)


class PreflightFailure(Exception):
    def __init__(self, phase, *, http_status=None, api_status=None, api_reason=None):
        self.details={'phase':phase}
        if isinstance(http_status,int):self.details['http_status']=http_status
        if api_status in {'PERMISSION_DENIED','UNAUTHENTICATED','NOT_FOUND','RESOURCE_EXHAUSTED','UNAVAILABLE'}:
            self.details['api_status']=api_status
        if api_reason in {'SERVICE_DISABLED','ACCESS_TOKEN_SCOPE_INSUFFICIENT','IAM_PERMISSION_DENIED','BILLING_DISABLED','CONSUMER_INVALID'}:
            self.details['api_reason']=api_reason
        super().__init__('Resource preflight blocked')


def checked(phase, operation):
    try:return operation()
    except Exception as error:
        # Do not serialize exception messages, requests, headers or response bodies.
        raise PreflightFailure(phase,http_status=getattr(error,'code',None)) from None


def run_check(output, inspector=None):
    try:
        report=(inspector or inspect)()
    except Exception as error:
        report={'status':'fail','publication_approved':False,
                'failure':error.details if isinstance(error,PreflightFailure) else {'phase':'unclassified'}}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return 0 if report.get('status')=='pass' else 1


def assess(billing, tables, jobs, *, monthly_complete):
    if billing is not False: raise ValueError('No-cost policy requires verified billingEnabled=false')
    storage=sum(t.get('logical_bytes') or 0 for t in tables)
    if storage>STORAGE_BUDGET: raise ValueError('Accessible storage exceeds 8 GiB operating budget')
    usage=sum(j.get('bytes_billed') or 0 for j in jobs if j.get('statement_type')!='SCRIPT')
    if monthly_complete and usage>MONTHLY_QUERY_BUDGET: raise ValueError('Monthly query usage exceeds 80% operating budget')
    return {'status':'pass','billing_enabled':False,'storage_logical_bytes':storage,
        'storage_scope':'datasets accessible to the current identity; not quota remaining',
        'query_bytes_billed':usage if monthly_complete else None,
        'query_bytes_observed':usage if jobs else None,'monthly_inventory_complete':monthly_complete,
        'warnings':[] if monthly_complete else ['Global monthly usage unavailable; not interpreted as zero.'],
        'expiring_within_14_days':[t for t in tables if t.get('expires') and
          datetime.fromisoformat(t['expires'])<datetime.now(timezone.utc)+timedelta(days=14)],
        'publication_approved':False}


def inspect():
    import google.auth
    from google.auth.transport.requests import AuthorizedSession
    from google.cloud import bigquery
    credentials,_=checked('credentials',lambda:google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform']))
    response=checked('billing-request',lambda:AuthorizedSession(credentials).get(f'https://cloudbilling.googleapis.com/v1/projects/{PROJECT}/billingInfo',timeout=30))
    if not response.ok:
        try:failure=response.json().get('error',{})
        except ValueError:failure={}
        reason=next((d.get('reason') for d in failure.get('details',[]) if isinstance(d,dict) and d.get('reason')),None)
        raise PreflightFailure('billing-verification',http_status=response.status_code,
                               api_status=failure.get('status'),api_reason=reason)
    billing=response.json().get('billingEnabled')
    # Reject before any query/load. Tables and jobs below are metadata API calls only.
    if billing is not False: raise PreflightFailure('billing-not-verified-disabled')
    client=bigquery.Client(project=PROJECT,credentials=credentials,location='US');tables=[]
    for dataset in checked('dataset-inventory',lambda:list(client.list_datasets(timeout=30))):
        for item in checked('table-inventory',lambda:list(client.list_tables(dataset.reference,timeout=30))):
            t=checked('table-metadata',lambda:client.get_table(item.reference,timeout=30))
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
    return checked('operating-budget',lambda:assess(billing,tables,jobs,monthly_complete=complete))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    raise SystemExit(run_check(a.output))
