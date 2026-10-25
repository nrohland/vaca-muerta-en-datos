import argparse
import copy
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import source_history_pipeline as source


class HistoryPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.inbound=self.root/'inbound';self.inbound.mkdir()
        self.contract=self.root/'contract.json'
        fields={'idpozo':'numeric','anio':'numeric','mes':'numeric','formacion':'text',
                'tipo_de_recurso':'text','prod_pet':'numeric','prod_gas':'numeric'}
        self.contract.write_text(json.dumps(fields));self.fields=fields
        self.anchor=self.root/'release.json';anchors=[]
        for year,resource in source.RESOURCES.items():
            csvpath=self.inbound/f'{year}.csv'
            with csvpath.open('w') as stream:
                writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
                for month in range(1,13):
                    writer.writerow({'idpozo':1,'anio':year,'mes':month,'formacion':'vaca muerta',
                                     'tipo_de_recurso':'NO CONVENCIONAL','prod_pet':1,'prod_gas':2})
                    if year<2026 or month<=8:
                        for fluid,volume in [('oil',6.289810770432105),('gas',0.002)]:
                            anchors.append({'fluid':fluid,'periodo':f'{year}-{month:02d}-01',
                                            'volume':volume,'reported_well_rows':1,'is_complete':True})
            url=f'https://datos.energia.gob.ar/dataset/{source.PACKAGE}/resource/{resource}/download/produccin-de-pozos-de-gas-y-petrleo-{year}.csv'
            metadata={'id':resource,'url':url,'size':csvpath.stat().st_size,'last_modified':'2026-10-13'}
            retained={'year':year,'resource_id':resource,'before':metadata,'after':metadata,
                      'source_url':url,'final_url':url,'downloaded_at':source.now(),'sha256':source.digest(csvpath)}
            (self.inbound/f'{year}.retrieval.json').write_text(json.dumps(retained))
        self.anchor.write_text(json.dumps({'production':anchors}))
        self.args=argparse.Namespace(start_period=source.START_PERIOD,cutoff=source.CUTOFF,
            output=self.root/'candidate',inbound=self.inbound,contract=self.contract,anchor_release=self.anchor)

    def prepared(self):
        source.prepare_stage(self.args)
        return json.loads((self.args.output/'evidence.json').read_text())

    def test_complete_bundle_stamped_once_preserves_original_retrieval(self):
        evidence=self.prepared();source.validate_bundle(evidence)
        metrics=json.loads((self.args.output/'preparation-metrics.json').read_text())
        self.assertEqual(len(metrics['phases']),12)
        self.assertTrue(all(p['status']=='passed' and p['seconds']>=0 for p in metrics['phases']))
        self.assertFalse(any('source_url' in p or 'raw_value' in p for p in metrics['phases']))
        self.assertEqual([v['year'] for v in evidence['sources']],[2023,2024,2025,2026])
        self.assertEqual(len(evidence['accepted_periods']),44)
        self.assertEqual(evidence['total_rows'],48)
        self.assertEqual(sum(len(s['review']['vm_reconciliation']) for s in evidence['sources']),88)
        manifest=source.validate_candidate(self.args.output,self.fields)
        self.assertEqual(manifest['source_hashes'],{str(s['year']):s['source_sha256'] for s in evidence['sources']})
        import pyarrow.parquet as pq
        records=pq.read_table(self.args.output/'history.raw.parquet').to_pylist()
        self.assertEqual(len(records),48)
        self.assertEqual(records[0]['_sdc_extracted_at'].isoformat(),evidence['sources'][0]['extracted_at'])
        self.assertFalse(any(self.args.output.glob('*-normalized/*.ndjson')))
        self.assertFalse((self.args.output/'load.ndjson').exists())

    def test_2024_official_row_id_is_preserved_other_years_are_null(self):
        path=self.inbound/'2024.csv'
        with path.open() as stream:
            reader=csv.DictReader(stream);fields=list(reader.fieldnames);rows=list(reader)
        with path.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=[*fields,'id']);writer.writeheader()
            for i,row in enumerate(rows,1):writer.writerow({**row,'id':i})
        meta=self.inbound/'2024.retrieval.json';value=json.loads(meta.read_text())
        value['sha256']=source.digest(path);meta.write_text(json.dumps(value))
        self.prepared()
        import pyarrow.parquet as pq
        records=pq.read_table(self.args.output/'history.raw.parquet').to_pylist()
        self.assertTrue(all(r['id'] is not None for r in records if r['anio']==2024))
        self.assertTrue(all(r['id'] is None for r in records if r['anio']!=2024))
        self.assertEqual(source.validate_candidate(self.args.output,self.fields)['schema']['id'],'numeric')

    def test_unreviewed_extra_column_fails_before_large_payload(self):
        path=self.inbound/'2024.csv'
        path.write_text(path.read_text().replace('prod_gas','prod_gas,unexpected'))
        meta=self.inbound/'2024.retrieval.json';value=json.loads(meta.read_text())
        value['sha256']=source.digest(path);meta.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'Annual CSV fields'):
            self.prepared()
        self.assertFalse((self.args.output/'history.raw.parquet').exists())

    def test_bundle_hash_tampering_rejected(self):
        value=self.prepared();value['sources'][0]['source_sha256']='a'*64
        with self.assertRaises(ValueError):source.validate_bundle(value)

    def test_partial_review_anchors_rejected(self):
        value=self.prepared();value['sources'][0]['review']['vm_reconciliation'].pop()
        value['source_sha256']=source.bundle_digest(value['sources'])
        with self.assertRaisesRegex(ValueError,'both-fluid'):source.validate_bundle(value)

    def test_other_resource_rejected(self):
        value=self.prepared();value['sources'][1]['resource_id']='different'
        value['source_sha256']=source.bundle_digest(value['sources'])
        with self.assertRaises(ValueError):source.validate_bundle(value)

    def test_source_bytes_changed_rejected_before_normalization(self):
        with (self.inbound/'2023.csv').open('a') as target:target.write('\n')
        with self.assertRaisesRegex(ValueError,'bytes differ'):source.prepare_stage(self.args)

    def test_stale_retained_source_not_rejuvenated(self):
        p=self.inbound/'2023.retrieval.json';value=json.loads(p.read_text());value['downloaded_at']='2000-01-01T00:00:00+00:00';p.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'stale'):source.prepare_stage(self.args)

    def test_metadata_change_rejected(self):
        p=self.inbound/'2023.retrieval.json';value=json.loads(p.read_text());value['after']['size']=99;p.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'changed'):source.prepare_stage(self.args)

    def test_review_revision_not_silently_accepted(self):
        p=self.anchor;value=json.loads(p.read_text());value['production'][0]['volume']=99;p.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'differs from accepted'):source.prepare_stage(self.args)

    def test_exact_url_allowlist(self):
        resource=source.RESOURCES[2023]
        good='http://datos.energia.gob.ar/api/3/action/resource_show?id='+resource
        self.assertEqual(source.official_url(good,2023),good)
        for bad in [good+'&extra=1',good.replace(resource,source.RESOURCES[2024]),good.replace('datos.energia.gob.ar','datos.energia.gob.ar.evil.test'),good+'#fragment',good.replace('http://','file://'),good.replace('http://','http://u:p@')]:
            with self.assertRaises(ValueError):source.official_url(bad,2023)

    def test_shared_dataset_never_reaches_client(self):
        with self.assertRaisesRegex(ValueError,'restricted'):
            source.load_stage(argparse.Namespace(project=source.PROJECT,dataset='raw_cap4_dev'))

    def test_wrong_project_never_reaches_client(self):
        with self.assertRaisesRegex(ValueError,'restricted'):
            source.load_stage(argparse.Namespace(project='another-project',dataset=source.DATASET))

    def test_payload_bytes_tampering_rejected(self):
        self.prepared()
        with (self.args.output/'history.raw.parquet').open('a') as target:target.write('{}\n')
        with self.assertRaisesRegex(ValueError,'bytes differ'):
            source.validate_candidate(self.args.output,self.fields)

    def test_schema_mismatch_rejected(self):
        self.prepared()
        with self.assertRaisesRegex(ValueError,'schema contract'):
            source.validate_candidate(self.args.output,{'other':'text'})

    def test_legacy_retained_format_rechecks_metadata_without_timestamp_renewal(self):
        p=self.inbound/'2023.retrieval.json';value=json.loads(p.read_text())
        legacy={'year':2023,'resource':value['before'],'extracted_at':value['downloaded_at'],
                'source_url':value['source_url'],'final_url':value['final_url'],'source_sha256':value['sha256']}
        with patch.object(source,'read_metadata',return_value=value['after']):
            normalized=source.normalize_retained(2023,legacy)
        self.assertEqual(normalized['downloaded_at'],value['downloaded_at'])
        self.assertEqual(normalized['sha256'],value['sha256'])


if __name__=='__main__':unittest.main()
