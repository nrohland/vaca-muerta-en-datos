"""Safe failure report when observation cannot produce evidence; preserve the last state."""
import argparse
import hashlib
import json
from pathlib import Path

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--previous',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(exist_ok=True,parents=True)
    # Never advance timestamps or assert that a failed check found no changes.
    state=json.loads(a.previous.read_text())
    event={'id':hashlib.sha256(b'source-monitor-execution-failed-v1').hexdigest(),
           'kind':'source_observation_failed','period':None,'details':{'code':'execution_failed'}}
    (a.output/'state.json').write_text(json.dumps(state,indent=2)+'\n')
    (a.output/'report.json').write_text(json.dumps({'status':'degraded','events':[event],'months':{},'publication_approved':False},indent=2)+'\n')
    (a.output/'summary.md').write_text('## No se pudo observar la fuente\n\nNo se actualizó la evidencia de frescura ni se certifica ausencia de novedades. Revisar la ejecución.\n')
