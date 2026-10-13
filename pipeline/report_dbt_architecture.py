"""Report evaluator findings from a local metadata-only DuckDB audit."""
import argparse
import json
from pathlib import Path
import re


def report(database, results, manifest):
    if not results.get('results') or not any(r['unique_id'].startswith('model.dbt_project_evaluator.') for r in results['results']):
        raise ValueError('A real evaluator run is required; an empty audit cannot pass')
    import duckdb
    connection=duckdb.connect(str(database),read_only=True)
    findings=[]
    for r in results['results']:
        if r['status']!='warn':continue
        node=manifest['nodes'][r['unique_id']];details=[]
        for parent in node['depends_on']['nodes']:
            if not parent.startswith('model.dbt_project_evaluator.'):continue
            model=manifest['nodes'][parent];schema=model['schema'];table=model['alias']
            if schema!='stg_cap4_candidate_dev' or not re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',table):
                raise ValueError('Only local evaluator metadata tables can be reported')
            rows=connection.execute(f'SELECT * FROM "{schema}"."{table}" LIMIT 100').fetchall()
            columns=[c[0] for c in connection.description]
            details.append({'rule_model':table,'findings':[dict(zip(columns,row)) for row in rows]})
        findings.append({'test':node['name'],'failures':r.get('failures'),'details':details})
    connection.close()
    return {'status':'completed_with_advisories' if findings else 'pass',
        'package':'dbt-labs/dbt_project_evaluator','execution':'local DuckDB graph metadata; not a BigQuery runtime benchmark',
        'invocation_id':results['metadata']['invocation_id'],
        'passed':sum(r['status'] in ['pass','success'] for r in results['results']),
        'warnings':findings,'errors':sum(r['status']=='error' for r in results['results'])}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True);p.add_argument('--run-results',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();v=report(a.database,json.loads(a.run_results.read_text()),json.loads(a.manifest.read_text()))
    a.output.write_text(json.dumps(v,indent=2,default=str)+'\n')
    print(json.dumps({'passed':v['passed'],'warnings':len(v['warnings']),'errors':v['errors']}))
