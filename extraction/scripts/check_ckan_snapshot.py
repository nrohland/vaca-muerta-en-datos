#!/usr/bin/env python3
"""Bounded CKAN metadata/count preflight; no extraction, warehouse or publication writes."""
import argparse
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
BASE='https://datos.energia.gob.ar/api/3/action/'
REQUIRED={'idpozo','anio','mes','prod_pet','prod_gas'}

def action(name,parameters):
    with urlopen(BASE+name+'?'+urlencode(parameters),timeout=30) as response:
        result=json.load(response)
    if result.get('success') is not True:raise ValueError('CKAN action failed')
    return result['result']

def fingerprint(value):
    stable={key:value[key] for key in ('resource_id','year','month','year_rows','month_rows','resource_total','schema','source_last_modified')}
    return hashlib.sha256(json.dumps(stable,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def compare(before,after,evidence):
    failures=[]
    if before['source_sha256']!=after['source_sha256']:failures.append('source changed during extraction')
    for key in ('resource_id','year','year_rows','source_sha256','hash_scope'):
        if evidence.get(key)!=before[key]:failures.append('reviewed evidence differs: '+key)
    period=f"{before['year']:04}-{before['month']:02}-01"
    if evidence.get('month_rows',{}).get(period)!=before['month_rows'][period]:failures.append('reviewed monthly count differs')
    if evidence.get('coverage_status')!='reviewed_complete_snapshot' or period not in evidence.get('accepted_periods',[]):failures.append('month not technically accepted')
    return failures

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--resource-id',required=True);p.add_argument('--year',type=int,required=True);p.add_argument('--month',type=int,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--before',type=Path);p.add_argument('--evidence',type=Path,required=True)
    args=p.parse_args()
    if not 1<=args.month<=12:p.error('month1..12 required')
    meta=action('resource_show',{'id':args.resource_id})
    def rows(filters):
        return action('datastore_search',{'resource_id':args.resource_id,'limit':0,'filters':json.dumps(filters)})
    full=rows({});annual=rows({'anio':args.year});monthly=rows({'anio':args.year,'mes':args.month})
    schema=sorted([{'id':f['id'],'type':f['type']} for f in full['fields']],key=lambda f:f['id'])
    if not REQUIRED.issubset({f['id'] for f in schema}):raise ValueError('required source schema absent')
    if full['total']!=annual['total']:raise ValueError('resource is not the exact requested annual scope')
    period=f'{args.year:04}-{args.month:02}-01'
    observation={'resource_id':args.resource_id,'year':args.year,'month':args.month,'resource_total':full['total'],
      'year_rows':annual['total'],'month_rows':{period:monthly['total']},'schema':schema,'source_last_modified':meta.get('last_modified'),
      'extracted_at':datetime.now(timezone.utc).isoformat(),'hash_scope':'ckan_metadata_counts'}
    observation['source_sha256']=fingerprint(observation)
    evidence=json.loads(args.evidence.read_text())
    before=json.loads(args.before.read_text()) if args.before else observation
    failures=compare(before,observation,evidence)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(observation,indent=2))
    print(json.dumps({'status':'fail' if failures else 'pass','errors':failures,'publication_approved':False}))
    return int(bool(failures))
if __name__=='__main__':raise SystemExit(main())
