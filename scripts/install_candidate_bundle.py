#!/usr/bin/env python3
"""Replace a candidate bundle as a unit; never retain approval from an older version."""
import argparse
from pathlib import Path
import os
import shutil
import tempfile

REQUIRED = ('release.json', 'manifest.json', 'prices.json', 'valuation-manifest.json')
ALLOWED = {*REQUIRED, 'approval.json', 'snapshots', 'map', 'export-receipt.json'}


def install_bundle(source, destination):
    source, destination = Path(source).resolve(), Path(destination).absolute()
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError('Source and destination must be separate bundle directories')
    if destination.is_symlink() or any(p.is_symlink() for p in source.rglob('*')):
        raise ValueError('Bundle paths must not be symbolic links')
    for name in REQUIRED:
        if not (source/name).is_file() or not (source/name).stat().st_size:
            raise ValueError('Incomplete bundle: '+name)
    unexpected = {p.name for p in source.iterdir()} - ALLOWED
    if unexpected:
        raise ValueError('Unexpected bundle entries: '+', '.join(sorted(unexpected)))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.candidate-bundle-', dir=destination.parent) as tmp:
        stage, previous = Path(tmp)/'next', Path(tmp)/'previous'
        shutil.copytree(source, stage, ignore=shutil.ignore_patterns('export-receipt.json'))
        had_previous = destination.exists()
        if had_previous:
            os.replace(destination, previous)
        try:
            os.replace(stage, destination)
        except BaseException:
            if had_previous:
                os.replace(previous, destination)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    install_bundle(args.source, args.destination)


if __name__ == '__main__': main()
