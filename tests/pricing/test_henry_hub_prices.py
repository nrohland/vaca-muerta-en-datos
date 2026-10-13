import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from datetime import datetime, timedelta, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from import_henry_hub import parse, ENERGY_BASIS
from prepare_reference_prices import prepare
from load_reference_prices import validate
from test_reference_prices import HTML as OIL

TITLE = b'<title>Henry Hub Natural Gas Spot Price (Dollars per Million Btu)</title>'
GAS = TITLE + b'<table><tr><td>2026</td>' + b''.join(b'<td>'+v+b'</td>' for v in [b'7.72',b'3.62',b'3.04',b'2.77',b'2.94',b'3.15',b'2.89',b'2.78',b'2.95',b'',b'',b'']) + b'</tr></table>Release Date: 10/7/2026'

class HenryHubTest(unittest.TestCase):
    def prepare(self, gas=GAS):
        now = datetime.now(timezone.utc)
        return prepare(OIL,'2026-08-01',(now-timedelta(minutes=1)).isoformat(),gas,now.isoformat())
    def rows(self):
        data, manifest = self.prepare()
        return [json.loads(x) for x in data.splitlines()], manifest
    def altered(self, mutate):
        rows, manifest = self.rows(); mutate(rows, manifest)
        data = ''.join(json.dumps(r)+'\n' for r in rows).encode()
        manifest['rows_sha256'] = hashlib.sha256(data).hexdigest()
        return data, manifest
    def test_monthly_hh_and_units(self):
        snapshot=parse(GAS)
        self.assertEqual(snapshot['source']['unit'],'USD/MMBTU')
        self.assertEqual(snapshot['prices'][7]['usd_per_mmbtu'],2.78)
    def test_wrong_series_rejected(self):
        with self.assertRaises(ValueError):parse(OIL)
    def test_wrong_unit_rejected(self):
        with self.assertRaises(ValueError):parse(GAS.replace(b'Dollars per Million Btu',b'Dollars per Barrel'))
    def test_combined_cutoff_both_products_same_month_allowed(self):
        data,manifest=self.prepare();rows=validate(data,manifest)
        self.assertEqual(len(rows),16);self.assertEqual(manifest['schema_version'],2)
        self.assertEqual(set(manifest['products']),{'oil','gas'})
        self.assertEqual([r['price'] for r in rows if r['product']=='gas' and r['periodo']=='2026-08-01'],[2.78])
    def test_individual_hashes_unchanged(self):
        _,manifest=self.prepare()
        self.assertEqual(manifest['products']['oil']['response_sha256'],hashlib.sha256(OIL).hexdigest())
        self.assertEqual(manifest['products']['gas']['response_sha256'],hashlib.sha256(GAS).hexdigest())
    def test_oldest_retrieval_not_rejuvenated(self):
        _,manifest=self.prepare()
        self.assertEqual(manifest['retrieved_at'],manifest['products']['oil']['retrieved_at'])
    def test_missing_required_gas_month_fails(self):
        with self.assertRaises(ValueError):self.prepare(GAS.replace(b'<td>2.78</td>',b'<td>NA</td>'))
    def test_missing_nonrequired_month_not_filled(self):
        data,manifest=self.prepare(GAS.replace(b'<td>3.15</td>',b'<td>NA</td>'))
        rows=validate(data,manifest)
        self.assertNotIn('2026-06-01',[r['periodo'] for r in rows if r['product']=='gas'])
    def test_wrong_gas_row_hash_fails(self):
        with self.assertRaises(ValueError):validate(*self.altered(lambda rows,m:rows[-1].update(source_sha256=m['products']['oil']['response_sha256'])))
    def test_wrong_energy_basis_fails(self):
        with self.assertRaises(ValueError):validate(*self.altered(lambda rows,m:rows[-1].update(energy_basis='measured_vm')))
    def test_wrong_gas_unit_fails(self):
        with self.assertRaises(ValueError):validate(*self.altered(lambda rows,m:rows[-1].update(price_unit='bbl')))
    def test_missing_source_manifest_fails(self):
        with self.assertRaises(ValueError):validate(*self.altered(lambda rows,m:m['products'].pop('gas')))
    def test_changed_source_count_fails(self):
        with self.assertRaises(ValueError):validate(*self.altered(lambda rows,m:m['products']['gas'].update(row_count=999)))
    def test_duplicate_within_gas_fails(self):
        with self.assertRaises(ValueError):validate(*self.altered(lambda rows,m:rows[-1].update(periodo=rows[-2]['periodo'])))
    def test_stale_one_source_fails(self):
        with self.assertRaises(ValueError):validate(*self.altered(lambda rows,m:m['products']['gas'].update(retrieved_at=(datetime.now(timezone.utc)-timedelta(days=8)).isoformat())))
    def test_zero_gas_price_fails(self):
        with self.assertRaises(ValueError):validate(*self.altered(lambda rows,m:rows[-1].update(price=0)))
    def test_wrong_gas_benchmark_fails(self):
        with self.assertRaises(ValueError):validate(*self.altered(lambda rows,m:rows[-1].update(benchmark='ARGENTINA_PPP')))
    def test_scenario_explicit(self):
        rows,manifest=self.rows()
        self.assertTrue(manifest['gas_valuation_enabled'])
        self.assertEqual(manifest['gas_valuation_kind'],'international_reference_scenario')
        self.assertEqual(rows[-1]['energy_basis'],ENERGY_BASIS)
    def test_timestamp_without_gas_bytes_fails(self):
        with self.assertRaises(ValueError):prepare(OIL,'2026-08-01',datetime.now(timezone.utc).isoformat(),gas_retrieved_at=datetime.now(timezone.utc).isoformat())

if __name__=='__main__':unittest.main()
