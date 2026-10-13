"""Exercise the gate SQL locally with NULLs/duplicates; no cloud connection."""
from datetime import datetime, timezone, timedelta
import importlib.util
import json
import math
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('loaded_lineage',Path(__file__).parents[1]/'verify_loaded_lineage.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)


class CountIf:
    def __init__(self):self.n=0
    def step(self,value):self.n+=int(bool(value))
    def finalize(self):return self.n


class LineageTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
        self.time=datetime.now(timezone.utc).isoformat();self.sha='a'*64
        products = {}
        for product, (benchmark, unit, url, basis) in gate.REFERENCES.items():
            products[product] = dict(product=product,benchmark=benchmark,currency='USD',price_unit=unit,
                source_url=url,energy_basis=basis,response_sha256=self.sha,snapshot_id=self.sha,
                cutoff='2026-08-01',retrieved_at=self.time,source_updated_at=self.time[:10],row_count=2)
        self.price=dict(schema_version=2,products=products,cutoff='2026-08-01',retrieved_at=self.time,
            row_count=4,rows_sha256='c'*64,gas_valuation_enabled=True,
            gas_valuation_kind='international_reference_scenario')
        self.root.joinpath('source-evidence.json').write_text(json.dumps(dict(source_sha256=self.sha,year_rows=1)))
        self.write_price()
        self.db=sqlite3.connect(':memory:');self.addCleanup(self.db.close);self.db.row_factory=sqlite3.Row
        self.db.create_aggregate('COUNTIF',1,CountIf)
        self.db.create_function('IS_NAN',1,lambda v:False if v is None else math.isnan(v))
        self.db.create_function('IS_INF',1,lambda v:False if v is None else math.isinf(v))
        self.db.execute('create table production (_source_sha256 text)');self.db.execute('insert into production values (?)',[self.sha])
        self.db.execute('''create table prices (source_sha256 text,snapshot_id text,accepted_cutoff text,
            product text,benchmark text,currency text,price_unit text,energy_basis text,price real,
            periodo text,source_url text,source_updated_at text,retrieved_at text)''')
        for product, (benchmark, unit, url, basis) in gate.REFERENCES.items():
            for period in ['2026-01-01','2026-08-01']:
                self.db.execute('insert into prices values (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    [self.sha,self.sha,'2026-08-01',product,benchmark,'USD',unit,basis,91.08 if product=='oil' else 2.78,
                     period,url,self.time[:10],self.time])

    def write_price(self):self.root.joinpath('price-manifest.json').write_text(json.dumps(self.price))

    def verify(self):
        db=self.db
        class Parameter:
            def __init__(self,name,kind,value):self.name=name;self.value=value
        class Config:
            def __init__(self,**kwargs):self.__dict__.update(kwargs)
        class Client:
            def __init__(self,**kwargs):pass
            def query(self,sql,job_config):
                if job_config.maximum_bytes_billed!=1024**3 or job_config.use_query_cache:
                    raise AssertionError('Unbounded or cached query')
                sql=sql.replace('CAST(periodo AS STRING)', 'periodo')
                sql=sql.replace('`vaca-muerta-pulse.raw_cap4_candidate_dev.produccion_pozo_mes`','production')
                sql=sql.replace('`vaca-muerta-pulse.raw_cap4_candidate_dev.monthly_reference_price`','prices')
                params={p.name:(p.value.isoformat() if hasattr(p.value,'isoformat') else p.value) for p in job_config.query_parameters}
                result=dict(db.execute(sql,params).fetchone())
                return types.SimpleNamespace(job_id='fake-local',total_bytes_processed=100,result=lambda timeout:[result])
        module=types.ModuleType('google.cloud.bigquery');module.Client=Client;module.QueryJobConfig=Config;module.ScalarQueryParameter=Parameter
        cloud=types.ModuleType('google.cloud');cloud.bigquery=module
        google=types.ModuleType('google');google.cloud=cloud
        with patch.dict(sys.modules,{'google':google,'google.cloud':cloud,'google.cloud.bigquery':module}):
            return gate.verify(self.root)

    def test_valid_rows_pass_bounded_query(self):self.assertEqual(self.verify()['status'],'pass')

    def test_null_reference_fields_fail(self):
        for field in ['product','benchmark','currency','price_unit','source_url','source_updated_at','retrieved_at']:
            with self.subTest(field=field):
                self.db.execute('savepoint current_case');self.db.execute(f'update prices set {field}=NULL where periodo="2026-01-01"')
                self.assertEqual(self.verify()['status'],'fail');self.db.execute('rollback to current_case')

    def test_duplicate_month_fails_even_when_total_and_cutoff_match(self):
        self.db.execute('update prices set periodo="2026-02-01" where periodo="2026-01-01"')
        self.db.execute('insert into prices select * from prices where periodo="2026-02-01"')
        self.price['row_count']=6
        for product in self.price['products'].values(): product['row_count']=3
        self.write_price()
        result=self.verify();self.assertEqual(result['status'],'fail');self.assertEqual(result['results']['duplicate_price_period_rows'],2)

    def test_mismatched_retrieval_timestamp_fails(self):
        self.db.execute('update prices set retrieved_at="2026-01-01T00:00:00+00:00"')
        self.assertEqual(self.verify()['status'],'fail')

    def test_unknown_source_url_or_stale_manifest_fail_before_query(self):
        self.price['products']['gas']['source_url']='https://example.invalid/?sql=DROP';self.write_price()
        with self.assertRaisesRegex(ValueError,'source URL'):self.verify()
        self.price['products']['gas']['source_url']=gate.GAS_URL
        old=(datetime.now(timezone.utc)-timedelta(days=8)).isoformat()
        self.price['products']['gas']['retrieved_at']=old
        self.price['products']['gas']['source_updated_at']=old[:10];self.price['retrieved_at']=old;self.write_price()
        with self.assertRaisesRegex(ValueError,'stale'):self.verify()

    def test_missing_or_unreviewed_gas_basis_fails(self):
        for basis in [None,'MEASURED_VM']:
            with self.subTest(basis=basis):
                self.db.execute('update prices set energy_basis=? where product="gas"',[basis])
                self.assertEqual(self.verify()['status'],'fail')

    def test_oil_and_gas_same_calendar_month_do_not_duplicate(self):
        self.assertEqual(self.verify()['results']['duplicate_price_period_rows'],0)


if __name__=='__main__':unittest.main()
