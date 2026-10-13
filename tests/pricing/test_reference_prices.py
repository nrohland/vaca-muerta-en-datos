import hashlib
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from prepare_reference_prices import prepare
from load_reference_prices import validate

HTML = b'<table><tr><td>2026</td>' + b''.join(b'<td>'+v+b'</td>' for v in [b'66.60',b'70.89',b'103.13',b'117.29',b'107.14',b'85.40',b'83.76',b'91.08',b'114.16',b'',b'',b'']) + b'</tr></table>Release Date: 10/7/2026'

class PricesTest(unittest.TestCase):
    def rows(self):
        return prepare(HTML,'2026-08-01',datetime.now(timezone.utc).isoformat())
    def test_official_month_same_cutoff(self):
        payload,manifest=self.rows(); rows=validate(payload,manifest)
        self.assertEqual(len(rows),8); self.assertEqual(rows[-1]['price'],91.08)
        self.assertEqual(rows[-1]['periodo'],'2026-08-01')
    def test_source_hash_preserved(self):
        payload,manifest=self.rows()
        self.assertEqual(manifest['response_sha256'],hashlib.sha256(HTML).hexdigest())
    def test_missing_required_month_fails(self):
        with self.assertRaises(ValueError): prepare(HTML,'2026-10-01','2026-10-12T12:00:00Z')
    def test_cutoff_first_day_only(self):
        with self.assertRaises(ValueError): prepare(HTML,'2026-08-02','2026-10-12T12:00:00Z')
    def test_release_after_retrieval_fails(self):
        with self.assertRaises(ValueError): prepare(HTML,'2026-08-01','2026-10-01T12:00:00Z')
    def test_tamper_digest_fails(self):
        payload,manifest=self.rows()
        with self.assertRaises(ValueError): validate(payload+b' ',manifest)
    def alter(self,key,value):
        payload,manifest=self.rows(); rows=[json.loads(x) for x in payload.splitlines()]
        rows[0][key]=value
        payload=''.join(json.dumps(r)+'\n' for r in rows).encode()
        manifest['rows_sha256']=hashlib.sha256(payload).hexdigest()
        return payload,manifest
    def test_wrong_currency_fails(self):
        with self.assertRaises(ValueError): validate(*self.alter('currency','ARS'))
    def test_nonfinite_price_fails(self):
        with self.assertRaises(ValueError): validate(*self.alter('price',float('nan')))
    def test_negative_price_fails(self):
        with self.assertRaises(ValueError): validate(*self.alter('price',-1))
    def test_gas_not_enabled(self):
        with self.assertRaises(ValueError): validate(*self.alter('product','gas'))
    def test_wrong_snapshot_fails(self):
        with self.assertRaises(ValueError): validate(*self.alter('snapshot_id','a'*64))
    def test_duplicate_period_fails(self):
        with self.assertRaises(ValueError): validate(*self.alter('periodo','2026-02-01'))

if __name__=='__main__': unittest.main()
