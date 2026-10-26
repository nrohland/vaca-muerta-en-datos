"""Parse EIA monthly Henry Hub history; no daily aggregation or price substitution."""
from datetime import datetime, timezone
import hashlib
import re
if __package__:
    from .import_brent import Table
else:
    from import_brent import Table

URL = 'https://www.eia.gov/dnav/ng/hist/rngwhhdm.htm'
BENCHMARK = 'EIA_HENRY_HUB_MONTHLY'
ENERGY_BASIS = 'EIA_US_AVERAGE_1036_BTU_PER_CUBIC_FOOT_SCENARIO_V1'


def parse(raw):
    text = raw.decode('utf-8')
    if 'Henry Hub Natural Gas Spot Price' not in text or 'Dollars per Million Btu' not in text:
        raise ValueError('Wrong Henry Hub series or unit')
    table = Table(); table.feed(text)
    prices = []
    for row in table.rows:
        if len(row) != 13 or not re.fullmatch(r'\d{4}', row[0]):
            continue
        for month, cell in enumerate(row[1:], 1):
            if cell in ('', '-', '--', 'NA', 'W'):
                continue
            if not re.fullmatch(r'\d+\.\d{2}', cell) or float(cell) <= 0:
                raise ValueError('Unrecognized Henry Hub price')
            prices.append({'periodo': f'{int(row[0]):04d}-{month:02d}-01', 'usd_per_mmbtu': float(cell)})
    release = re.search(r'Release Date:\s*(\d{1,2}/\d{1,2}/\d{4})', text)
    if not prices or not release:
        raise ValueError('Missing Henry Hub history or release date')
    if len({r['periodo'] for r in prices}) != len(prices):
        raise ValueError('Duplicate Henry Hub month')
    return {'schema_version': 1, 'source': {'provider': 'EIA', 'series': 'Henry Hub Natural Gas Spot Price',
            'url': URL, 'unit': 'USD/MMBTU', 'frequency': 'monthly',
            'source_updated_at': datetime.strptime(release[1], '%m/%d/%Y').date().isoformat(),
            'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'response_sha256': hashlib.sha256(raw).hexdigest()}, 'prices': prices}
