import argparse
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import run_candidate as candidate


class CandidateCLITests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name)

    def args(self, phase='transform'):
        return argparse.Namespace(phase=phase,python=sys.executable,repo=self.path,run_dir=self.path/'run',
            scratch_dir=self.path/'scratch',extract_artifact=self.path/'extract',dbt_bin='/legitimate/dbt',dbt_project_dir=None)

    def artifacts(self):
        path=self.path/'extract'; path.mkdir()
        stamp=datetime.now(timezone.utc).isoformat(); sha='a'*64
        values={
          'source-evidence':dict(resource_id=candidate.RESOURCE,year=2026,hash_scope='official_csv_bytes',
            coverage_status='reviewed_complete_snapshot',accepted_periods=[f'2026-{m:02d}-01' for m in range(1,9)],
            source_sha256=sha,year_rows=10,extracted_at=stamp),
          'source-manifest':dict(status='pass',sha256_csv=sha),
          'source-load':dict(status='pass',source_sha256=sha,rows=10,
            destination=f'{candidate.PROJECT}.{candidate.DATASET}.produccion_pozo_mes',publication_approved=False),
          'price-manifest':dict(schema_version=2,cutoff=candidate.CUTOFF,gas_valuation_enabled=True,
             gas_valuation_kind='international_reference_scenario',row_count=828,retrieved_at=stamp,
             rows_sha256='c'*64,products={
                k:dict(product=k,benchmark=ref[0],currency='USD',price_unit=ref[1],source_url=ref[2],energy_basis=ref[3],
                  cutoff=candidate.CUTOFF,retrieved_at=stamp,source_updated_at=stamp[:10],row_count=472 if k=='oil' else 356,
                  response_sha256='b'*64,snapshot_id='b'*64)
                for k,ref in __import__('verify_loaded_lineage').REFERENCES.items()}),
          'price-load':dict(table=f'{candidate.PROJECT}.{candidate.DATASET}.monthly_reference_price',rows=828,job_id='job',
                           source_hashes={'oil':'b'*64,'gas':'b'*64},rows_sha256='c'*64)}
        for name,value in values.items():path.joinpath(name+'.json').write_text(json.dumps(value))
        return path

    def test_transform_never_plans_a_load_or_download(self):
        stages=candidate.plan(self.args())
        self.assertEqual([s.name for s in stages],['artifact-check','raw-revalidate','loaded-revalidate','dbt-source-freshness','dbt-parse','dbt-compile','dbt-build'])
        self.assertTrue(all(s.environment['DBT_RAW_DATASET']==candidate.DATASET for s in stages))

    def test_history_stage_argument_survives_every_subprocess(self):
        args=self.args('all');args.history=True;args.source_inbound=self.path/'inbound'
        stages=candidate.plan(args)
        self.assertTrue(all('--history' in s.argv for s in stages))
        self.assertTrue(all('--source-inbound' in s.argv for s in stages))

    def test_history_transform_exports_only_after_successful_build(self):
        args=self.args();args.history=True
        stages=candidate.plan(args)
        self.assertEqual([s.name for s in stages][-3:],['dbt-build','dashboard-export','snapshot-check'])
        calls=[]
        def execute(argv,**kwargs):
            name=argv[argv.index('--stage')+1];calls.append(name)
            if name=='dbt-build':return subprocess.CompletedProcess(argv,1)
            (args.run_dir/(name+'.gate.json')).write_text(json.dumps({'status':'pass','publication_approved':False}))
            return subprocess.CompletedProcess(argv,0)
        self.assertEqual(candidate.run(stages,args.run_dir,execute=execute)['status'],'failed')
        self.assertNotIn('dashboard-export',calls)

    def test_export_failure_does_not_reach_frontend_contract(self):
        args=self.args('export');args.history=True;args.transform_artifact=self.path/'accepted-dbt'
        stages=candidate.plan(args);self.assertEqual([s.name for s in stages],['artifact-check','dashboard-export','snapshot-check'])
        calls=[]
        def execute(argv,**kwargs):
            name=argv[argv.index('--stage')+1];calls.append(name)
            if name=='dashboard-export':return subprocess.CompletedProcess(argv,1)
            (args.run_dir/(name+'.gate.json')).write_text(json.dumps({'status':'pass','publication_approved':False}))
            return subprocess.CompletedProcess(argv,0)
        self.assertEqual(candidate.run(stages,args.run_dir,execute=execute)['status'],'failed')
        self.assertNotIn('snapshot-check',calls)

    def test_prepare_is_public_only_and_load_is_separate_without_dbt(self):
        self.assertEqual([s.name for s in candidate.plan(self.args('prepare'))],['source-prepare','price-prepare'])
        args=self.args('load');args.prepared_artifact=self.path/'prepared'
        stages=candidate.plan(args)
        self.assertEqual([s.name for s in stages],['prepared-check','source-load','price-load','raw-gate','loaded-lineage'])
        self.assertTrue(all('--prepared-artifact' in s.argv for s in stages))

    def test_single_annual_artifact_is_not_accepted_as_history(self):
        path=self.artifacts()
        with self.assertRaises((ValueError, KeyError)):
            candidate.assert_extract_artifact(path,history=True)

    def test_extract_never_plans_dbt(self):
        stages=candidate.plan(self.args('extract'))
        self.assertEqual([s.name for s in stages],['source-prepare','source-load','price-prepare','price-load','raw-gate','loaded-lineage'])

    def test_artifact_rejects_source_hash_mismatch(self):
        path=self.artifacts();p=path/'source-load.json';value=json.loads(p.read_text());value['source_sha256']='b'*64;p.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'source lineage'):candidate.assert_extract_artifact(path)

    def test_artifact_rejects_shared_destination(self):
        path=self.artifacts();p=path/'source-load.json';value=json.loads(p.read_text());value['destination']='vaca-muerta-pulse.raw_cap4_dev.produccion_pozo_mes';p.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'source lineage'):candidate.assert_extract_artifact(path)

    def test_artifact_rejects_old_price_even_with_fresh_raw(self):
        path=self.artifacts();p=path/'price-manifest.json';value=json.loads(p.read_text());value['products']['gas']['retrieved_at']=(datetime.now(timezone.utc)-timedelta(days=8)).isoformat();value['products']['gas']['source_updated_at']=value['products']['gas']['retrieved_at'][:10];p.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'Pricing evidence stale'):candidate.assert_extract_artifact(path)

    def test_artifact_rejects_gas_disabled(self):
        path=self.artifacts();p=path/'price-manifest.json';value=json.loads(p.read_text());value['gas_valuation_enabled']=False;p.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'pricing lineage'):candidate.assert_extract_artifact(path)

    def test_artifact_rejects_price_receipt_hash_mismatch(self):
        path=self.artifacts();p=path/'price-load.json';value=json.loads(p.read_text());value['source_hashes']['gas']='d'*64;p.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'pricing lineage'):candidate.assert_extract_artifact(path)

    def test_missing_hashes_cannot_match_as_none(self):
        path=self.artifacts()
        for name in ['price-manifest','price-load']:
            p=path/(name+'.json');value=json.loads(p.read_text())
            for key in ['response_sha256','source_sha256','rows_sha256']:value.pop(key,None)
            p.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'pricing lineage'):candidate.assert_extract_artifact(path)

    def test_gate_failure_stops_before_dbt(self):
        args=self.args();stages=candidate.plan(args);calls=[]
        def execute(argv,**kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv,1)
        report=candidate.run(stages,args.run_dir,execute=execute)
        self.assertEqual(report['status'],'failed');self.assertEqual(len(calls),1)

    def test_profile_is_candidate_budgeted_and_contains_no_keys(self):
        path=candidate.configure_profile(self.path);profile=(path/'profiles.yml').read_text()
        self.assertIn('maximum_bytes_billed: 1073741824',profile)
        self.assertIn('target: candidate',profile)
        self.assertNotIn('keyfile',profile);self.assertNotIn('service-account',profile)

    def test_freshness_stage_rejects_warnings(self):
        args=self.args();args.stage='dbt-source-freshness';args.run_dir.mkdir()
        target=args.run_dir/'dbt-target';target.mkdir()
        (target/'sources.json').write_text(json.dumps({'results':[{'status':'pass'},{'status':'warn'}]}))
        with patch.object(candidate.subprocess,'run',return_value=subprocess.CompletedProcess([],0)) as process:
            with self.assertRaisesRegex(ValueError,'freshness must pass'):
                candidate.execute_stage(args)
            self.assertEqual(process.call_args.args[0][1:3],['source','freshness'])

    def test_dbt_build_enables_prices_and_rejects_skipped_results(self):
        args=self.args();args.stage='dbt-build';args.run_dir.mkdir();target=args.run_dir/'dbt-target';target.mkdir()
        (target/'run_results.json').write_text(json.dumps({'results':[{'unique_id':'test.a','status':'skipped','execution_time':0}]}))
        with patch.object(candidate.subprocess,'run',return_value=subprocess.CompletedProcess([],0)) as process:
            with self.assertRaisesRegex(ValueError,'errors/skips'):candidate.execute_stage(args)
            argv=process.call_args.args[0];vars=json.loads(argv[argv.index('--vars')+1])
            self.assertTrue(vars['enable_candidate_pricing']);self.assertEqual(vars['candidate_period'],candidate.CUTOFF)


if __name__=='__main__':unittest.main()
