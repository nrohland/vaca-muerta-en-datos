"""Export only node IDs/status/timing; omit credentials, SQL and environment metadata."""
import json
import sys
from pathlib import Path

source, output = map(Path, sys.argv[1:])
output.parent.mkdir(parents=True, exist_ok=True)
if source.exists():
    raw = json.loads(source.read_text())
    results = [{k: row.get(k) for k in ['unique_id', 'status', 'execution_time']} for row in raw['results']]
    report = {'results': results, 'publication_approved': False}
else:
    report = {'status': 'no_run_results', 'publication_approved': False}
output.write_text(json.dumps(report, indent=2))
