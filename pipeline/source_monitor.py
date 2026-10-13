"""Observe public sources without warehouse writes or automatic month acceptance."""
import argparse
import copy
import csv
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import statistics
import sys
import tempfile
import re
from zoneinfo import ZoneInfo
from urllib.request import HTTPRedirectHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'extraction/scripts'), str(ROOT/'scripts')]
import source_history_pipeline as source
import import_brent
import import_henry_hub

VERSION = 1
POLICY = {'coverage_floor': 0.98, 'stable_hours': 48, 'fresh_hours': 36,
          'historical_full_days': 7, 'reference_months': 3, 'volume_ratio_min':0.5, 'volume_ratio_max':2.0}
# Arrival/user metadata and the optional surrogate id do not change product semantics.
EXCLUDED = {'fecha_data', 'idusuario', 'id'}
INTEGERS = {'anio', 'mes', 'idpozo', 'idusuario', 'id'}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def moment(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('Observation timestamp requires timezone')
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def canonical(row, contract, year):
    values = {}
    for name, kind in contract.items():
        value = row[name]
        if value is None:
            raise ValueError('CSV field missing')
        if kind == 'text':
            values[name] = value
        elif value == '':
            values[name] = None
        elif kind == 'numeric':
            number = Decimal(value)
            if not number.is_finite() or not math.isfinite(float(number)) or (name in INTEGERS and number != number.to_integral_value()):
                raise ValueError('Invalid numeric field')
            values[name] = str(number.normalize()) if number else '0'
        elif kind == 'timestamp':
            values[name] = datetime.fromisoformat(value).isoformat()
        else:
            raise ValueError('Unknown field type')
    y, m, well = (int(Decimal(values[k])) for k in ('anio', 'mes', 'idpozo'))
    if y != year or not 1 <= m <= 12 or well <= 0:
        raise ValueError('Invalid well/month grain')
    if values['prod_pet'] is None or values['prod_gas'] is None:
        raise ValueError('Missing production')
    return values, f'{y}-{m:02d}-01', well


def profile(csv_path, contract, year):
    """Bounded-memory row fingerprint sorting and distinct-well counts in private SQLite."""
    stats = {}
    with tempfile.TemporaryDirectory(prefix='vm-monitor-') as directory:
        database = sqlite3.connect(str(Path(directory)/'sort.sqlite'))
        database.execute('PRAGMA journal_mode=OFF'); database.execute('PRAGMA synchronous=OFF')
        database.execute('CREATE TABLE rows(period TEXT, hash TEXT, well INTEGER, vm INTEGER, oil_positive INTEGER, gas_positive INTEGER)')
        with csv_path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            header = reader.fieldnames or []
            extra = set(header)-set(contract)
            if len(set(header)) != len(header) or set(contract)-set(header) or extra not in (set(), {'id'} if year == 2024 else set()):
                raise ValueError('Source schema drift')
            for index, row in enumerate(reader, 1):
                if None in row or index > source.MAX_ROWS_YEAR:
                    raise ValueError('Malformed or oversized annual CSV')
                values, period, well = canonical(row, contract, year)
                vm = values['formacion'] == 'vaca muerta' and values['tipo_de_recurso'] == 'NO CONVENCIONAL'
                oil, gas = Decimal(values['prod_pet']), Decimal(values['prod_gas'])
                if vm and any(n < 0 for n in (oil, gas)):
                    raise ValueError('Negative production outside reviewed exception')
                current = stats.setdefault(period, {'rows': 0, 'vm_rows': 0, 'oil_m3': Decimal(0), 'gas_km3': Decimal(0), 'negative_fields_outside_product':0})
                current['rows'] += 1
                if not vm: current['negative_fields_outside_product'] += sum(n < 0 for n in (oil,gas))
                if vm:
                    current['vm_rows'] += 1; current['oil_m3'] += oil; current['gas_km3'] += gas
                fingerprint = digest({k:v for k,v in values.items() if k not in EXCLUDED})
                database.execute('INSERT INTO rows VALUES(?,?,?,?,?,?)',
                                 (period, fingerprint, well, int(vm), int(oil>0), int(gas>0)))
                if index % 10_000 == 0:
                    database.commit()
        if not stats:
            raise ValueError('Empty annual CSV')
        database.commit()
        hashes, vm_hashes = {}, {}
        for period, row_hash, vm in database.execute('SELECT period, hash, vm FROM rows ORDER BY period, hash'):
            hashes.setdefault(period, hashlib.sha256()).update(bytes.fromhex(row_hash))
            if vm: vm_hashes.setdefault(period, hashlib.sha256()).update(bytes.fromhex(row_hash))
        for period, count, wells, oil_wells, gas_wells in database.execute('''SELECT period, COUNT(*), COUNT(DISTINCT well),
            COUNT(DISTINCT CASE WHEN vm=1 AND oil_positive=1 THEN well END),
            COUNT(DISTINCT CASE WHEN vm=1 AND gas_positive=1 THEN well END) FROM rows GROUP BY period'''):
            stats[period].update(duplicate_rows=count-wells, oil_wells=oil_wells, gas_wells=gas_wells,
                                 fingerprint=hashes[period].hexdigest(),
                                 vm_fingerprint=vm_hashes.get(period, hashlib.sha256()).hexdigest())
        database.close()
    return {period:{k:str(v) if isinstance(v, Decimal) else v for k,v in values.items()}
            for period,values in sorted(stats.items())}


def read_state(path):
    if path.stat().st_size > 5*1024**2:
        raise ValueError('Monitor state exceeds metadata budget')
    state = json.loads(path.read_text())
    if state.get('schema_version') != VERSION or state.get('policy') != POLICY or state.get('publication_approved') is not False:
        raise ValueError('Monitor state contract/policy differs')
    for period, entry in state['periods'].items():
        datetime.strptime(period, '%Y-%m-%d')
        if not re.fullmatch(r'\d{4}-(0[1-9]|1[012])-01', period): raise ValueError('Invalid month')
        moment(entry['observed_at']); moment(entry['stable_since'])
        if entry['observations'] < 1 or len(entry['profile']['fingerprint']) != 64:
            raise ValueError('Invalid observation state')
    return state


def readiness(period, profile_value, previous, observed_at, as_of, periods, accepted, prices):
    reasons, ratios = [], {}
    current = moment(observed_at)
    if period >= as_of.astimezone(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('%Y-%m-01'):
        reasons.append('month_not_elapsed')
    if not 0 <= (as_of-current).total_seconds() <= POLICY['fresh_hours']*3600:
        reasons.append('observation_not_fresh')
    if profile_value['duplicate_rows']:
        reasons.append('duplicate_well_month')
    references = [p for p in sorted(accepted) if p < period and p in periods][-POLICY['reference_months']:]
    if len(references) < POLICY['reference_months']:
        reasons.append('insufficient_accepted_reference')
    else:
        for metric in ('rows', 'vm_rows', 'oil_wells', 'gas_wells'):
            denominator = statistics.median(periods[p]['profile'][metric] for p in references)
            ratios[metric] = profile_value[metric]/denominator if denominator else None
            if ratios[metric] is None or ratios[metric] < POLICY['coverage_floor']:
                reasons.append('coverage_'+metric)
    if len(references)==POLICY['reference_months']:
        for metric in ('oil_m3','gas_km3'):
            denominator=statistics.median(float(periods[p]['profile'][metric]) for p in references)
            ratio=float(profile_value[metric])/denominator if denominator else None
            ratios[metric]=ratio
            if ratio is None or not POLICY['volume_ratio_min']<=ratio<=POLICY['volume_ratio_max']:
                reasons.append('volume_outlier_'+metric)
    if not previous or previous['observations'] < 2 or (current-moment(previous['stable_since'])).total_seconds() < POLICY['stable_hours']*3600:
        reasons.append('stability_not_established')
    if any(period not in prices.get(fluid,{}) for fluid in ('oil','gas')):
        reasons.append('missing_monthly_reference_price')
    return {'status':'ready_for_review' if not reasons else 'observing', 'reasons':reasons, 'coverage_ratios':ratios,
            'official_completeness_verified':False, 'automatic_acceptance':False}


def compare(state, observations, prices, as_of):
    """Advance evidence only on genuinely newer recoveries; dedupe by semantic transition."""
    result = copy.deepcopy(state); events = []; evaluations = {}
    accepted = set(state['accepted_periods'])
    old_prices = state.get('prices', {})
    def event(kind, period, before, after, details):
        identifier = digest([kind, period, before, after])
        events.append({'id':identifier, 'kind':kind, 'period':period, 'details':details})
    for period, observed in sorted(observations.items()):
        fresh_profile = observed['profile']; timestamp = observed['observed_at']
        if moment(timestamp) > as_of or period > as_of.astimezone(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('%Y-%m-01'):
            raise ValueError('Future source observation or business month')
        previous = result['periods'].get(period)
        if previous and moment(timestamp) < moment(previous['observed_at']):
            raise ValueError('Source observation moves backwards')
        changed = previous and previous['profile']['fingerprint'] != fresh_profile['fingerprint']
        if changed and moment(timestamp) == moment(previous['observed_at']):
            raise ValueError('Different payload claims the same recovery')
        if changed and period in accepted:
            event('accepted_month_revised',period,previous['profile']['fingerprint'],fresh_profile['fingerprint'],
                  {'before':previous['profile'],'after':fresh_profile,'vm_changed':previous['profile']['vm_fingerprint']!=fresh_profile['vm_fingerprint']})
        if not previous and period not in accepted:
            event('new_month_observed', period, None, fresh_profile['fingerprint'], {'profile':fresh_profile})
        entry = {'profile':fresh_profile, 'observed_at':timestamp,
                 'stable_since':timestamp if not previous or changed else previous['stable_since'],
                 'previous_review_status':previous.get('review_status') if previous else None,
                 'observations':1 if not previous or changed else previous['observations']+int(moment(timestamp)>moment(previous['observed_at']))}
        result['periods'][period] = entry
        if fresh_profile['duplicate_rows']:
            event('source_quality_failure',period,None,fresh_profile['fingerprint'],{'reason':'duplicate_well_month'})
    for period, entry in sorted(result['periods'].items()):
        if period in accepted: continue
        evaluation = readiness(period,entry['profile'],entry,entry['observed_at'],as_of,{p:{'profile':v} for p,v in state['accepted_reference'].items()},accepted,prices)
        evaluations[period] = evaluation
        if entry.get('previous_review_status')=='ready_for_review' and evaluation['status']!='ready_for_review':
            event('month_readiness_withdrawn',period,None,digest([entry['profile']['fingerprint'],evaluation['reasons']]),evaluation)
        entry['review_status']=evaluation['status']
        entry.pop('previous_review_status',None)
        if evaluation['status'] == 'ready_for_review':
            event('month_ready_for_review',period,None,digest([entry['profile']['fingerprint'],{f:prices[f][period] for f in ('oil','gas')}]),evaluation)
    for fluid, old in old_prices.items():
        for period, price in old.items():
            if period in accepted and period not in prices.get(fluid,{}):
                event('accepted_price_missing',period,price,None,{'fluid':fluid,'before':price})
    for fluid, values in prices.items():
        for period, price in values.items():
            if period in accepted and period in old_prices.get(fluid,{}) and price != old_prices[fluid][period]:
                event('accepted_price_revised',period,old_prices[fluid][period],price,{'fluid':fluid,'before':old_prices[fluid][period],'after':price})
    result['prices'] = prices; result['updated_at'] = as_of.isoformat()
    return result, {'schema_version':VERSION,'observed_at':as_of.isoformat(),'policy':POLICY,
                    'events':events,'months':evaluations,'publication_approved':False}


def fetch_eia(parser):
    class Exact(HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            if newurl != parser.URL: raise ValueError('Unexpected EIA redirect')
            return super().redirect_request(request,fp,code,msg,headers,newurl)
    with build_opener(Exact()).open(parser.URL,timeout=30) as response:
        if response.url != parser.URL: raise ValueError('Unexpected EIA response URL')
        raw = response.read(5*1024**2+1)
    if len(raw)>5*1024**2: raise ValueError('EIA response exceeds budget')
    if parser is import_brent and (b'Europe Brent Spot Price FOB' not in raw or b'Dollars per Barrel' not in raw):
        raise ValueError('Wrong Brent series or unit')
    return parser.parse(raw)


def bootstrap(observations, release, prices):
    """Durable seed uses only months already accepted by the reviewed consumer."""
    accepted = sorted({r['periodo'] for r in release['production']})
    for row in release['production']:
        values = observations[row['periodo']]['profile']
        volume = float(Decimal(values['oil_m3'])*Decimal('6.28981077')) if row['fluid']=='oil' else float(Decimal(values['gas_km3'])/1000)
        if abs(volume-row['volume']) > max(1e-6, abs(volume)*1e-10) or values[row['fluid']+'_wells'] != row['positive_producing_wells']:
            raise ValueError('Monitoring seed differs from reviewed physical snapshot')
    return {'schema_version':VERSION,'policy':POLICY,'accepted_periods':accepted,
            'periods':{p:{**observations[p], 'stable_since':observations[p]['observed_at'], 'observations':1} for p in accepted},
            'prices':{f:{p:v for p,v in entries.items() if p in accepted} for f,entries in prices.items()},
            'accepted_reference':{p:observations[p]['profile'] for p in accepted},'years':{},'notified_event_ids':[], 'publication_approved':False}


def missing_profile():
    return {'rows':0,'vm_rows':0,'oil_m3':'0','gas_km3':'0','duplicate_rows':0,
            'oil_wells':0,'gas_wells':0,'fingerprint':hashlib.sha256(b'').hexdigest(),
            'vm_fingerprint':hashlib.sha256(b'').hexdigest(),'negative_fields_outside_product':0}


def collect(state, scratch, inbound=None, force=False):
    contract = json.loads((ROOT/'extraction/contracts/production_csv.json').read_text())
    observations, years, errors = {}, {}, []; now = datetime.now(timezone.utc)
    for year in source.RESOURCES:
        previous = state.get('years',{}).get(str(year))
        retrieval = None
        try:
            due = not previous or year == max(source.RESOURCES) or (now-moment(previous['observed_at'])).days >= POLICY['historical_full_days']
            if not due and not force and not inbound:
                current = source.read_metadata(year, build_opener(source.AnnualRedirect(year)))
                due = any(current.get(k)!=previous['metadata'].get(k) for k in ('id','url','size','last_modified'))
            if not due and not force and not inbound:
                observations.update({p: {'profile':v['profile'],'observed_at':v['observed_at']} for p,v in state['periods'].items() if p.startswith(str(year))})
                years[str(year)] = previous; continue
            if inbound:
                csv_path = inbound/f'{year}.csv'; retained=json.loads((inbound/f'{year}.retrieval.json').read_text())
                retrieval = source.normalize_retained(year,retained)
            else:
                csv_path = scratch/f'{year}.csv'; retrieval = source.retrieve(year,csv_path)
            source.validate_retrieval(year,csv_path,retrieval)
            values = profile(csv_path,contract,year)
            if any(p>now.astimezone(ZoneInfo('America/Argentina/Buenos_Aires')).strftime('%Y-%m-01') for p in values):
                raise ValueError('Future business month')
            for period in state.get('periods',{}):
                if period.startswith(str(year)) and period not in values: values[period]=missing_profile()
            observations.update({p: {'profile':v, 'observed_at':retrieval['downloaded_at']} for p,v in values.items()})
            years[str(year)] = {'observed_at':retrieval['downloaded_at'],
                                'metadata':{k:retrieval['after'].get(k) for k in ('id','url','size','last_modified')},
                                'csv_sha256':retrieval['sha256']}
        except Exception as error:
            if previous: years[str(year)]=previous
            errors.append({'year':year,'code':type(error).__name__,
                           'source_fingerprint':retrieval['sha256'] if retrieval else 'unavailable'})
    return observations, years, errors


def discover_resources(previous_ids=None):
    from urllib.parse import urlparse
    url='https://datos.energia.gob.ar/api/3/action/package_show?id='+source.PACKAGE
    class ExactPortal(HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            if newurl not in (url,url.replace('https://','http://',1)):
                raise ValueError('Unexpected catalogue redirect')
            return super().redirect_request(request,fp,code,msg,headers,newurl)
    with build_opener(ExactPortal()).open(url,timeout=30) as response:
        raw=response.read(5*1024**2+1)
    if len(raw)>5*1024**2:raise ValueError('Catalogue exceeds budget')
    data=json.loads(raw)
    if data.get('success') is not True:raise ValueError('Catalogue unavailable')
    events=[];observed_ids=[]
    for resource in data['result']['resources']:
        parsed=urlparse(resource.get('url',''))
        matched=re.fullmatch(r'/dataset/'+source.PACKAGE+r'/resource/([a-f0-9-]{36})/download/produccin-de-pozos-de-gas-y-petrleo-(\d{4})\.csv',parsed.path)
        if not matched or parsed.hostname!='datos.energia.gob.ar' or parsed.username or parsed.password or parsed.query:continue
        identifier,year=matched[1],int(matched[2])
        if year<min(source.RESOURCES):continue
        observed_ids.append(identifier)
        if previous_ids is not None and identifier not in previous_ids and source.RESOURCES.get(year)!=identifier:
            details={'year':year,'resource_id':identifier}
            events.append({'id':digest(['annual_resource_requires_review',details]),'kind':'annual_resource_requires_review',
                           'period':f'{year}-01-01','details':details})
    return events,sorted(set(observed_ids))


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    state = read_state(args.previous or ROOT/'pipeline/contracts/monitor-baseline.json') if not args.bootstrap else {'years':{}}
    if not args.bootstrap:
        seed=read_state(ROOT/'pipeline/contracts/monitor-baseline.json')
        state['accepted_periods']=seed['accepted_periods']
        state['accepted_reference']=seed['accepted_reference']
    with tempfile.TemporaryDirectory(prefix='vm-monitor-sources-') as temporary:
        observations, years, errors = collect(state,Path(temporary),args.inbound,args.full)
    if args.bootstrap:
        if errors:
            print(json.dumps({'bootstrap_errors':errors}))
            raise ValueError('Bootstrap source validation failed')
        prices = json.loads((ROOT/'apps/web/public/data/prices.json').read_text())
        quotes={'oil':{r['periodo']:r['usd_per_bbl'] for r in prices['prices']},
                'gas':{r['periodo']:r['usd_per_mmbtu'] for r in prices['gas']['prices']}}
        result = bootstrap(observations,json.loads((ROOT/'apps/web/public/data/release.json').read_text()),quotes)
        result['catalogue_resource_ids']=discover_resources()[1]
        report = {'schema_version':VERSION,'events':[],'status':'bootstrap_verified','publication_approved':False}
    else:
        quotes=copy.deepcopy(state['prices'])
        for fluid, parser, field in [('oil',import_brent,'usd_per_bbl'),('gas',import_henry_hub,'usd_per_mmbtu')]:
            try:
                parsed=fetch_eia(parser)
                quotes[fluid]={r['periodo']:r[field] for r in parsed['prices'] if r['periodo']>='2023-01-01'}
            except Exception as error:
                errors.append({'source':fluid,'code':type(error).__name__,'source_fingerprint':'unavailable'})
        catalogue_events=[]
        try:
            catalogue_events,catalogue_ids=discover_resources(state.get('catalogue_resource_ids',list(source.RESOURCES.values())))
            state['catalogue_resource_ids']=catalogue_ids
        except Exception as error: errors.append({'source':'catalogue','code':type(error).__name__,'source_fingerprint':'unavailable'})
        result, report = compare(state,observations,quotes,datetime.now(timezone.utc))
        report['events'].extend(catalogue_events)
        if errors:
            for evaluation in report['months'].values():
                evaluation['status']='observing';evaluation['reasons'].append('source_observation_failed')
            for period in report['months']:
                result['periods'][period]['review_status']='observing'
                if state['periods'].get(period,{}).get('review_status')=='ready_for_review':
                    report['events'].append({'id':digest(['month_readiness_withdrawn',period,errors]),'kind':'month_readiness_withdrawn','period':period,'details':report['months'][period]})
            report['events']=[e for e in report['events'] if e['kind']!='month_ready_for_review']
            for error in errors:
                report['events'].append({'id':digest(['source_observation_failed',error]),'kind':'source_observation_failed',
                                         'period':None,'details':error})
        report['status']='degraded' if errors or any(e['kind']=='source_quality_failure' for e in report['events']) else 'observed'
    result['years'] = years
    for name, value in [('state',result),('report',report)]:
        (args.output/f'{name}.json').write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    lines=['## Observación de fuentes', '', 'Estado: '+report['status']+'. No hay aceptación ni promoción automática.', '', '| Mes | Estado | Motivos |', '| --- | --- | --- |']
    for period, item in report.get('months',{}).items():
        lines.append('| '+period[:7]+' | '+item['status']+' | '+', '.join(item['reasons'])+' |')
    lines += ['', 'Novedades detectadas: '+str(len(report['events']))+'.']
    (args.output/'summary.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'status':report['status'],'events':len(report['events']),'publication_approved':False}))
    return report['status'] != 'degraded'


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--inbound',type=Path);parser.add_argument('--full',action='store_true')
    parser.add_argument('--bootstrap',action='store_true')
    raise SystemExit(not run(parser.parse_args()))
