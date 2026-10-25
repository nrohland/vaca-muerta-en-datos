#!/usr/bin/env python3
"""Reject environment files, credentials and generated artifacts in Git. No file values are printed."""
import argparse
from pathlib import PurePosixPath
import subprocess


def forbidden(path):
    p=PurePosixPath(path);name=p.name.casefold();parts={v.casefold() for v in p.parts}
    if name=='.env' or (name.startswith('.env.') and name!='.env.example'):
        return 'environment file'
    if name.endswith(('.pem','.key','.p12','.pfx','.tfstate','.tfplan')):
        return 'private key or infrastructure state'
    if name in {'application_default_credentials.json','credentials.json','meltano-raw-writer.json','vm-pulse-meltano.json','vm-pulse-dbt.json'} or name.startswith('gha-creds-'):
        return 'credential file'
    if parts.intersection({'.secrets','secrets','credentials','.venv','node_modules','.next','.terraform','.meltano','.local','__pycache__'}):
        return 'private or generated directory'
    return None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history',action='store_true',help='Also inspect every path recorded in all reachable commits')
    args=parser.parse_args()
    paths=set(subprocess.check_output(['git','ls-files','--cached','-z']).decode().split('\0'))-{''}
    if args.history:
        names=subprocess.check_output(['git','log','--all','--format=','--name-only','-z']).decode()
        paths.update(v.strip('\n') for v in names.split('\0') if v.strip('\n'))
    failures=[(p,forbidden(p)) for p in sorted(paths) if forbidden(p)]
    for path,reason in failures:print(f'BLOCKED {path!r}: {reason}')
    print(f'Publication path check: {len(paths)} paths, {len(failures)} violations')
    return int(bool(failures))


if __name__=='__main__':raise SystemExit(main())
