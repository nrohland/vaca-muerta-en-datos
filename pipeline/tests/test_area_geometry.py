"""Geographic join and provenance contracts; no live network."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('area_map',ROOT/'scripts/prepare_area_map.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class Geometry(unittest.TestCase):
    def setUp(self):
        self.release={'entities':[{'dimension':'area','entity_id':'ABC','entity_name':'ÁREA UNO'}, {'dimension':'area','entity_id':'XYZ','entity_name':'OTRA'}]}
        self.feature={'properties':{'SIGLA':'ABC','NOMBRE':'AREA UNO','OPERADOR':'unreviewed'},'geometry':{'type':'Polygon','coordinates':[[[-69,-39],[-68.9,-39],[-68.9,-38.9],[-69,-39]]]}}
    def compile(self, features):
        return module.compile_map(json.dumps({'features':features}).encode(),self.release,'2026-10-18')
    def test_exact_code_and_canonical_name_required_no_fuzzy_join(self):
        bad=copy.deepcopy(self.feature);bad['properties']['SIGLA']='XYZ'
        result=self.compile([self.feature,bad])
        self.assertEqual([r['id'] for r in result['features']],['ABC'])
        self.assertEqual(result['unmatched_ids'],['XYZ'])
        self.assertIsNone(result['geometry_effective_date'])
        self.assertNotIn('unreviewed',json.dumps(result))
        self.assertEqual(result['type'],'FeatureCollection')
    def test_out_of_region_coordinates_fail_instead_of_fake_locations(self):
        self.feature['geometry']['coordinates'][0][0]=[0,0]
        self.feature['geometry']['coordinates'][0][-1]=[0,0]
        with self.assertRaisesRegex(ValueError,'outside'):self.compile([self.feature])
    def test_versioned_asset_has_unique_ids_explicit_coverage_and_size_budget(self):
        asset=ROOT/'apps/web/public/geography/areas.json';result=json.loads(asset.read_text())
        ids=[f['id'] for f in result['features']]
        self.assertEqual(len(ids),len(set(ids)));self.assertEqual(len(ids)+len(result['unmatched_ids']),result['catalog_count'])
        self.assertLess(asset.stat().st_size,200*1024);self.assertEqual(len(result['source_sha256']),64)
        self.assertIsNone(result['geometry_effective_date'])

    def test_anchors_are_in_geometry_and_outside_holes(self):
        asset=json.loads((ROOT/'apps/web/public/geography/areas.json').read_text())
        for feature in asset['features']:
            anchor=feature['properties']['anchor']
            self.assertTrue(any(module.inside_polygon(anchor,p) for p in feature['geometry']['coordinates']),feature['id'])
        polygon=[[[0,0],[10,0],[10,10],[0,10],[0,0]],[[4,4],[6,4],[6,6],[4,6],[4,4]]]
        anchor=module.interior_anchor([polygon]);self.assertTrue(module.inside_polygon(anchor,polygon))
