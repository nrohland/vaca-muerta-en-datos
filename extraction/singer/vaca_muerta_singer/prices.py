"""Singer tap for both official monthly EIA references, with existing parsing/validation."""
import hashlib
import json

from singer_sdk import Stream, Tap
from pipeline.public_price_fetch import fetch
from pipeline.verify_loaded_lineage import validate_price_manifest
from scripts.prepare_reference_prices import prepare, URL, GAS_URL
from scripts.load_reference_prices import validate
from extraction.scripts import source_history_pipeline as source
from .common import record_bytes, run_identity, write_json_once


def price_schema():
    strings = ['product','benchmark','currency','price_unit','source_url','source_sha256','snapshot_id']
    properties = {name:{'type':'string'} for name in strings}
    properties.update({name:{'type':'string','format':'date'}
        for name in ['periodo','source_updated_at','accepted_cutoff']})
    properties.update(price={'type':'number'},energy_basis={'type':['string','null']},
        retrieved_at={'type':'string','format':'date-time'})
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}


class ReferencePricesStream(Stream):
    primary_keys = ['product','periodo']
    replication_key = None

    def get_records(self, context):
        oil = fetch(URL); oil_at = source.now()
        gas = fetch(GAS_URL); gas_at = source.now()
        payload, manifest = prepare(oil,source.CUTOFF,oil_at,gas,gas_at)
        records = validate(payload,manifest)
        validate_price_manifest(manifest)
        for product in ('oil','gas'):
            periods = {r['periodo'] for r in records if r['product']==product}
            if not set(source.accepted_periods()) <= periods:
                raise ValueError('Incomplete price coverage for accepted production history')
        self._tap.evidence = {'price_manifest':manifest,'total_rows':len(records),
                              'source_sha256':manifest['rows_sha256']}
        for record in records:
            self._tap.wire_hash.update(record_bytes(record))
            yield record


class TapEIAPrices(Tap):
    name = 'tap-eia-prices'
    config_jsonschema = {'type':'object','properties':{
        'run_id':{'type':'string'},'artifacts_dir':{'type':'string'}},
        'required':['run_id','artifacts_dir']}

    def discover_streams(self):
        self.run_id,self.artifacts_dir,self.table_name = run_identity({**self.config,'source_kind':'reference_prices'})
        self.wire_hash = hashlib.sha256()
        self.evidence = None
        return [ReferencePricesStream(self,name=self.table_name,schema=price_schema())]

    def sync_all(self):
        self.artifacts_dir.mkdir(parents=True,exist_ok=False,mode=0o700)
        super().sync_all()
        if self.evidence is None:
            raise ValueError('Reference prices stream must be selected')
        write_json_once(self.artifacts_dir/'tap-complete.json',{
            'schema_version':1,'run_id':self.run_id,'stream':self.table_name,
            'rows':self.evidence['total_rows'],'record_sha256':self.wire_hash.hexdigest(),
            'evidence':self.evidence,'completed_at':source.now(),'publication_approved':False})
        self.state['references'] = {'run_id':self.run_id,'rows':self.evidence['total_rows'],
                                  'source_sha256':self.evidence['source_sha256']}
        self.state_writer.write_state(self.state)


if __name__=='__main__':
    TapEIAPrices.cli()
