"""Typed, bounded CSV → Parquet landing; no warehouse access or inferred schemas."""
import csv
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
from functools import lru_cache
import math
import pyarrow as pa
import pyarrow.parquet as pq

INTEGERS = {'id', 'idpozo', 'anio', 'mes', 'idusuario'}
BATCH_ROWS = 32768


def arrow_schema(contract):
    fields = [pa.field(name, pa.string() if kind == 'text' else pa.timestamp('us', tz='UTC')
                      if kind == 'timestamp' else pa.int64() if name in INTEGERS else pa.float64())
              for name, kind in contract.items()]
    return pa.schema(fields + [pa.field('periodo', pa.date32())] +
        [pa.field(k, pa.timestamp('us', tz='UTC')) for k in
         ('_sdc_extracted_at', '_sdc_batched_at', '_sdc_received_at')] +
        [pa.field('_source_sha256', pa.string())])


@lru_cache(maxsize=4096)
def timestamp(value):
    parsed = datetime.fromisoformat(value)
    # BigQuery's existing JSON load interprets unzoned timestamps as UTC.
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def iter_csv_records(csv_path, contract, year, source_hash, retrieved_at, batched_at):
    """Strict raw records shared by Singer and Parquet batch preparation."""
    seen = {}
    with csv_path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        expected = set(contract) - ({'id'} if year != 2024 else set())
        # The reviewed 2024 source may or may not carry its optional surrogate id.
        actual = set(reader.fieldnames or [])
        if len(reader.fieldnames or []) != len(actual) or actual not in (expected, expected-{'id'}):
            raise ValueError('CSV fields differ from reviewed contract')
        for row in reader:
            if None in row or None in row.values(): raise ValueError('Malformed CSV record')
            record = {}
            for name, kind in contract.items():
                value = row.get(name, '')
                if kind == 'text': record[name] = value
                elif value == '': record[name] = None
                elif kind == 'timestamp': record[name] = timestamp(value)
                elif kind == 'numeric':
                    decimal = Decimal(value)
                    if not decimal.is_finite() or (name in INTEGERS and decimal != decimal.to_integral_value()):
                        raise ValueError('Invalid numeric field: ' + name)
                    record[name] = int(decimal) if name in INTEGERS else float(decimal)
                    if not math.isfinite(record[name]): raise ValueError('Nonfinite value')
                else: raise ValueError('Unreviewed field type')
            if record['anio'] != year or not 1 <= record['mes'] <= 12 or not record['idpozo'] or record['idpozo'] <= 0:
                raise ValueError('Invalid production grain')
            # Twelve-bit month bitmap per well: uniqueness without retaining a tuple per row.
            bit = 1 << record['mes']; previous = seen.get(record['idpozo'], 0)
            if previous & bit: raise ValueError('Duplicate production grain')
            seen[record['idpozo']] = previous | bit
            period = date(year, record['mes'], 1)
            record.update(periodo=period, _source_sha256=source_hash,
                _sdc_extracted_at=timestamp(retrieved_at), _sdc_batched_at=timestamp(batched_at),
                _sdc_received_at=timestamp(batched_at))
            yield record


def append_csv(writer, csv_path, contract, year, source_hash, retrieved_at, batched_at):
    schema = arrow_schema(contract)
    buffers = {f.name: [] for f in schema}
    periods = Counter(); total = 0
    def flush():
        if buffers['anio']:
            writer.write_table(pa.Table.from_pydict(buffers, schema=schema), row_group_size=BATCH_ROWS)
            for values in buffers.values(): values.clear()
    for record in iter_csv_records(csv_path, contract, year, source_hash, retrieved_at, batched_at):
        periods[record['periodo'].isoformat()] += 1
        for name, values in buffers.items(): values.append(record[name])
        total += 1
        if total % BATCH_ROWS == 0: flush()
    flush()
    if total == 0: raise ValueError('Empty source')
    return {'rows': total, 'period_rows': dict(sorted(periods.items()))}
