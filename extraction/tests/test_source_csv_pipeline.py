import argparse
import csv
import json
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import source_csv_pipeline as source


class SourcePipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def fixture(self, *, negative=False, changed=False):
        csv_path = self.path/'source.csv'
        fields = ['formacion', 'tipo_de_recurso','anio','mes','prod_pet','prod_gas']
        with csv_path.open('w') as f:
            writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
            writer.writerow(dict(zip(fields,['vaca muerta','NO CONVENCIONAL','2026','1','-1' if negative else '1','2'])))
            writer.writerow(dict(zip(fields,['vaca muerta','NO CONVENCIONAL','2026','9','1','2'])))
        release = self.path/'release.json'
        release.write_text(json.dumps({'production':[
            {'periodo':'2026-01-01','fluid':'oil','is_complete':True,'reported_well_rows':1,'volume':10 if changed else 6.289810770432105},
            {'periodo':'2026-01-01','fluid':'gas','is_complete':True,'reported_well_rows':1,'volume':0.002}]}))
        return csv_path, release

    def test_official_redirect_only(self):
        allowed = 'http://datos.energia.gob.ar/api/3/action/resource_show?id='+source.RESOURCE
        self.assertEqual(source.official_url(allowed), allowed)
        for url in ['https://evil.test/a','file:///tmp/a','https://datos.energia.gob.ar.evil.test/a','https://u:p@datos.energia.gob.ar/a','https://datos.energia.gob.ar:999/a']:
            with self.assertRaises(ValueError): source.official_url(url)

    def test_other_resource_path_rejected(self):
        with self.assertRaises(ValueError):
            source.official_url('https://datos.energia.gob.ar/api/3/action/resource_show?id=another')

    def test_nonvm_rounding_warning_preserves_value(self):
        csv_path, release = self.fixture()
        with csv_path.open('a') as f:
            f.write('another formation,CONVENCIONAL,2026,1,-0.0000000000000006,0\n')
        result = source.review_csv(csv_path, release, 2026, 1)
        self.assertEqual(result['warning_count'], 1)
        self.assertEqual(result['warnings'][0]['raw_value'], '-0.0000000000000006')

    def test_nonvm_significant_negative_blocks(self):
        csv_path, release = self.fixture()
        with csv_path.open('a') as f:
            f.write('another formation,CONVENCIONAL,2026,1,-0.000000000002,0\n')
        with self.assertRaises(ValueError): source.review_csv(csv_path, release, 2026, 1)

    def test_history_policy_preserves_negative_outside_product(self):
        csv_path, release = self.fixture()
        with csv_path.open('a') as f:
            f.write('sierras blancas,CONVENCIONAL,2026,1,-0.01,-0.01\n')
        before = csv_path.read_bytes()
        result = source.review_csv(csv_path,release,2026,1,allow_out_of_scope_negative=True)
        self.assertEqual(result['warning_count'],2)
        self.assertEqual(result['negative_policy'],'strict_vm_preserve_flag_outside_product')
        self.assertEqual(csv_path.read_bytes(),before)
        self.assertTrue(all(w['scope']=='outside_vm_noconv' for w in result['warnings']))

    def test_history_policy_still_rejects_vm_negative(self):
        with self.assertRaisesRegex(ValueError,'Invalid raw'):
            source.review_csv(*self.fixture(negative=True),2026,1,allow_out_of_scope_negative=True)

    def test_history_policy_rejects_nonfinite_outside_product(self):
        csv_path, release = self.fixture()
        with csv_path.open('a') as f:
            f.write('sierras blancas,CONVENCIONAL,2026,1,nan,0\n')
        with self.assertRaisesRegex(ValueError,'Invalid raw'):
            source.review_csv(csv_path,release,2026,1,allow_out_of_scope_negative=True)

    def test_vm_rounding_negative_has_no_exception(self):
        csv_path, release = self.fixture()
        text = csv_path.read_text().replace('2026,1,1,2', '2026,1,-0.0000000000000006,2')
        csv_path.write_text(text)
        with self.assertRaises(ValueError): source.review_csv(csv_path, release, 2026, 1)

    def test_full_source_excludes_unaccepted_month(self):
        result = source.review_csv(*self.fixture(), 2026, 1)
        self.assertEqual(result['excluded_periods'], ['2026-09-01'])
        self.assertEqual(result['source_rows'], 2)
        self.assertEqual(len(result['vm_reconciliation']), 2)

    def test_negative_volume_blocks(self):
        with self.assertRaisesRegex(ValueError, 'Invalid raw'):
            source.review_csv(*self.fixture(negative=True), 2026, 1)

    def test_source_revision_blocks(self):
        with self.assertRaisesRegex(ValueError, 'differs from accepted'):
            source.review_csv(*self.fixture(changed=True), 2026, 1)

    def test_missing_complete_anchor_blocks(self):
        with self.assertRaisesRegex(ValueError, 'Missing independently'):
            source.review_csv(*self.fixture(), 2026, 2)

    def test_shared_dataset_rejected_before_client(self):
        with self.assertRaisesRegex(ValueError, 'restricted'):
            source.load_stage(argparse.Namespace(project='vaca-muerta-pulse',dataset='raw_cap4_dev',candidate=self.path))

    def test_wrong_project_rejected(self):
        with self.assertRaisesRegex(ValueError, 'restricted'):
            source.load_stage(argparse.Namespace(project='another',dataset='raw_cap4_candidate_dev',candidate=self.path))

    def test_tampered_manifest_rejected_before_client(self):
        (self.path/'manifest.json').write_text(json.dumps({'status':'pass','review':{'accepted':True},'rows':1,
            'year':2026,'resource':{'id':'other'},'schema':{}}))
        (self.path/'evidence.json').write_text('{}')
        contract = self.path/'contract.json'; contract.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'contract differs'):
            source.load_stage(argparse.Namespace(project=source.PROJECT,dataset=source.DATASET,candidate=self.path,contract=contract))

    def test_oversized_manifest_rejected_before_client(self):
        (self.path/'manifest.json').write_text(json.dumps({'status':'pass','review':{'accepted':True},'rows':source.MAX_ROWS+1}))
        (self.path/'evidence.json').write_text('{}')
        contract = self.path/'contract.json'; contract.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Validated source'):
            source.load_stage(argparse.Namespace(project=source.PROJECT,dataset=source.DATASET,candidate=self.path,contract=contract))

    def test_wrong_cutoff_rejected_before_fetch(self):
        with self.assertRaisesRegex(ValueError, 'August'):
            source.prepare_stage(argparse.Namespace(year=2026,month=9,resource_id=source.RESOURCE))


if __name__ == '__main__': unittest.main()
