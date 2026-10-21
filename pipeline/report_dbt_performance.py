"""Summarize real dbt BigQuery metrics without exporting SQL or credentials."""
import argparse
from datetime import datetime
import html
import json
from pathlib import Path


def summarize(results):
    nodes=[]
    for r in results['results']:
        a=r.get('adapter_response') or {}
        nodes.append({'node':r['unique_id'],'status':r['status'],'seconds':r['execution_time'],
            'bytes_processed':a.get('bytes_processed'),'bytes_billed':a.get('bytes_billed'),
            'slot_ms':a.get('slot_ms'),'job_id':a.get('job_id'),
            'resource_type':r['unique_id'].split('.')[0]})
    timed=[t for r in results['results'] for t in r.get('timing',[]) if t.get('started_at') and t.get('completed_at')]
    wall=(max(datetime.fromisoformat(t['completed_at'].replace('Z','+00:00')) for t in timed)-
          min(datetime.fromisoformat(t['started_at'].replace('Z','+00:00')) for t in timed)).total_seconds() if timed else None
    totals={k:sum(n[k] for n in nodes if isinstance(n[k],(int,float))) for k in ['bytes_processed','bytes_billed','slot_ms']}
    return {'schema_version':1,'invocation_id':results['metadata']['invocation_id'],
        'wall_seconds':wall,'totals':totals,'node_count':len(nodes),
        'metrics_available':{k:sum(n[k] is not None for n in nodes) for k in totals},
        'models':[n for n in nodes if n['resource_type']=='model'],
        'slowest_nodes':sorted(nodes,key=lambda n:n['seconds'],reverse=True)[:15],
        'nodes':nodes,'limitations':['One execution, not a statistically comparable performance baseline.',
            'Missing adapter metrics remain null; totals include only reported values.',
            'Bytes billed are not a monetary charge; no pricing assumption is applied.',
            'A view CREATE with zero processed bytes does not measure its downstream query cost.']}


def budget_check(report, policy):
    query_nodes=[n for n in report['nodes'] if n['resource_type'] not in ['seed']]
    if any(n['bytes_billed'] is None for n in query_nodes):
        raise ValueError('Query billing metrics missing; budget cannot be verified')
    if report['totals']['bytes_billed']>policy['dbt_bytes_billed']:
        raise ValueError('dbt run exceeds 3 GiB billed-byte budget')
    if any(n['bytes_billed']>policy['query_bytes_billed'] for n in query_nodes):
        raise ValueError('A query exceeds billed-byte budget')
    return {'status':'pass','bytes_billed':report['totals']['bytes_billed'],
        'run_limit':policy['dbt_bytes_billed'],'query_limit':policy['query_bytes_billed'],
        'warnings':['Wall time exceeds advisory threshold'] if report['wall_seconds'] is not None and report['wall_seconds']>policy['wall_seconds_warning'] else [],
        'scope':'dbt run_results only; freshness, gates and export are separate',
        'enforcement':'acceptance after build; execution is guarded per query'}

def render(report):
    rows=''.join('<tr><td>'+html.escape(n['node'])+'</td><td>'+f"{n['seconds']:.2f}"+'</td><td>'+
        ('—' if n['bytes_processed'] is None else f"{n['bytes_processed']/1024**2:.2f}")+'</td><td>'+
        ('—' if n['slot_ms'] is None else str(n['slot_ms']))+'</td></tr>' for n in report['slowest_nodes'])
    notice='<p>Esta ejecución contiene errores o nodos omitidos; el reporte de rendimiento no equivale a aceptación.</p>' if any(n['status'] not in ['pass','success'] for n in report['nodes']) else ''
    return '<!doctype html><html lang="es"><meta charset="utf-8"><title>Rendimiento dbt · Vaca Muerta en Datos</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px;color:#173c4d;background:#f8fafa}table{border-collapse:collapse;width:100%;font-size:13px}td,th{text-align:left;padding:10px;border-bottom:1px solid #ccd9de}h1{font-size:28px}</style><h1>Rendimiento dbt histórico</h1>'+notice+'<p>Una ejecución real. El tiempo de cada nodo incluye trabajo del adaptador; slot-ms representa uso de cómputo, no duración de pared.</p><p>'+f"{report['node_count']} nodos · tiempo de pared {str(round(report['wall_seconds'],1)) if report['wall_seconds'] is not None else 'sin dato'} s · {report['totals']['bytes_processed']/1024**3:.3f} GiB procesados reportados"+'</p><table><tr><th>Nodo</th><th>Segundos</th><th>MiB procesados</th><th>Slot-ms</th></tr>'+rows+'</table><p>No hay comparación estadística con ejecuciones anteriores. Las métricas ausentes no se interpretan como cero. Bytes facturables no equivalen a un costo monetario.</p></html>'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-results',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=summarize(json.loads(a.run_results.read_text()));a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'performance.json').write_text(json.dumps(r,indent=2)+'\n');(a.output/'performance.html').write_text(render(r))
    print(json.dumps({'nodes':r['node_count'],'wall_seconds':r['wall_seconds'],'totals':r['totals']}))
