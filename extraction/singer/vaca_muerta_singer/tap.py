"""True Singer tap: official CSV -> SCHEMA / RECORD / STATE, without a payload intermediate."""
from collections import Counter
from datetime import date, datetime
import hashlib
import json
from pathlib import Path

from singer_sdk import Stream, Tap
from extraction.scripts import source_history_pipeline as source
from extraction.scripts.parquet_candidate import INTEGERS, iter_csv_records
from .common import record_bytes, run_identity, write_json_once


def singer_schema(contract):
    properties = {}
    for name, kind in contract.items():
        if kind == 'text': properties[name] = {'type':['string','null']}
        elif kind == 'timestamp': properties[name] = {'type':['string','null'],'format':'date-time'}
        else: properties[name] = {'type':['integer' if name in INTEGERS else 'number','null']}
    properties['periodo'] = {'type':'string','format':'date'}
    for name in ('_sdc_extracted_at','_sdc_batched_at','_sdc_received_at'):
        properties[name] = {'type':'string','format':'date-time'}
    properties['_source_sha256'] = {'type':'string','pattern':'^[a-f0-9]{64}$'}
    return {'type':'object','properties':properties,'additionalProperties':False,
            'required':list(properties)}


class ProductionStream(Stream):
    primary_keys = ['idpozo','anio','mes']
    replication_key = None  # FULL_TABLE: old months may be rectified.
    STATE_MSG_FREQUENCY = 100000

    def __init__(self, tap):
        super().__init__(tap, name=tap.table_name, schema=singer_schema(tap.contract))
        self.cap4_tap = tap

    def get_records(self, context):
        del context
        tap = self.cap4_tap
        sources, reviews, total = [], [], 0
        # A failed year cannot leave a receipt that certifies a completed bundle.
        reviewed = {year:source.review_annual_source(
            year,tap.inbound,tap.base_contract,tap.work_dir,tap.anchor
        ) for year in source.RESOURCES}
        for year, resource_id in source.RESOURCES.items():
            path,retrieval,review,_ = reviewed[year]
            periods = Counter(); rows = 0
            stamp = source.now()
            for record in iter_csv_records(path,tap.contract,year,retrieval['sha256'],retrieval['downloaded_at'],stamp):
                wire = {k:v.isoformat() if isinstance(v,(date,datetime)) else v for k,v in record.items()}
                periods[wire['periodo']] += 1; rows += 1; total += 1
                tap.wire_hash.update(record_bytes(wire))
                yield wire
            if rows != review['source_rows'] or not 0 < rows <= source.MAX_ROWS_YEAR:
                raise ValueError('Singer row count differs from source review')
            sources.append({'year':year,'resource_id':resource_id,'source_sha256':retrieval['sha256'],
                'extracted_at':retrieval['downloaded_at'],'year_rows':rows,'month_rows':dict(sorted(periods.items())),
                'review':review,'source_url':retrieval['source_url'],'final_url':retrieval['final_url'],
                'transport_security':retrieval.get('transport_security')})
            reviews.append({'year':year,**review})
        tap.evidence = {'schema_version':2,'start_period':source.START_PERIOD,'cutoff':source.CUTOFF,
            'sources':sources,'total_rows':total,'accepted_periods':source.accepted_periods(),
            'source_sha256':source.bundle_digest(sources),'extracted_at':min(s['extracted_at'] for s in sources),
            'hash_scope':source.HASH_SCOPE,'coverage_status':'reviewed_complete_snapshot','reviews':reviews,
            'publication_approved':False}
        source.validate_bundle(tap.evidence)


class TapCap4(Tap):
    name = 'tap-cap4'
    config_jsonschema = {'type':'object','properties':{
        'repo_dir':{'type':'string','default':'.'},
        'run_id':{'type':'string'},'artifacts_dir':{'type':'string'},
        'inbound_dir':{'type':['string','null'],'default':None},
    },'required':['run_id','artifacts_dir']}

    def configure_source(self):
        if hasattr(self, 'contract'):
            return
        self.run_id,self.artifacts_dir,self.table_name = run_identity(self.config)
        root = Path(self.config['repo_dir']).resolve()
        self.base_contract = json.loads((root/'extraction/contracts/production_csv.json').read_text())
        self.contract = {**self.base_contract,'id':'numeric'}
        self.anchor = root/'docs/evidence/historical-source/physical-anchors.json'
        self.inbound = Path(self.config['inbound_dir']).resolve() if self.config.get('inbound_dir') else None
        self.wire_hash = hashlib.sha256()
        self.evidence = None
        self.work_dir = self.artifacts_dir/'tap-input'

    def discover_streams(self):
        self.configure_source()
        return [ProductionStream(self)]

    def sync_all(self):
        # Discovery doesn't create directories or contact a source.
        self.configure_source()
        self.work_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
        super().sync_all()
        if self.evidence is None:
            raise ValueError('Production stream must be selected')
        receipt = {'schema_version':1,'run_id':self.run_id,'stream':self.table_name,
            'replication_method':'FULL_TABLE','rows':self.evidence['total_rows'],
            'record_sha256':self.wire_hash.hexdigest(),'evidence':self.evidence,
            'completed_at':source.now(),'publication_approved':False}
        write_json_once(self.artifacts_dir/'tap-complete.json',receipt)
        self.state['cap4'] = {'run_id':self.run_id,'rows':receipt['rows'],
                              'source_sha256':self.evidence['source_sha256']}
        self.state_writer.write_state(self.state)


if __name__ == '__main__':
    TapCap4.cli()
