import copy
import csv
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import source_monitor as monitor
from monitor_github import notify,restore,issue_body

NOW=datetime(2026,10,13,15,tzinfo=timezone.utc)

def value(rows=100,vm_rows=100,volume='100',fingerprint='a'*64):
    return {'rows':rows,'vm_rows':vm_rows,'oil_m3':volume,'gas_km3':volume,'oil_wells':vm_rows,'gas_wells':vm_rows,
            'duplicate_rows':0,'fingerprint':fingerprint,'vm_fingerprint':fingerprint}

def base():
    periods={f'2026-{month:02d}-01':{'profile':value(),'observed_at':(NOW-timedelta(days=3)).isoformat(),
                                  'stable_since':(NOW-timedelta(days=3)).isoformat(),'observations':1} for month in [6,7,8]}
    return {'schema_version':1,'policy':monitor.POLICY,'accepted_periods':list(periods),'periods':periods,
            'accepted_reference':{p:r['profile'] for p,r in periods.items()},'prices':{'oil':{},'gas':{}},
            'years':{},'notified_event_ids':[],'publication_approved':False}

def observe(profile=None,at=NOW,period='2026-09-01'):
    return {period:{'profile':profile or value(),'observed_at':at.isoformat()}}

PRICES={fluid:{'2026-09-01':3} for fluid in ('oil','gas')}

class Observe(unittest.TestCase):
    def test_new_partial_month_is_not_ready(self):
        state,report=monitor.compare(base(),observe(value(5,2,'2')),PRICES,NOW)
        self.assertEqual(report['months']['2026-09-01']['status'],'observing')
        self.assertTrue(any(e['kind']=='new_month_observed' for e in report['events']))
        self.assertIn('coverage_vm_rows',report['months']['2026-09-01']['reasons'])
    def test_ready_requires_independent_recoveries_and_48_hours(self):
        state,_=monitor.compare(base(),observe(at=NOW-timedelta(days=3)),PRICES,NOW-timedelta(days=3))
        repeated,report=monitor.compare(state,observe(at=NOW-timedelta(days=3)),PRICES,NOW)
        self.assertEqual(repeated['periods']['2026-09-01']['observations'],1)
        self.assertNotEqual(report['months']['2026-09-01']['status'],'ready_for_review')
        state,report=monitor.compare(state,observe(),PRICES,NOW)
        self.assertEqual(report['months']['2026-09-01']['status'],'ready_for_review')
        self.assertFalse(report['months']['2026-09-01']['official_completeness_verified'])
        self.assertEqual(state['accepted_periods'],base()['accepted_periods'])
    def test_changed_payload_resets_stability(self):
        state,_=monitor.compare(base(),observe(at=NOW-timedelta(days=3)),PRICES,NOW-timedelta(days=3))
        state,report=monitor.compare(state,observe(value(fingerprint='b'*64)),PRICES,NOW)
        self.assertEqual(state['periods']['2026-09-01']['observations'],1)
        self.assertIn('stability_not_established',report['months']['2026-09-01']['reasons'])
    def test_missing_prices_duplicates_and_extreme_volume_block_readiness(self):
        for profile,prices,reason in [(value(),{},'missing_monthly_reference_price'),
                ({**value(),'duplicate_rows':1},PRICES,'duplicate_well_month'),(value(volume='1e10'),PRICES,'volume_outlier_oil_m3')]:
            state,_=monitor.compare(base(),observe(profile,at=NOW-timedelta(days=3)),prices,NOW-timedelta(days=3))
            _,report=monitor.compare(state,observe(profile),prices,NOW)
            self.assertIn(reason,report['months']['2026-09-01']['reasons'])
    def test_current_month_in_argentina_cannot_be_ready(self):
        # UTC has advanced into October, Argentina is still in September.
        now=datetime(2026,10,1,1,tzinfo=timezone.utc)
        state,_=monitor.compare(base(),observe(at=now-timedelta(days=3)),PRICES,now-timedelta(days=3))
        _,report=monitor.compare(state,observe(at=now),PRICES,now)
        self.assertIn('month_not_elapsed',report['months']['2026-09-01']['reasons'])
    def test_reclassification_with_unchanged_totals_is_detected(self):
        state,report=monitor.compare(base(),observe(value(fingerprint='b'*64),period='2026-08-01'),PRICES,NOW)
        event=next(e for e in report['events'] if e['kind']=='accepted_month_revised')
        self.assertEqual(event['details']['before']['oil_m3'],event['details']['after']['oil_m3'])
        self.assertTrue(event['details']['vm_changed'])
        self.assertEqual(state['accepted_reference'],base()['accepted_reference'])
    def test_closed_price_revision_and_removal_are_detected(self):
        state=base();state['prices']={f:{'2026-08-01':3} for f in ('oil','gas')}
        _,report=monitor.compare(state,{}, {'oil':{'2026-08-01':4},'gas':{}}, NOW)
        self.assertEqual({e['kind'] for e in report['events']},{'accepted_price_revised','accepted_price_missing'})
    def test_future_and_replayed_different_payloads_are_rejected(self):
        with self.assertRaises(ValueError):monitor.compare(base(),observe(at=NOW+timedelta(seconds=1)),PRICES,NOW)
        state,_=monitor.compare(base(),observe(),PRICES,NOW)
        with self.assertRaises(ValueError):monitor.compare(state,observe(value(fingerprint='b'*64)),PRICES,NOW)
    def test_readiness_withdrawal_notifies(self):
        state,_=monitor.compare(base(),observe(at=NOW-timedelta(days=3)),PRICES,NOW-timedelta(days=3))
        state,_=monitor.compare(state,observe(),PRICES,NOW)
        _,report=monitor.compare(state,observe(value(5,2,'2',fingerprint='b'*64),at=NOW+timedelta(days=1)),PRICES,NOW+timedelta(days=1))
        self.assertIn('month_readiness_withdrawn',{e['kind'] for e in report['events']})

