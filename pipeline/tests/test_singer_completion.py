from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from singer_completion import completion

class SingerCompletionTests(unittest.TestCase):
    def seed(self,root):
        paths=[]
        for directory,prefix in [(root/'offline','produccion_pozo_mes_singer_'),
                                 (root/'prices/offline','monthly_reference_price_singer_')]:
            directory.mkdir(parents=True)
            tap={'run_id':'offline','stream':prefix+'offline','rows':4,'record_sha256':'a'*64,
                'evidence':{'total_rows':4,'source_sha256':'b'*64},'publication_approved':False}
            target={'run_id':'offline','destination':'vaca-muerta-pulse.raw_cap4_candidate_dev.'+prefix+'offline',
                'rows':4,'record_sha256':'a'*64,'source_sha256':'b'*64,'method':'batch_job',
                'status':'loaded_isolated_candidate','completed_at':datetime.now(timezone.utc).isoformat(),
                'publication_approved':False}
            (directory/'tap-complete.json').write_text(json.dumps(tap))
            path=directory/'target-complete.json';path.write_text(json.dumps(target));paths.append(path)
        return paths

    def test_requires_both_certified_sources_and_never_claims_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);paths=self.seed(root)
            report=completion('offline',root)
            self.assertEqual(len(report['loads']),2)
            self.assertFalse(report['transformation_executed']);self.assertFalse(report['publication_approved'])
            paths[1].unlink()
            with self.assertRaises(FileNotFoundError):completion('offline',root)

    def test_rejects_mixed_run_destination_hash_count_and_expired_receipts(self):
        for key,value in [('run_id','another'),('rows',5),('record_sha256','c'*64),
            ('destination','vaca-muerta-pulse.raw_cap4_candidate_dev.produccion_pozo_mes'),
            ('completed_at','2020-01-01T00:00:00+00:00'),('publication_approved',True)]:
            with self.subTest(key=key),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);paths=self.seed(root);data=json.loads(paths[1].read_text())
                data[key]=value;paths[1].write_text(json.dumps(data))
                with self.assertRaises(ValueError):completion('offline',root)

if __name__=='__main__':unittest.main()
