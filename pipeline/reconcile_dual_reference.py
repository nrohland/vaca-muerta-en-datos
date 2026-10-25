"""Independent read-only August reconciliation of source volume, dual prices and UI.
Fixed candidate tables; aggregate output only, 1 GiB query budget.
"""
import json
from pathlib import Path
from decimal import Decimal, localcontext
from google.cloud import bigquery

ROOT = Path(__file__).resolve().parents[1]
PERIOD = '2026-08-01'
BASIS = 'EIA_US_AVERAGE_1036_BTU_PER_CUBIC_FOOT_SCENARIO_V1'
query = """WITH physical AS (
 SELECT COUNT(*) n, SUM(prod_gas_km3) gas_km3, SUM(prod_pet_m3) oil_m3
 FROM `vaca-muerta-pulse.marts_cap4_candidate_dev.fct_well_month` WHERE periodo=@period
), prices AS (
 SELECT COUNTIF(product='gas') gas_n, COUNTIF(product='oil') oil_n,
 MAX(IF(product='gas',price,NULL)) hh, MAX(IF(product='oil',price,NULL)) brent
 FROM `vaca-muerta-pulse.raw_cap4_candidate_dev.monthly_reference_price` WHERE periodo=@period
), well AS (
 SELECT COUNT(*) n, COUNT(DISTINCT well_month_id) distinct_wells,
 SUM(gas_reference_value_usd) gas_usd, SUM(oil_reference_value_usd) oil_usd,
 COUNTIF(NOT gas_valuation_available OR gas_reference_value_usd IS NULL
   OR gas_energy_basis != @basis OR gas_valuation_method != 'estimated_reference_scenario'
   OR NOT gas_energy_is_scenario) invalid_gas
 FROM `vaca-muerta-pulse.marts_cap4_candidate_dev.fct_reference_valuation_month` WHERE periodo=@period
), entity AS (
 SELECT entity_type, SUM(gas_reference_value_usd) gas_usd, SUM(oil_reference_value_usd) oil_usd,
 COUNTIF(gas_reference_ytd_usd IS NOT NULL OR gas_reference_mom_change_usd IS NOT NULL
   OR gas_reference_yoy_change_usd IS NOT NULL) invented_history
 FROM `vaca-muerta-pulse.marts_cap4_candidate_dev.fct_reference_valuation_entity_month`
 WHERE periodo=@period GROUP BY entity_type
)
SELECT entity.entity_type,physical.n physical_wells,physical.gas_km3,physical.oil_m3,
 prices.hh,prices.brent,prices.gas_n,prices.oil_n,well.n valued_wells,well.distinct_wells,
 well.gas_usd,well.oil_usd,well.invalid_gas,entity.invented_history,
 entity.gas_usd-well.gas_usd gas_entity_error,
 entity.oil_usd-well.oil_usd oil_entity_error FROM physical CROSS JOIN prices CROSS JOIN well CROSS JOIN entity"""
client=bigquery.Client(project='vaca-muerta-pulse',location='US')
job=client.query(query,job_config=bigquery.QueryJobConfig(maximum_bytes_billed=1024**3,use_query_cache=False,
 query_parameters=[bigquery.ScalarQueryParameter('period','DATE',PERIOD),bigquery.ScalarQueryParameter('basis','STRING',BASIS)]))
rows=[dict(r) for r in job.result(timeout=120)]
release=json.loads((ROOT/'apps/web/public/data/release.json').read_text())
ui_prices=json.loads((ROOT/'apps/web/public/data/prices.json').read_text())
ui_volume=next(r['volume'] for r in release['production'] if r['fluid']=='gas' and r['periodo']==PERIOD)
ui_price=next(r['usd_per_mmbtu'] for r in ui_prices['gas']['prices'] if r['periodo']==PERIOD)
with localcontext() as context:
 context.prec=50
 factor=Decimal(1036)/Decimal('0.028316846592')/Decimal(1000000)
 first=rows[0]
 expected_gas=float(Decimal(str(first['gas_km3']))*Decimal(1000)*factor*Decimal(str(first['hh'])))
 expected_oil=float(Decimal(str(first['oil_m3']))*Decimal('6.28981077')*Decimal(str(first['brent'])))
 ui_estimate=float(Decimal(str(ui_volume))*Decimal(1000000)*factor*Decimal(str(ui_price)))
def close(actual,expected):
 return actual is not None and abs(actual-expected)<=max(1e-7,abs(expected)*1e-10)
passed={r['entity_type'] for r in rows}=={'basin','company','area'}
for r in rows:
 passed=passed and r['gas_n']==1 and r['oil_n']==1 and r['hh']==2.78 and r['brent']==91.08
 passed=passed and r['physical_wells']==r['valued_wells']==r['distinct_wells'] and r['invalid_gas']==0 and r['invented_history']==0
 passed=passed and close(r['gas_usd'],expected_gas) and close(r['oil_usd'],expected_oil)
 passed=passed and abs(r['gas_entity_error'])<=max(1e-7,abs(expected_gas)*1e-10) and abs(r['oil_entity_error'])<=max(1e-7,abs(expected_oil)*1e-10)
 # Independent aggregations of FLOAT64 need tolerance relative to the total.
 passed=passed and close(r['gas_usd'],ui_estimate)
result={'status':'pass' if passed else 'fail','period':PERIOD,'job_id':job.job_id,'bytes_processed':job.total_bytes_processed,
 'expected_gas_reference_usd':expected_gas,'ui_gas_reference_usd':ui_estimate,'expected_oil_reference_usd':expected_oil,
 'basis':BASIS,'method':'independent Decimal calculation from declared source volumes and official same-month references',
 'results':rows,'publication_approved':False}
print(json.dumps(result));raise SystemExit(not passed)
