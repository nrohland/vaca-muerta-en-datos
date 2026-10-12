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
        self.price=dict(response_sha256=self.sha,source_url=gate.PRICE_URL,cutoff='2026-08-01',
                        retrieved_at=self.time,source_updated_at=self.time[:10],row_count=2)
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
        for period in ['2026-01-01','2026-08-01']:
            self.db.execute('insert into prices values (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                [self.sha,self.sha,'2026-08-01','oil','EIA_BRENT_MONTHLY','USD','bbl',None,91.08,
                 period,gate.PRICE_URL,self.time[:10],self.time])

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
        self.price['row_count']=3;self.write_price()
        result=self.verify();self.assertEqual(result['status'],'fail');self.assertEqual(result['results']['duplicate_price_period_rows'],1)

    def test_mismatched_retrieval_timestamp_fails(self):
        self.db.execute('update prices set retrieved_at="2026-01-01T00:00:00+00:00"')
        self.assertEqual(self.verify()['status'],'fail')

    def test_unknown_source_url_or_stale_manifest_fail_before_query(self):
        self.price['source_url']='https://example.invalid/?sql=DROP';self.write_price()
        with self.assertRaisesRegex(ValueError,'source URL'):self.verify()
        self.price['source_url']=gate.PRICE_URL;self.price['retrieved_at']=(datetime.now(timezone.utc)-timedelta(days=8)).isoformat()
        self.price['source_updated_at']=self.price['retrieved_at'][:10];self.write_price()
        with self.assertRaisesRegex(ValueError,'chronology'):self.verify()


if __name__=='__main__':unittest.main()
