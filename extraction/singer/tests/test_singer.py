"""Protocol/worker tests use the real SDK and Blueprint target; all source/cloud IO mocked."""
from contextlib import ExitStack, redirect_stdout
from datetime import date, datetime, timezone
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from google.api_core.exceptions import NotFound
from target_bigquery.target import TargetBigQuery
from vaca_muerta_singer.common import run_identity
from vaca_muerta_singer.tap import TapCap4, source
from vaca_muerta_singer.target import SandboxTargetBigQuery, check_settings

ROOT = Path(__file__).resolve().parents[3]


def config(directory):
    return dict(run_id='offline', artifacts_dir=str(directory/'offline'),
        project=source.PROJECT, dataset=source.DATASET, location='US', method='batch_job',
        denormalized=True, fail_fast=True, load_method='append-only', overwrite=False,
        upsert=False, generate_view=False, add_record_metadata=False, flattening_enabled=False,
        options={'max_workers':1,'process_pool':False}, batch_size=2)


class SingerTests(unittest.TestCase):
    def test_discovery_is_offline_and_full_table(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(source,'review_annual_source') as review:
            tap = TapCap4(config={'repo_dir':str(ROOT),'run_id':'offline','artifacts_dir':tmp+'/offline'})
            stream = next(iter(tap.streams.values()))
            self.assertEqual(stream.replication_method,'FULL_TABLE')
            self.assertEqual(stream.primary_keys,['idpozo','anio','mes'])
            self.assertIn('_source_sha256',stream.schema['properties'])
            self.assertFalse(Path(tmp,'offline').exists())
            review.assert_not_called()

    def test_invalid_run_ids(self):
        for value in ['', '../escape', 'a/b', 'Upper', 'with-dash', 'a'*49]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                run_identity({'run_id':value,'artifacts_dir':'/tmp/offline'})

    def test_unsafe_target_modes_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for key,value in [('method','storage_write_api'),('method','gcs_stage'),('project','other'),
                ('dataset','raw'),('overwrite',True),('upsert',True),('fail_fast',False),
                ('generate_view',True),('credentials_json','forbidden'),('stream_maps',{'x':'y'})]:
                cfg=config(Path(tmp));cfg[key]=value
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):check_settings(cfg)

    def test_billing_enabled_blocks_before_sink_creation(self):
        with tempfile.TemporaryDirectory() as tmp, patch('vaca_muerta_singer.target.resource_preflight.inspect',
            return_value={'status':'pass','billing_enabled':True}),patch('google.cloud.bigquery.Client') as client:
            target=SandboxTargetBigQuery(config=config(Path(tmp)))
            with self.assertRaisesRegex(ValueError,'billing-disabled'):target.verify_sandbox()
            client.assert_not_called()

    def test_existing_table_or_missing_dataset_blocks(self):
        for missing in [False,True]:
            with tempfile.TemporaryDirectory() as tmp,patch('vaca_muerta_singer.target.resource_preflight.inspect',
                return_value={'status':'pass','billing_enabled':False}),patch('google.cloud.bigquery.Client') as client:
                if missing:client.return_value.get_dataset.side_effect=NotFound('absent')
                target=SandboxTargetBigQuery(config=config(Path(tmp)))
                with self.assertRaises((ValueError,NotFound)):target.verify_sandbox()
                client.return_value.create_dataset.assert_not_called()
                client.return_value.create_table.assert_not_called()

    def test_unexpected_stream_blocks_before_preflight(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(SandboxTargetBigQuery,'verify_sandbox') as verify:
            target=SandboxTargetBigQuery(config=config(Path(tmp)))
            with self.assertRaises(ValueError):target.get_sink('produccion_pozo_mes',schema={})
            verify.assert_not_called()

    def wire_fixture(self, directory):
        stamp='2026-10-25T12:00:00+00:00'
        retrieval={'sha256':'a'*64,'downloaded_at':stamp,'source_url':'https://example.invalid',
                   'final_url':'https://example.invalid','transport_security':'verified_tls'}
        def reviewed(year,*args):return Path('mock.csv'),retrieval,{'source_rows':1},None
        def records(path,contract,year,*args):
            record={k:None for k in contract}
            record.update(id=year,idpozo=year,anio=year,mes=1,prod_pet=1.5,
                periodo=date(year,1,1),_source_sha256='a'*64,
                _sdc_extracted_at=datetime.fromisoformat(stamp),_sdc_received_at=datetime.fromisoformat(stamp),
                _sdc_batched_at=datetime.fromisoformat(stamp))
            yield record
        output=io.StringIO()
        with patch.object(source,'review_annual_source',side_effect=reviewed),\
             patch('vaca_muerta_singer.tap.iter_csv_records',side_effect=records),\
             patch.object(source,'validate_bundle'), redirect_stdout(output):
            tap=TapCap4(config={'repo_dir':str(ROOT),'run_id':'offline','artifacts_dir':str(directory/'offline')})
            tap.sync_all()
        return output.getvalue()

    def run_wire(self, directory, wire, *, rows=4, worker_error=False):
        client=MagicMock()
        tables={}; loaded=[]
        def get_table(ref):
            name=str(ref)
            if name not in tables:raise NotFound('absent')
            return tables[name]
        def create_table(table,**kwargs):
            tables[str(table.reference)]=table
            return table
        def load_file(file,ref,**kwargs):
            if worker_error:raise RuntimeError('mock load failure')
            loaded.extend(json.loads(line) for line in gzip.decompress(file.read()).splitlines())
            tables[str(ref)]._properties['numRows']=str(rows)
            return MagicMock()
        client.get_table.side_effect=get_table
        client.create_table.side_effect=create_table
        client.load_table_from_file.side_effect=load_file
        stdout=io.StringIO()
        with ExitStack() as stack:
            stack.enter_context(patch('vaca_muerta_singer.target.resource_preflight.inspect',
                return_value={'status':'pass','billing_enabled':False}))
            fake_client_type=type('FakeClient',(),{'__new__':lambda cls,*args,**kwargs:client})
            stack.enter_context(patch('google.cloud.bigquery.Client',new=fake_client_type))
            stack.enter_context(patch('target_bigquery.core.bigquery_client_factory',return_value=client))
            stack.enter_context(patch('target_bigquery.batch_job.bigquery_client_factory',return_value=client))
            stack.enter_context(patch.object(source,'validate_bundle'))
            stack.enter_context(redirect_stdout(stdout))
            target=SandboxTargetBigQuery(config=config(directory))
            try:target.listen(io.StringIO(wire))
            finally:self.last_stdout=stdout.getvalue();self.last_client=client;self.last_loaded=loaded
        return target

    def test_real_singer_wire_reaches_blueprint_batch_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);wire=self.wire_fixture(directory)
            messages=[json.loads(line) for line in wire.splitlines()]
            self.assertEqual(sum(m['type']=='RECORD' for m in messages),4)
            target=self.run_wire(directory,wire)
            receipt=json.loads((directory/'offline/target-complete.json').read_text())
            self.assertEqual(receipt['rows'],4)
            self.assertEqual(len(self.last_loaded),4)
            self.assertEqual(self.last_loaded[0]['_sdc_extracted_at'],'2026-10-25T12:00:00+00:00')
            self.assertIn('cap4',self.last_stdout)
            self.last_client.query.assert_not_called()
            self.last_client.create_dataset.assert_not_called()
            self.assertFalse(receipt['publication_approved'])
            self.assertIsInstance(target,TargetBigQuery)

    def test_partial_input_does_not_acknowledge_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);wire=self.wire_fixture(directory)
            (directory/'offline/tap-complete.json').unlink()
            with self.assertRaises(FileNotFoundError):self.run_wire(directory,wire)
            self.assertEqual(self.last_stdout,'')
            self.assertFalse((directory/'offline/target-complete.json').exists())

    def test_changed_wire_is_not_certified(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);wire=self.wire_fixture(directory).replace('1.5','9.5')
            with self.assertRaisesRegex(ValueError,'altered Singer'):self.run_wire(directory,wire)
            self.assertEqual(self.last_stdout,'')

    def test_duplicate_load_or_worker_failure_is_not_certified(self):
        for kwargs in [{'rows':8},{'worker_error':True}]:
            with self.subTest(kwargs=kwargs),tempfile.TemporaryDirectory() as tmp:
                directory=Path(tmp);wire=self.wire_fixture(directory)
                with self.assertRaises(Exception):self.run_wire(directory,wire,**kwargs)
                self.assertEqual(self.last_stdout,'')
                self.assertFalse((directory/'offline/target-complete.json').exists())


if __name__=='__main__':unittest.main()
