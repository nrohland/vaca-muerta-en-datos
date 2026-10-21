from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[2]

def reject(message): raise ValueError(message)

class DbtIsolation(unittest.TestCase):
    def node(self, resource_type='model', enabled=True):
        return SimpleNamespace(resource_type=resource_type, config=SimpleNamespace(enabled=enabled), unique_id='model.test')
    def test_audit_schema_is_only_allowed_for_tests(self):
        macro = self.macros('candidate')
        self.assertEqual(macro.generate_schema_name('dbt_test__audit', self.node('test')).strip(), 'fallback')
        with self.assertRaises(ValueError): macro.generate_schema_name('dbt_test__audit', self.node())
        self.assertEqual(macro.generate_schema_name('meta', self.node(enabled=False)).strip(), 'fallback')
    def macros(self, name, period='2025-12-01'):
        env = Environment()
        env.globals.update(target=SimpleNamespace(name=name, schema='fallback'),
            modules=SimpleNamespace(re=re), exceptions=SimpleNamespace(raise_compiler_error=reject),
            var=lambda key, default=None: period if key == 'candidate_period' else default,
            **{'return': lambda value: value})
        text = (ROOT/'transform/macros/generate_schema_name.sql').read_text()
        text += (ROOT/'transform/macros/candidate_period_sql.sql').read_text()
        return env.from_string(text).make_module()
    def test_candidate_cannot_write_existing_dev_or_prod(self):
        macro = self.macros('candidate')
        for layer in ['stg', 'int', 'marts']:
            self.assertEqual(macro.generate_schema_name(layer, self.node()).strip(), layer+'_cap4_candidate_dev')
        with self.assertRaises(ValueError): macro.generate_schema_name('raw_cap4_dev', self.node())
    def test_original_dev_and_prod_names_are_preserved(self):
        for layer in ['stg', 'int', 'marts']:
            self.assertEqual(self.macros('dev').generate_schema_name(layer, {}).strip(), layer+'_cap4_dev')
            self.assertEqual(self.macros('prod').generate_schema_name(layer, {}).strip(), layer+'_cap4')
    def test_candidate_period_is_typed_and_required(self):
        self.assertEqual(self.macros('candidate').candidate_period_sql().strip(), "DATE '2025-12-01'")
        for value in ['', '2025-13-01', "2025-12-01' OR true --", ['2025-12-01']]:
            with self.assertRaises(ValueError): self.macros('candidate', value).candidate_period_sql()
