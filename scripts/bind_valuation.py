"""Bind the monthly price artifact to exact reviewed production release bytes."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from datetime import datetime, timezone
p=argparse.ArgumentParser();p.add_argument('--data-dir',type=Path,required=True);a=p.parse_args();d=a.data_dir
manifest=json.loads((d/'manifest.json').read_text());r=(d/'release.json').read_bytes();prices=(d/'prices.json').read_bytes();price=json.loads(prices)
assert hashlib.sha256(r).hexdigest()==manifest['data_sha256']
assert price['schema_version']==1 and price['source']['unit']=='USD/bbl' and price['source']['provider']=='EIA'
seen=set()
for row in price['prices']:
 assert re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])-01', row['periodo']) and row['periodo'] not in seen and type(row['usd_per_bbl']) in (int,float) and math.isfinite(row['usd_per_bbl']) and row['usd_per_bbl']>0;seen.add(row['periodo'])
missing=[p for p in manifest['source']['accepted_periods'] if p not in seen]
gas=price.get('gas',{})
assert gas.get('status')=='available' and gas.get('interpretation')=='reference_scenario'
assert gas['source']['provider']=='EIA' and gas['source']['unit'].upper()=='USD/MMBTU'
assert gas['source']['frequency']=='monthly' and gas['source']['url']=='https://www.eia.gov/dnav/ng/hist/rngwhhdm.htm'
conversion=gas['conversion']; factor=1036/0.028316846592/1e6
assert conversion['energy_basis']=='EIA_US_AVERAGE_1036_BTU_PER_CUBIC_FOOT_SCENARIO_V1'
assert conversion['interpretation']=='scenario' and conversion['btu_per_cubic_foot']==1036
assert math.isfinite(conversion['m3_to_mmbtu']) and abs(conversion['m3_to_mmbtu']-factor)<1e-12
assert conversion['source_url']=='https://www.eia.gov/energyexplained/units-and-calculators/energy-conversion-calculators.php'
gas_seen=set()
for row in gas['prices']:
 assert re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])-01',row['periodo']) and row['periodo'] not in gas_seen
 assert type(row['usd_per_mmbtu']) in (int,float) and math.isfinite(row['usd_per_mmbtu']) and row['usd_per_mmbtu']>0
 gas_seen.add(row['periodo'])
missing_gas=[p for p in manifest['source']['accepted_periods'] if p not in gas_seen]
(d/'valuation-manifest.json').write_text(json.dumps({'schema_version':1,'status':'candidate','release_sha256':manifest['data_sha256'],'prices_sha256':hashlib.sha256(prices).hexdigest(),'generated_at':datetime.now(timezone.utc).isoformat(),'missing_oil_price_periods':missing,'missing_gas_price_periods':missing_gas,'method':'Oil: monthly bbl × same-month EIA Brent USD/bbl. Gas: reported m3 × reference-scenario MMBtu/m3 × same-month EIA Henry Hub USD/MMBtu; daily = monthly value / calendar days. Estimated reference values, not realized revenues or measured VM gas energy.','gas_status':'available','gas_valuation_kind':'international_reference_scenario','energy_basis':conversion['energy_basis'],'m3_to_mmbtu':factor,'reference_sources':{'oil':price['source'],'gas':gas['source']},'publication_approved':False},ensure_ascii=False,indent=2)+'\n')
print('Bound price history; missing accepted oil/gas periods:',missing,missing_gas)
