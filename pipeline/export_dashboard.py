"""Export a technically accepted dbt candidate to a private review directory.

Payload reads the mart only; bounded raw lineage aggregates stay in the warehouse.
No browser price arithmetic, external upload, approval or promotion.
Physical baseline anchors are independently checked before replacing any asset.
"""
import argparse
import csv
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import shutil
import calendar
import copy
import subprocess
from pathlib import Path

PROJECT = 'vaca-muerta-pulse'
TABLE = PROJECT + '.marts_cap4_candidate_dev.fct_dashboard_month'
ENERGY_BASIS = 'EIA_US_AVERAGE_1036_BTU_PER_CUBIC_FOOT_SCENARIO_V1'
FACTOR = 1036 / 0.028316846592 / 1e6
KEYS = ['estimated_value_usd','estimated_daily_value_usd','mom_estimated_value_usd',
        'yoy_estimated_value_usd','estimated_ytd_value_usd','yoy_estimated_ytd_value_usd','price_usd_per_unit','price_unit','energy_basis','valuation_method']

def normalized(value):
    if isinstance(value, (date, datetime)): return value.isoformat()
    if isinstance(value, Decimal): return float(value)
    if isinstance(value, dict): return {k:normalized(v) for k,v in value.items()}
    if isinstance(value, (tuple,list)): return [normalized(v) for v in value]
    return value

def row_key(row):
    return (row['fluid'],row['periodo'],row.get('dimension','basin'),row.get('entity_id','vaca_muerta'))

def prepare(rows, baseline, manifest, grouping):
    accepted = manifest['source']['accepted_periods']
    if not accepted or len(set(accepted)) != len(accepted): raise ValueError('Invalid accepted periods')
    values = {}; production=[]; entities=[]
    for raw in rows:
        r=normalized(dict(raw))
        if r.get('fluid') not in ('oil','gas') or r.get('dimension') not in ('basin','company','area'):
            raise ValueError('Unknown dashboard grain')
        key=row_key(r)
        if key in values or r['periodo'] not in accepted: raise ValueError('Duplicate or unaccepted mart row')
        if r.get('coverage') != 1 or r.get('is_complete') is not True or r.get('acceptance_basis') != 'approved_complete_snapshot': raise ValueError('Unaccepted coverage')
        if not all(k in r for k in KEYS): raise ValueError('Missing warehouse valuation')
        for k in ['volume','rate','estimated_value_usd','estimated_daily_value_usd','mom_estimated_value_usd','yoy_estimated_value_usd','estimated_ytd_value_usd','yoy_estimated_ytd_value_usd','price_usd_per_unit']:
            if r[k] is not None and (not isinstance(r[k],(int,float)) or not math.isfinite(r[k]) or r[k]<0): raise ValueError('Invalid mart number')
        if r['energy_basis'] != (ENERGY_BASIS if r['fluid']=='gas' else None): raise ValueError('Unknown energy scenario')
        if r['price_unit'] != ('USD/bbl' if r['fluid']=='oil' else 'USD/MMBtu'): raise ValueError('Invalid monetary unit')
        available_method='estimated_reference' if r['fluid']=='oil' else 'estimated_reference_scenario'
        if r['valuation_method'] not in (available_method,'unavailable'): raise ValueError('Unknown monetary method')
        if r['estimated_value_usd'] is None:
            if r['estimated_daily_value_usd'] is not None: raise ValueError('Inconsistent monetary availability')
            r['valuation_method']='unavailable'
        elif r['valuation_method'] != available_method or r['estimated_daily_value_usd'] is None or r['price_usd_per_unit'] is None or r['price_usd_per_unit'] <= 0:
            raise ValueError('Inconsistent monetary availability')
        values[key]=r
        if r['dimension']=='basin':
            for k in ['dimension','entity_id','entity_name','operator_group_rule_version','legal_operator_provenance','name_periodo','volume_rank','is_absent_current','yoy_contribution_selected','yoy_rest_rate_delta','top5_share_pct','yoy_top5_share_pct','top5_share_yoy_pp']:r.pop(k,None)
            production.append(r)
        else:
            r['source_name']=r['entity_name']
            if r['dimension']=='area':r['legal_operator_provenance']=[];r['operator_group_rule_version']=None
            entities.append(r)
    if {(r['fluid'],r['periodo']) for r in production} != {(f,p) for f in ['oil','gas'] for p in accepted}: raise ValueError('Incomplete basin history')
    # Review snapshot provides accepted physical anchors, never monetary values.
    for anchor in [*baseline['production'],*baseline['entities']]:
        actual=values.get(row_key(anchor))
        if actual is None: raise ValueError('Missing physical anchor')
        for k in ['volume','rate']:
            if not math.isclose(actual[k],anchor[k],rel_tol=1e-10,abs_tol=1e-8): raise ValueError('Physical anchor differs: '+str(row_key(anchor))+'/'+k)
        if actual['positive_producing_wells']!=anchor['positive_producing_wells']:raise ValueError('Well anchor differs')
    for fluid in ['oil','gas']:
        for period in accepted:
            basin=values[(fluid,period,'basin','vaca_muerta')]
            for dimension in ['company','area']:
                es=[r for r in entities if r['fluid']==fluid and r['periodo']==period and r['dimension']==dimension]
                if not es or not math.isclose(sum(r['volume'] for r in es),basin['volume'],rel_tol=1e-10,abs_tol=1e-8):raise ValueError('Entity reconciliation differs')
                available=all(r['estimated_value_usd'] is not None for r in es)
                if available != (basin['estimated_value_usd'] is not None):raise ValueError('Entity availability differs')
                if available and not math.isclose(sum(r['estimated_value_usd'] for r in es),basin['estimated_value_usd'],rel_tol=1e-10,abs_tol=1e-6):raise ValueError('Value reconciliation differs')
    return {**({'map':baseline['map']} if 'map' in baseline else {}),'schema_version':1,'status':'candidate','production':sorted(production,key=lambda r:(r['fluid'],r['periodo'])),
            'entities':sorted(entities,key=lambda r:(r['dimension'],r['fluid'],r['entity_id'],r['periodo'])),
            'operator_grouping':grouping,
            'valuation':{'schema_version':1,'producer':'dbt','model':'fct_dashboard_month',
                         'energy_basis_scenario':ENERGY_BASIS,'m3_to_mmbtu_scenario':FACTOR}}