class Profile(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.file=Path(self.temp.name)/'source.csv'
        self.contract={'anio':'numeric','mes':'numeric','idpozo':'numeric','prod_pet':'numeric','prod_gas':'numeric',
                       'formacion':'text','tipo_de_recurso':'text','empresa':'text','fecha_data':'timestamp','idusuario':'numeric'}
        self.rows=[{'anio':'2026','mes':'9','idpozo':str(n),'prod_pet':'1','prod_gas':'1','formacion':'vaca muerta',
                    'tipo_de_recurso':'NO CONVENCIONAL','empresa':'A','fecha_data':'2026-10-01','idusuario':'1'} for n in (1,2)]
    def run_profile(self,rows):
        with self.file.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=self.contract);writer.writeheader();writer.writerows(rows)
        return monitor.profile(self.file,self.contract,2026)['2026-09-01']
    def test_order_and_numeric_format_do_not_create_false_revisions(self):
        first=self.run_profile(self.rows)
        changed=copy.deepcopy(list(reversed(self.rows)));changed[0]['prod_pet']='1.00'
        changed[0]['fecha_data']='2026-10-02';changed[0]['idusuario']='2'
        self.assertEqual(first['fingerprint'],self.run_profile(changed)['fingerprint'])
    def test_operator_reassignment_changes_fingerprint_without_volume_change(self):
        first=self.run_profile(self.rows);changed=copy.deepcopy(self.rows);changed[0]['empresa']='B'
        second=self.run_profile(changed);self.assertNotEqual(first['fingerprint'],second['fingerprint'])
        self.assertEqual(first['oil_m3'],second['oil_m3'])
    def test_duplicates_are_reported_and_nonfinite_or_vm_negatives_fail(self):
        self.assertEqual(self.run_profile(self.rows+self.rows)['duplicate_rows'],2)
        for invalid in ['NaN','-1']:
            changed=copy.deepcopy(self.rows);changed[0]['prod_pet']=invalid
            with self.assertRaises(ValueError):self.run_profile(changed)
    def test_schema_drift_is_not_ignored(self):
        self.file.write_text('anio,mes,idpozo\n2026,9,1\n')
        with self.assertRaisesRegex(ValueError,'schema drift'):monitor.profile(self.file,self.contract,2026)

class FakeAPI:
    def __init__(self,existing=None):self.repository='a/b';self.existing=existing or [];self.created=[]
    def api(self,path,data=None):
        if path.startswith('/labels'):return [{'name':'data-monitor'}]
        if data is None and path.startswith('/issues'):return self.existing
        if path=='/issues':self.created.append(data);return {'number':len(self.created)}
        raise AssertionError(path)

