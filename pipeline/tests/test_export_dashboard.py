import importlib.util
from pathlib import Path
import unittest
import hashlib
import copy
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
from datetime import date,datetime,timezone

path=Path(__file__).resolve().parents[1]/'export_dashboard.py'
spec=importlib.util.spec_from_file_location('export_dashboard',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ExportDashboard(unittest.TestCase):
 def revision_fixture(self):
  records=[dict(well_id=164323,company_id='PAL',area_id='APO',periodo=f'{year}-{month:02d}-01',gas_delta_million_m3=1.0) for year in (2024,2025) for month in range(1,13)]
  base={'production':[],'entities':[]}
  for r in records:
   for dimension,entity_id in [('basin','vaca_muerta'),('company','PAL'),('area','APO')]:
    anchor=dict(fluid='gas',periodo=r['periodo'],dimension=dimension,entity_id=entity_id,volume=10.,rate=1.,positive_producing_wells=2)
    base['production' if dimension=='basin' else 'entities'].append(anchor)
  data=module.json_bytes(base);source={'sources':[{'year':2024,'source_sha256':'a'*64}],'source_sha256':'b'*64}
  revision=dict(status='pass',well_id=164323,prior_baseline_sha256=hashlib.sha256(data).hexdigest(),reviewed_source_sha256='b'*64,csv_source_hashes={'2024':'a'*64},prior_classification='CONVENCIONAL',official_csv_classification='NO CONVENCIONAL',reclassified_well_volume_changed=False,gas_difference_MMm3={'2024':12.,'2025':12.},records=records)
  return data,revision,source
 def test_reviewed_membership_correction_is_exact_and_preserves_baseline(self):
  data,revision,source=self.revision_fixture();base=module.reviewed_baseline(data,revision,source)
  self.assertEqual(base['production'][0]['volume'],11.)
  self.assertEqual(base['production'][0]['positive_producing_wells'],3)
  self.assertEqual(__import__('json').loads(data)['production'][0]['volume'],10.)
 def test_unrelated_revision_or_changed_input_is_rejected(self):
  data,revision,source=self.revision_fixture()
  for field,value in [('prior_baseline_sha256','c'*64),('reviewed_source_sha256','c'*64),('reclassified_well_volume_changed',True)]:
   bad=copy.deepcopy(revision);bad[field]=value
   with self.assertRaises(ValueError):module.reviewed_baseline(data,bad,source)
  bad=copy.deepcopy(revision);bad['records'][0]['gas_delta_million_m3']=2.
  with self.assertRaisesRegex(ValueError,'annual'):module.reviewed_baseline(data,bad,source)
 def test_assignment_changes_conserve_volume_and_reject_unrelated_revisions(self):
  data,_,source=self.revision_fixture();base={'production':[],'entities':[]};transfers=[]
  for m in range(1,13):
   period=f'2025-{m:02d}-01'
   for fluid in ('oil','gas'):
    for id in ('AVI','MBE','LTAC'):
     base['entities'].append(dict(fluid=fluid,periodo=period,dimension='area',entity_id=id,volume=10.,rate=1.,positive_producing_wells=5))
   for old,new,count in [('AVI','AVN',2),('MBE','MBE1',2),('LTAC','LTII',3),('LTAC','LTI',1)]:
    transfers.append(dict(periodo=period,old_area_id=old,new_area_id=new,old_company_id='YPF',new_company_id='YPF',well_months=count,changed_volumes=0,oil_volume=1.,gas_volume=1.,oil_positive_wells=1,gas_positive_wells=1))
  revision=dict(status='pass',job_id='read-job',prior_baseline_sha256=hashlib.sha256(data).hexdigest(),source_sha256=source['source_sha256'],transfers=transfers)
  actual=module.reviewed_assignments(base,revision,data,source)
  self.assertEqual(sum(r['volume'] for r in actual['entities']),sum(r['volume'] for r in base['entities']))
  bad=copy.deepcopy(revision);bad['transfers'][0]['new_company_id']='PAL'
  with self.assertRaises(ValueError):module.reviewed_assignments(base,bad,data,source)
 def test_current_dbt_baseline_does_not_reapply_migration(self):
  base={'schema_version':1,'status':'candidate','valuation':{'producer':'dbt','model':'fct_dashboard_month'},'production':[],'entities':[]}
  data=module.json_bytes(base);manifest={'data_sha256':hashlib.sha256(data).hexdigest(),'source':{'accepted_periods':['2026-08-01']}}
  source={'accepted_periods':['2026-08-01']}
  self.assertEqual(module.baseline_for_export(data,manifest,source),base)
  with self.assertRaisesRegex(ValueError,'binding'):module.baseline_for_export(data+b' ',manifest,source)
  with self.assertRaisesRegex(ValueError,'together'):module.baseline_for_export(data,manifest,source,revision={})
  legacy=module.json_bytes({**base,'valuation':{}});manifest['data_sha256']=hashlib.sha256(legacy).hexdigest()
  with self.assertRaisesRegex(ValueError,'reviewed dbt'):module.baseline_for_export(legacy,manifest,source)

 def test_prices_are_exported_from_exact_loaded_rows_without_revaluation(self):
  from verify_loaded_lineage import REFERENCES
  stamp=datetime.now(timezone.utc).isoformat();rows=[];products={}
  for product,(benchmark,unit,url,basis) in REFERENCES.items():
   rows.append(dict(product=product,periodo='2026-08-01',benchmark=benchmark,price=2.78 if product=='gas' else 91.08,currency='USD',price_unit=unit,source_url=url,source_sha256='a'*64,source_updated_at=stamp[:10],retrieved_at=stamp,accepted_cutoff='2026-08-01',snapshot_id='a'*64,energy_basis=basis))
   products[product]=dict(product=product,benchmark=benchmark,price_unit=unit,source_url=url,energy_basis=basis,currency='USD',cutoff='2026-08-01',retrieved_at=stamp,source_updated_at=stamp[:10],row_count=1,response_sha256='a'*64,snapshot_id='a'*64)
  checksum=hashlib.sha256(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows).encode()).hexdigest()
  manifest=dict(schema_version=2,cutoff='2026-08-01',gas_valuation_enabled=True,gas_valuation_kind='international_reference_scenario',products=products,row_count=2,retrieved_at=stamp,rows_sha256=checksum)
  asset=module.price_asset(list(reversed(rows)),manifest)
  self.assertEqual(asset['gas']['source']['unit'],'USD/MMBtu')
  self.assertEqual(asset['prices'][0]['usd_per_bbl'],91.08);self.assertEqual(asset['gas']['prices'][0]['usd_per_mmbtu'],2.78)
  module.verify_quotes([{'fluid':'oil','periodo':date(2026,8,1),'price_usd_per_unit':91.08}],asset)
  with self.assertRaisesRegex(ValueError,'Mart quote'):
   module.verify_quotes([{'fluid':'oil','periodo':date(2026,8,1),'price_usd_per_unit':90.}],asset)
  rows[0]['price']=1
  with self.assertRaisesRegex(ValueError,'exact extraction'):module.price_asset(rows,manifest)

 def rows(self):
  rows=[]
  for fluid in ['oil','gas']:
   for dimension,id in [('basin','vaca_muerta'),('company','A'),('area','X')]:
    rows.append(dict(dimension=dimension,entity_id=id,entity_name=id,fluid=fluid,periodo='2026-08-01',volume=10.0,rate=10/31,positive_producing_wells=2,coverage=1,is_complete=True,acceptance_basis='approved_complete_snapshot',estimated_value_usd=100.0,estimated_daily_value_usd=100/31,mom_estimated_value_usd=None,yoy_estimated_value_usd=None,estimated_ytd_value_usd=None,yoy_estimated_ytd_value_usd=None,price_usd_per_unit=10.0,price_unit='USD/bbl' if fluid=='oil' else 'USD/MMBtu',energy_basis=None if fluid=='oil' else module.ENERGY_BASIS,valuation_method='estimated_reference' if fluid=='oil' else 'estimated_reference_scenario'))
  return rows
 def run_export(self,rows):
  baseline={'production':[dict(r) for r in self.rows() if r['dimension']=='basin'],'entities':[dict(r) for r in self.rows() if r['dimension']!='basin']}
  return module.prepare(rows,baseline,{'source':{'accepted_periods':['2026-08-01']}},{})
 def test_preserves_zero_and_null_without_price_math(self):
  rows=self.rows()
  for r in rows:r['estimated_value_usd']=None;r['estimated_daily_value_usd']=None
  result=self.run_export(rows)
  self.assertTrue(all(r['estimated_value_usd'] is None and r['valuation_method']=='unavailable' for r in result['production']))
 def test_no_browser_or_python_revaluation(self):
  result=self.run_export(self.rows());self.assertEqual(result['valuation']['producer'],'dbt');self.assertEqual(result['production'][0]['estimated_value_usd'],100)
 def test_duplicate_rejected(self):
  rows=self.rows();rows.append(dict(rows[0]))
  with self.assertRaisesRegex(ValueError,'Duplicate'):self.run_export(rows)
 def test_physical_anchor_changed_rejected(self):
  rows=self.rows();rows[0]['volume']=11
  with self.assertRaisesRegex(ValueError,'Physical anchor'):self.run_export(rows)
 def test_invented_energy_basis_rejected(self):
  rows=self.rows();rows[-1]['energy_basis']='invented'
  with self.assertRaisesRegex(ValueError,'Unknown energy'):self.run_export(rows)
 def test_partial_history_rejected(self):
  with self.assertRaisesRegex(ValueError,'Incomplete basin'):self.run_export(self.rows()[1:])
 def test_money_entity_reconciliation_rejected(self):
  rows=self.rows();rows[1]['estimated_value_usd']=99
  with self.assertRaisesRegex(ValueError,'Value reconciliation'):self.run_export(rows)
 def test_invalid_monetary_nan_rejected(self):
  rows=self.rows();rows[0]['estimated_value_usd']=float('nan')
  with self.assertRaisesRegex(ValueError,'Invalid mart number'):self.run_export(rows)
 def test_missing_value_field_rejected(self):
  rows=self.rows();del rows[0]['estimated_value_usd']
  with self.assertRaisesRegex(ValueError,'Missing warehouse'):self.run_export(rows)
 def test_wrong_price_unit_rejected(self):
  rows=self.rows();rows[0]['price_unit']='USD/MMBtu'
  with self.assertRaisesRegex(ValueError,'monetary unit'):self.run_export(rows)
 def test_unknown_valuation_method_rejected(self):
  rows=self.rows();rows[0]['valuation_method']='estimated_sales'
  with self.assertRaisesRegex(ValueError,'monetary method'):self.run_export(rows)
 def test_null_value_with_daily_value_rejected(self):
  rows=self.rows();rows[0]['estimated_value_usd']=None
  with self.assertRaisesRegex(ValueError,'availability'):self.run_export(rows)
 def test_available_value_with_null_price_rejected(self):
  rows=self.rows();rows[0]['price_usd_per_unit']=None
  with self.assertRaisesRegex(ValueError,'availability'):self.run_export(rows)
 def test_unknown_grain_rejected(self):
  rows=self.rows();rows[0]['dimension']='province'
  with self.assertRaisesRegex(ValueError,'Unknown dashboard grain'):self.run_export(rows)
if __name__=='__main__':unittest.main()