def json_bytes(value): return (json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def reviewed_baseline(baseline_bytes, revision, source):
    """Apply only the independently evidenced well 164323 membership correction."""
    hashes = {str(s['year']):s['source_sha256'] for s in source['sources']}
    expected = {f'{y}-{m:02d}-01' for y in (2024,2025) for m in range(1,13)}
    records = revision.get('records', [])
    if (revision.get('status') != 'pass' or revision.get('well_id') != 164323
        or revision.get('prior_baseline_sha256') != hashlib.sha256(baseline_bytes).hexdigest()
        or revision.get('reviewed_source_sha256') != source['source_sha256']
        or revision.get('csv_source_hashes') != hashes
        or len(records) != 24 or {r['periodo'] for r in records} != expected
        or revision.get('prior_classification') != 'CONVENCIONAL'
        or revision.get('official_csv_classification') != 'NO CONVENCIONAL'
        or revision.get('reclassified_well_volume_changed') is not False):
        raise ValueError('Unreviewed baseline revision')
    base = json.loads(baseline_bytes)
    lookup = {row_key(r):r for r in [*base['production'],*base['entities']]}
    for record in records:
        delta = record['gas_delta_million_m3']
        if (record['well_id'] != 164323 or record['company_id'] != 'PAL' or record['area_id'] != 'APO'
            or type(delta) not in (int,float) or not math.isfinite(delta) or delta <= 0):
            raise ValueError('Invalid reviewed membership')
        period = record['periodo']; days = calendar.monthrange(int(period[:4]),int(period[5:7]))[1]
        for dimension, entity_id in [('basin','vaca_muerta'),('company','PAL'),('area','APO')]:
            anchor = lookup.get(('gas',period,dimension,entity_id))
            if anchor is None: raise ValueError('Missing revision anchor')
            anchor['volume'] += delta
            anchor['rate'] = anchor['volume']/days
            anchor['positive_producing_wells'] += 1
    for year in (2024,2025):
        if not math.isclose(sum(r['gas_delta_million_m3'] for r in records if r['periodo'].startswith(str(year))),
                            revision['gas_difference_MMm3'][str(year)],rel_tol=1e-12,abs_tol=1e-9):
            raise ValueError('Reviewed annual membership delta differs')
    return base

def current_manifest(template, source, receipt, summary, commit):
    result = copy.deepcopy(template)
    result['status'] = 'candidate'; result['publication_approved'] = False
    result['input_sha256'] = dict(summary['inputs'])
    result['source'] = {
        'data_kind':'official', 'approved_period':source['cutoff'],
        'accepted_periods':source['accepted_periods'], 'accepted_at':datetime.now(timezone.utc).isoformat(),
        'commit':commit, 'ingested_at':receipt['loaded_at'], 'published_at':None,
        'raw_candidate':receipt['destination'], 'bundle_sha256':source['source_sha256'],
        'acceptance_note':'Technical validation of 44 complete available-record months; owner promotion approval separate. September 2026 excluded.',
        'snapshot_revisions_note':'Official annual CSV history. Includes 24 reviewed well 164323 gas memberships in 2024–2025 and 96 well-month area ID revisions in 2025; unchanged physical well volumes. Other baseline anchors reconciled.',
        'resources':[{'id':s['resource_id'],'year':s['year'],'url':s['source_url'],
            'sha256':s['source_sha256'],'hash_scope':'original official CSV bytes',
            'extracted_at':s['extracted_at'],'raw_rows':s['year_rows'],'period_rows':s['month_rows']}
            for s in source['sources']]}
    return result

def reviewed_assignments(base, revision, baseline_bytes, source):
    transfers=revision.get('transfers',[])
    if (revision.get('status') != 'pass' or not revision.get('job_id')
        or revision.get('prior_baseline_sha256') != hashlib.sha256(baseline_bytes).hexdigest()
        or revision.get('source_sha256') != source['source_sha256']
        or len(transfers) != 48 or sum(t['well_months'] for t in transfers) != 96):
        raise ValueError('Unreviewed area assignment revision')
    base=copy.deepcopy(base);lookup={row_key(r):r for r in base['entities']}
    seen=set()
    for t in transfers:
        key=(t['periodo'],t['old_area_id'],t['new_area_id'])
        if (key in seen or not t['periodo'].startswith('2025-') or t['changed_volumes'] != 0
            or t['old_company_id'] != t['new_company_id']
            or (t['old_area_id'],t['new_area_id']) not in [('AVI','AVN'),('MBE','MBE1'),('LTAC','LTII'),('LTAC','LTI')]):
            raise ValueError('Unexpected assignment revision')
        seen.add(key)
        days=calendar.monthrange(2025,int(t['periodo'][5:7]))[1]
        for fluid in ('oil','gas'):
            delta=t[fluid+'_volume'];count=t[fluid+'_positive_wells']
            if not math.isfinite(delta) or delta<0 or type(count) is not int or not 0<=count<=t['well_months']:
                raise ValueError('Invalid assignment metric')
            for entity_id,sign in [(t['old_area_id'],-1),(t['new_area_id'],1)]:
                k=(fluid,t['periodo'],'area',entity_id);anchor=lookup.get(k)
                if anchor is None:
                    if sign<0:raise ValueError('Missing original area anchor')
                    anchor=dict(fluid=fluid,periodo=t['periodo'],dimension='area',entity_id=entity_id,volume=0.,rate=0.,positive_producing_wells=0)
                    lookup[k]=anchor;base['entities'].append(anchor)
                anchor['volume']+=sign*delta;anchor['rate']=anchor['volume']/days
                anchor['positive_producing_wells']+=sign*count
    return base

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--operator-seed',type=Path,default=Path(__file__).resolve().parents[1]/'transform/seeds/operator_groups.csv');p.add_argument('--dbt-summary',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--extract-artifact',type=Path,required=True)
    p.add_argument('--revision',type=Path,required=True)
    p.add_argument('--assignment-revision',type=Path,required=True)
    a=p.parse_args();summary=json.loads(a.dbt_summary.read_text())
    results=summary.get('results',[])
    if summary.get('status')!='pass' or not results or any(r.get('status') not in ('pass','success') for r in results) or not any(r.get('unique_id')=='model.vaca_muerta_pulse.fct_dashboard_month' for r in results):raise ValueError('Current dbt dashboard build must pass')
    from run_candidate import assert_extract_artifact
    from verify_loaded_lineage import verify
    source=assert_extract_artifact(a.extract_artifact,history=True)
    price=json.loads((a.extract_artifact/'price-manifest.json').read_text())
    if summary.get('inputs') != {'source_sha256':source['source_sha256'],'price_rows_sha256':price['rows_sha256']}:
        raise ValueError('Stale dbt input lineage')
    lineage=verify(a.extract_artifact)
    if lineage['status'] != 'pass': raise ValueError('Loaded source lineage differs')
    base=reviewed_baseline(a.baseline.read_bytes(),json.loads(a.revision.read_text()),source)
    base=reviewed_assignments(base,json.loads(a.assignment_revision.read_text()),a.baseline.read_bytes(),source)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).resolve().parents[1],text=True).strip()
    manifest=current_manifest(json.loads(a.manifest.read_text()),source,json.loads((a.extract_artifact/'source-load.json').read_text()),summary,commit)
    # Imported only after inputs pass, literal isolated table and read-only SELECT.
    from google.cloud import bigquery
    client=bigquery.Client(project=PROJECT,location='US');cfg=bigquery.QueryJobConfig(maximum_bytes_billed=1024**3)
    job=client.query(f'SELECT * FROM `{TABLE}` ORDER BY fluid,dimension,entity_id,periodo',job_config=cfg)
    rows=list(job.result())
    grouping=dict(base['operator_grouping']);seed=a.operator_seed.read_bytes();mappings=list(csv.DictReader(seed.decode().splitlines()))
    if len(mappings)!=2 or any(not any(all(old.get(k)==m[k] for k in m) for old in grouping['mappings']) for m in mappings):raise ValueError('Grouping seed differs from reviewed mapping')
    grouping['seed_sha256']=hashlib.sha256(seed).hexdigest()
    release=prepare(rows,base,manifest,grouping);data=json_bytes(release);sha=hashlib.sha256(data).hexdigest()
    manifest['data_sha256']=sha;manifest['generated_at']=datetime.now(timezone.utc).isoformat();manifest['version']=f"candidate-dbt-{sha[:12]}";manifest['valuation']={'producer':'dbt','model':'fct_dashboard_month','job_id':job.job_id}
    a.output.mkdir(parents=True,exist_ok=False)
    if 'map' in base:
        ref=base['map']['index'];relative=Path(ref['path'])
        if relative.is_absolute() or '..' in relative.parts or relative.parts[0]!='map':raise ValueError('Invalid map path')
        index=a.baseline.parent/relative;asset=index.read_bytes()
        if len(asset)!=ref['bytes'] or hashlib.sha256(asset).hexdigest()!=ref['sha256']:raise ValueError('Map baseline binding differs')
        shutil.copytree(a.baseline.parent/'map',a.output/'map')
    (a.output/'release.json').write_bytes(data);(a.output/'manifest.json').write_bytes(json_bytes(manifest))
    receipt={'status':'pass','publication_approved':False,'table':TABLE,'job_id':job.job_id,'bytes_processed':job.total_bytes_processed,'rows':len(rows),'data_sha256':sha,'physical_anchor_check':'pass','value_reconciliation':'pass','loaded_lineage':lineage,'inputs':summary['inputs'],'reviewed_membership_corrections':24}
    (a.output/'export-receipt.json').write_bytes(json_bytes(receipt));print(json.dumps(receipt))
if __name__=='__main__':main()
