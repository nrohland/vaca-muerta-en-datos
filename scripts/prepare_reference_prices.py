"""Build immutable candidate pricing rows from the retained official EIA HTML.

Reusable normalization for tap-eia-prices. Standalone batch CLI retired.
"""
import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
if __package__:
    from .import_brent import parse, URL
    from .import_henry_hub import parse as parse_gas, URL as GAS_URL, BENCHMARK as GAS_BENCHMARK, ENERGY_BASIS
else:
    from import_brent import parse, URL
    from import_henry_hub import parse as parse_gas, URL as GAS_URL, BENCHMARK as GAS_BENCHMARK, ENERGY_BASIS


def prepare(raw, cutoff, retrieved_at, gas_raw=None, gas_retrieved_at=None):
    cutoff_date = date.fromisoformat(cutoff)
    if cutoff_date.day != 1:
        raise ValueError('Cutoff must be first day of month')
    retrieved = datetime.fromisoformat(retrieved_at.replace('Z', '+00:00'))
    if retrieved.tzinfo is None:
        raise ValueError('Timezone required')
    snapshot = parse(raw)
    source = snapshot['source']
    if date.fromisoformat(source['source_updated_at']) > retrieved.date():
        raise ValueError('Release cannot be after retrieval')
    sha = hashlib.sha256(raw).hexdigest()
    rows = []
    for p in snapshot['prices']:
        if date.fromisoformat(p['periodo']) > cutoff_date:
            continue
        rows.append(dict(product='oil', periodo=p['periodo'], benchmark='EIA_BRENT_MONTHLY',
                         price=p['usd_per_bbl'], currency='USD', price_unit='bbl',
                         source_url=URL, source_sha256=sha,
                         source_updated_at=source['source_updated_at'],
                         retrieved_at=retrieved.isoformat(), accepted_cutoff=cutoff,
                         snapshot_id=sha, energy_basis=None))
    if not rows or cutoff not in {r['periodo'] for r in rows}:
        raise ValueError('Required cutoff price missing')
    oil_metadata = dict(product='oil', benchmark='EIA_BRENT_MONTHLY', currency='USD',
        price_unit='bbl', source_url=URL, response_sha256=sha, snapshot_id=sha,
        retrieved_at=retrieved.isoformat(), source_updated_at=source['source_updated_at'],
        row_count=len(rows), cutoff=cutoff, energy_basis=None)
    products = {'oil': oil_metadata}
    if gas_raw is not None:
        if gas_retrieved_at is None:
            raise ValueError('Gas retrieval timestamp required')
        gas_retrieved = datetime.fromisoformat(gas_retrieved_at.replace('Z', '+00:00'))
        gas_snapshot = parse_gas(gas_raw)
        gas_source = gas_snapshot['source']
        if gas_retrieved.tzinfo is None or date.fromisoformat(gas_source['source_updated_at']) > gas_retrieved.date():
            raise ValueError('Invalid gas retrieval/release chronology')
        gas_sha = hashlib.sha256(gas_raw).hexdigest()
        gas_rows = [dict(product='gas', periodo=p['periodo'], benchmark=GAS_BENCHMARK,
                        price=p['usd_per_mmbtu'], currency='USD', price_unit='MMBTU',
                        source_url=GAS_URL, source_sha256=gas_sha,
                        source_updated_at=gas_source['source_updated_at'],
                        retrieved_at=gas_retrieved.isoformat(), accepted_cutoff=cutoff,
                        snapshot_id=gas_sha, energy_basis=ENERGY_BASIS)
                    for p in gas_snapshot['prices'] if date.fromisoformat(p['periodo']) <= cutoff_date]
        if cutoff not in {r['periodo'] for r in gas_rows}:
            raise ValueError('Required gas cutoff price missing')
        products['gas'] = dict(product='gas', benchmark=GAS_BENCHMARK, currency='USD',
            price_unit='MMBTU', source_url=GAS_URL, response_sha256=gas_sha, snapshot_id=gas_sha,
            retrieved_at=gas_retrieved.isoformat(), source_updated_at=gas_source['source_updated_at'],
            row_count=len(gas_rows), cutoff=cutoff, energy_basis=ENERGY_BASIS)
        rows.extend(gas_rows)
    elif gas_retrieved_at is not None:
        raise ValueError('Gas timestamp without source')
    ndjson = ''.join(json.dumps(r, sort_keys=True) + '\n' for r in rows).encode()
    manifest = dict(schema_version=1, row_count=len(rows), response_sha256=sha,
                    rows_sha256=hashlib.sha256(ndjson).hexdigest(), cutoff=cutoff,
                    retrieved_at=retrieved.isoformat(), source_updated_at=source['source_updated_at'],
                    source_url=URL, gas_valuation_enabled=False)
    if gas_raw is not None:
        manifest = dict(schema_version=2, row_count=len(rows), products=products,
            rows_sha256=hashlib.sha256(ndjson).hexdigest(), cutoff=cutoff,
            gas_valuation_enabled=True, gas_valuation_kind='international_reference_scenario',
            retrieved_at=min(products.values(), key=lambda p: datetime.fromisoformat(p['retrieved_at']))['retrieved_at'])
    return ndjson, manifest


if __name__ == '__main__':
    raise SystemExit('Batch ingestion retired. Use: meltano run candidate-history')
