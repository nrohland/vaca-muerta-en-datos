"""Read-only connectivity diagnostics; no warehouse, notifications or state updates."""
import json
import time
import source_monitor as monitor


def main():
    checks = [('production_2026_metadata', lambda: monitor.source.read_metadata(2026, monitor.build_opener(monitor.source.AnnualRedirect(2026)))),
              ('catalogue', monitor.discover_resources),
              ('oil', lambda: monitor.fetch_eia(monitor.import_brent)),
              ('gas', lambda: monitor.fetch_eia(monitor.import_henry_hub))]
    failed = False
    for source, read in checks:
        started = time.monotonic()
        result = {'source': source}
        try:
            monitor.retry_public_read(read)
            result['status'] = 'passed'
        except Exception as error:
            failed = True
            result.update(status='failed', **monitor.source_error(error))
        result['seconds'] = round(time.monotonic()-started, 3)
        print(json.dumps(result), flush=True)
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
