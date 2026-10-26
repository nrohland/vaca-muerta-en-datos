"""Blueprint's Singer BigQuery target with a fail-closed sandbox policy."""
from copy import deepcopy
import hashlib
import json
from datetime import datetime, timedelta, timezone

from target_bigquery.batch_job import BigQueryBatchJobDenormalizedSink

from target_bigquery.target import TargetBigQuery
from extraction.scripts import source_history_pipeline as source
from pipeline import resource_preflight
from pipeline.verify_loaded_lineage import validate_price_manifest
from .common import record_bytes, run_identity, write_json_once


def check_settings(config):
    run_id,directory,stream = run_identity(config)
    if (config.get('project') != source.PROJECT or config.get('dataset') != source.DATASET
        or config.get('location') != 'US' or config.get('method') != 'batch_job'
        or config.get('denormalized') is not True or config.get('fail_fast') is not True
        or config.get('load_method') != 'append-only' or config.get('overwrite') is not False
        or config.get('upsert') is not False or config.get('generate_view') is not False
        or config.get('add_record_metadata') is not False
        or config.get('credentials_path') or config.get('credentials_json') or config.get('bucket')
        or config.get('stream_maps') or config.get('flattening_enabled')
        or config.get('options',{}).get('max_workers') != 1
        or config.get('options',{}).get('process_pool') is not False):
        raise ValueError('Only guarded ADC/WIF batch loading into isolated sandbox tables is allowed')
    return run_id,directory,stream


class ReviewedBatchSink(BigQueryBatchJobDenormalizedSink):
    """Use Blueprint's batch worker, preserving source provenance verbatim."""

    def _add_sdc_metadata_to_schema(self):
        pass  # Provenance is already declared by tap-cap4.

    def _add_sdc_metadata_to_record(self, record, message, context):
        pass  # Never replace the original retrieval time with a Singer processing time.

    def create_target(self, key_properties=None):
        # No dataset creation, existing-table append, DDL query or historical partition expiry.
        table = self.table.as_table(self.apply_transforms)
        table.expires = datetime.now(timezone.utc) + timedelta(days=1)
        self.client.create_table(table, exists_ok=False)
        return True

    @property
    def job_config(self):
        config = super().job_config
        config['ignore_unknown_values'] = False
        config['schema_update_options'] = []
        return config


class SandboxTargetBigQuery(TargetBigQuery):
    # Same loader implementation and worker code as the pinned Blueprint fork.
    config_jsonschema = deepcopy(TargetBigQuery.config_jsonschema)
    config_jsonschema['properties'].update({'run_id':{'type':'string'},'artifacts_dir':{'type':'string'},
        'source_kind':{'type':'string','enum':['cap4','reference_prices'],'default':'cap4'}})
    config_jsonschema['required'] = [*config_jsonschema.get('required',[]),'run_id','artifacts_dir']

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.run_id,self.artifacts_dir,self.allowed_stream = check_settings(self.config)
        if (self.artifacts_dir/'target-complete.json').exists():
            raise ValueError('Fresh target run required')
        self._sandbox_verified = False
        self._received_rows = 0
        self._received_hash = hashlib.sha256()
        self._price_payload_hash = hashlib.sha256()
        self._pending_state = None
        self._committed = False

    def get_sink_class(self, stream_name=None):
        return ReviewedBatchSink

    def verify_sandbox(self):
        report = resource_preflight.inspect()
        if report.get('status') != 'pass' or report.get('billing_enabled') is not False:
            raise ValueError('Verified billing-disabled sandbox is required')
        from google.cloud import bigquery
        from google.api_core.exceptions import NotFound
        client = bigquery.Client(project=source.PROJECT,location='US')
        client.get_dataset(f'{source.PROJECT}.{source.DATASET}')  # Never create a dataset.
        try:
            client.get_table(f'{source.PROJECT}.{source.DATASET}.{self.allowed_stream}')
        except NotFound:
            pass
        else:
            raise ValueError('Run table already exists; use a fresh run_id')
        self.artifacts_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
        write_json_once(self.artifacts_dir/'sandbox-preflight.json',report)

    def get_sink(self,stream_name,**kwargs):
        if stream_name != self.allowed_stream:
            raise ValueError('Only the isolated table for this run is allowed')
        if not self._sandbox_verified:
            self.verify_sandbox()
            self._sandbox_verified = True
        return super().get_sink(stream_name,**kwargs)

    def _process_record_message(self,message_dict):
        if message_dict['stream'] != self.allowed_stream:
            raise ValueError('Unexpected stream')
        super()._process_record_message(message_dict)
        self._received_rows += 1
        self._received_hash.update(record_bytes(message_dict['record']))
        if self.config.get('source_kind') == 'reference_prices':
            normalized = json.loads(record_bytes(message_dict['record']))
            self._price_payload_hash.update((json.dumps(normalized, sort_keys=True)+'\n').encode())

    def _write_state_message(self,state):
        # No checkpoint is acknowledged until the source completes and all BQ workers succeed.
        if self._committed:
            super()._write_state_message(state)
        else:
            self._pending_state = deepcopy(state)

    def verify_loaded_count(self):
        from google.cloud import bigquery
        table = bigquery.Client(project=source.PROJECT,location='US').get_table(
            f'{source.PROJECT}.{source.DATASET}.{self.allowed_stream}')
        if table.num_rows != self._received_rows:
            raise ValueError('BigQuery row count differs; possible incomplete/replayed load')

    def process_endofpipe(self):
        super().process_endofpipe()
        receipt = json.loads((self.artifacts_dir/'tap-complete.json').read_text())
        if self.config.get('source_kind') == 'reference_prices':
            manifest = receipt['evidence']['price_manifest']
            validate_price_manifest(manifest)
            if (manifest['row_count'] != self._received_rows
                or manifest['rows_sha256'] != self._price_payload_hash.hexdigest()
                or receipt['evidence']['source_sha256'] != manifest['rows_sha256']):
                raise ValueError('Price payload differs from reviewed manifest')
        else:
            source.validate_bundle(receipt['evidence'])
        if (receipt.get('run_id') != self.run_id or receipt.get('stream') != self.allowed_stream
            or receipt.get('rows') != self._received_rows
            or receipt['evidence'].get('total_rows') != self._received_rows
            or receipt.get('record_sha256') != self._received_hash.hexdigest()
            or receipt.get('publication_approved') is not False):
            raise ValueError('Incomplete or altered Singer input; no target completion/state')
        self.verify_loaded_count()
        write_json_once(self.artifacts_dir/'target-complete.json',{
            'schema_version':1,'run_id':self.run_id,'status':'loaded_isolated_candidate',
            'destination':f'{source.PROJECT}.{source.DATASET}.{self.allowed_stream}',
            'rows':self._received_rows,'record_sha256':self._received_hash.hexdigest(),
            'source_sha256':receipt['evidence']['source_sha256'],'method':'batch_job',
            'completed_at':source.now(),'publication_approved':False})
        self._committed = True
        if self._pending_state:
            super()._write_state_message(self._pending_state)


if __name__ == '__main__':
    SandboxTargetBigQuery.cli()
