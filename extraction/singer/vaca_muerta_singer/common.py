"""Run identity and canonical transport hashing; no credentials."""
import json
from decimal import Decimal
from pathlib import Path
import re


def run_identity(config):
    run_id = config.get('run_id', '')
    if not isinstance(run_id, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,47}', run_id):
        raise ValueError('run_id must start with a lowercase letter and contain 1-48 lowercase letters, digits or underscores')
    directory = Path(config['artifacts_dir']).resolve()
    if directory.name != run_id:
        raise ValueError('artifacts_dir must end with run_id')
    prefixes = {'cap4':'produccion_pozo_mes_singer_', 'reference_prices':'monthly_reference_price_singer_'}
    kind = config.get('source_kind', 'cap4')
    if kind not in prefixes:
        raise ValueError('Unsupported source_kind')
    return run_id, directory, prefixes[kind] + run_id


def _unsupported(value):
    raise TypeError(f'Unsupported wire value: {type(value).__name__}')


def record_bytes(record):
    return (json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False, default=lambda value: float(value) if isinstance(value, Decimal) else _unsupported(value))+'\n').encode()


def write_json_once(path, value):
    # A previous run is never mistaken for completion of a fresh run.
    with path.open('x') as handle:
        json.dump(value, handle, sort_keys=True, ensure_ascii=False, allow_nan=False)
        handle.write('\n')