class Notices(unittest.TestCase):
    def test_delivery_is_idempotent_even_after_state_loss_or_issue_closure(self):
        _,report=monitor.compare(base(),observe(),PRICES,NOW);state=base();api=FakeAPI()
        self.assertEqual(len(notify(api,state,report,'https://github.com/a/b/actions/runs/1')),1)
        self.assertEqual(notify(api,state,report,'https://github.com/a/b/actions/runs/2'),[])
        prior={'number':1,'body':api.created[0]['body'],'state':'closed'}
        self.assertEqual(notify(FakeAPI([prior]),base(),report,'https://github.com/a/b/actions/runs/3'),[])
    def test_ready_notice_does_not_claim_official_acceptance(self):
        event={'kind':'month_ready_for_review','period':'2026-09-01','id':'a'*64,'details':{}}
        _,body=issue_body(event,'https://github.com/a/b/actions/runs/1')
        self.assertIn('no una certificación oficial',body);self.assertIn('no carga BigQuery',body)

class MonitorSecurity(unittest.TestCase):
    def test_workflow_is_public_only_main_and_metadata_artifacts(self):
        import yaml
        path=Path(__file__).resolve().parents[2]/'.github/workflows/source-monitor.yml'
        workflow=yaml.load(path.read_text(),Loader=yaml.BaseLoader);job=workflow['jobs']['observe']
        self.assertEqual(job['permissions'],{'contents':'read','actions':'read','issues':'write'})
        for banned in ['id-token','google-github-actions/auth','dbt build','gcloud','git push','secrets.']:
            self.assertNotIn(banned,path.read_text())
        guard=job['if'];self.assertIn("refs/heads/main",guard);self.assertIn('head_repository.full_name',guard)
        artifact=job['steps'][-1]['with']['path']
        self.assertNotIn('*',artifact);self.assertNotIn('.csv',artifact)
        self.assertIn('state.json',artifact);self.assertIn('report.json',artifact)
    def test_artifact_redirect_never_forwards_authorization(self):
        import io,zipfile,urllib.request
        from monitor_github import GitHub
        archive=io.BytesIO()
        with zipfile.ZipFile(archive,'w') as bundle:bundle.writestr('state.json','{}')
        class Response(io.BytesIO):
            def __enter__(self):return self
            def __exit__(self,*args):self.close()
        captured=[]
        def opener(handler):
            captured.append(handler)
            class Opener:
                def open(self,*args,**kwargs):return Response(archive.getvalue())
            return Opener()
        with patch('urllib.request.build_opener',opener):self.assertEqual(GitHub('a/b','test').artifact(1),{})
        request=urllib.request.Request('https://api.github.com/repos/a/b/actions/artifacts/1/zip',headers={'Authorization':'Bearer test'})
        redirected=captured[0].redirect_request(request,None,302,'Found',{},'https://storage.example/state.zip')
        self.assertNotIn('authorization',{k.lower():v for k,v in redirected.headers.items()})
        with self.assertRaises(ValueError):captured[0].redirect_request(request,None,302,'Found',{},'http://storage.example/state.zip')
    def test_known_outside_product_negatives_are_preserved(self):
        fixture=Profile(methodName='test_schema_drift_is_not_ignored');fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        rows=copy.deepcopy(fixture.rows);rows[0]['formacion']='other';rows[0]['prod_gas']='-100'
        result=fixture.run_profile(rows)
        self.assertEqual(result['negative_fields_outside_product'],1)
        self.assertEqual(result['gas_km3'],'1')

class RestoreScope(unittest.TestCase):
    def test_restore_skips_foreign_repo_branch_and_pull_request(self):
        class API:
            repository='a/b'
            def api(self,path,data=None):
                if '/workflows/' in path:
                    return {'workflow_runs':[
                        {'id':1,'head_branch':'main','event':'schedule','head_repository':{'full_name':'other/b'}},
                        {'id':2,'head_branch':'feature','event':'workflow_dispatch','head_repository':{'full_name':'a/b'}},
                        {'id':3,'head_branch':'main','event':'pull_request','head_repository':{'full_name':'a/b'}},
                        {'id':4,'head_branch':'main','event':'workflow_run','head_repository':{'full_name':'a/b'}}]}
                self.path=path;return {'artifacts':[{'id':1,'name':'source-monitor-state','expired':False}]}
            def artifact(self,identifier):return {'ok':True}
        with tempfile.TemporaryDirectory() as d:
            api=API();p=Path(d)/'previous.json';self.assertTrue(restore(api,p))
            self.assertIn('/runs/4/',api.path);self.assertEqual(json.loads(p.read_text()),{'ok':True})
    def test_corrupt_month_state_is_rejected(self):
        state=base();state['periods']['2026-08-15']=state['periods'].pop('2026-08-01')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text(json.dumps(state))
            with self.assertRaises(ValueError):monitor.read_state(p)
