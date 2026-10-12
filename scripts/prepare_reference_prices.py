"""Build immutable candidate pricing rows from the retained official EIA HTML.

No warehouse writes. Feed output to load_reference_prices.py only after review.
"""
import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from import_brent import parse, URL


def prepare(raw, cutoff, retrieved_at):
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
    ndjson = ''.join(json.dumps(r, sort_keys=True) + '\n' for r in rows).encode()
    manifest = dict(schema_version=1, row_count=len(rows), response_sha256=sha,
                    rows_sha256=hashlib.sha256(ndjson).hexdigest(), cutoff=cutoff,
                    retrieved_at=retrieved.isoformat(), source_updated_at=source['source_updated_at'],
                    source_url=URL, gas_valuation_enabled=False)
    return ndjson, manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--cutoff', required=True)
    p.add_argument('--retrieved-at', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    rows, manifest = prepare(a.source.read_bytes(), a.cutoff, a.retrieved_at)
    a.output.write_bytes(rows)
    a.output.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest))
