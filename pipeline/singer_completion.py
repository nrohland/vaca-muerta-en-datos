"""Summarize both certified Singer loads; never promote tables or publish snapshots."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re


def completion(run_id, root=Path('.local/singer')):
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,47}',run_id):
        raise ValueError('Invalid run ID')
    result={}
    for kind,directory,prefix in [('cap4',root/run_id,'produccion_pozo_mes_singer_'),
            ('reference_prices',root/'prices'/run_id,'monthly_reference_price_singer_')]:
        tap=json.loads((directory/'tap-complete.json').read_text())
        target=json.loads((directory/'target-complete.json').read_text())
        stream=prefix+run_id
        if (tap.get('run_id')!=run_id or target.get('run_id')!=run_id
            or tap.get('stream')!=stream
            or target.get('destination')!='vaca-muerta-pulse.raw_cap4_candidate_dev.'+stream
            or target.get('status')!='loaded_isolated_candidate' or target.get('method')!='batch_job'
            or tap.get('publication_approved') is not False or target.get('publication_approved') is not False
            or type(target.get('rows')) is not int or target['rows']<=0
            or tap.get('rows')!=target['rows'] or tap['evidence']['total_rows']!=target['rows']
            or not re.fullmatch('[a-f0-9]{64}',target.get('record_sha256',''))
            or tap.get('record_sha256')!=target['record_sha256']
            or tap['evidence']['source_sha256']!=target.get('source_sha256')):
            raise ValueError('Both same-run isolated loads must be certified')
        stamp=datetime.fromisoformat(target['completed_at'])
        if stamp.tzinfo is None or not 0<=(datetime.now(timezone.utc)-stamp).total_seconds()<=86400:
            raise ValueError('Load completion is stale or in the future')
        result[kind]={key:target[key] for key in ('destination','rows','source_sha256','record_sha256')}
    return {'run_id':run_id,'status':'ingested_isolated_candidates','loads':result,
            'transformation_executed':False,'publication_approved':False}


if __name__=='__main__':
    print(json.dumps(completion(os.environ.get('VM_RUN_ID','')),sort_keys=True))
