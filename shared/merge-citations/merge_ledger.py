#!/usr/bin/env python3
"""Review all saved report citations against the same three-way merge inputs."""
import argparse
import json
from pathlib import Path
import sys

import check_citations as single

ledger_tool = single.module('merge_ledger_engine', 'tools/citation-ledger/ledger.py')
MAX_RESULT_BYTES = 1_000_000


def inspect(sources, ledger):
    ledger_tool.validate(ledger)
    if len(sources) != 3:
        raise ValueError('provide exactly three source trees')
    entries, counts = [], {}
    # A single immutable snapshot set supplies every citation, including duplicate
    # references to a source. Each anchor is bound to the actual original bytes.
    for entry in ledger['entries']:
        result = single.inspect(sources, entry['anchor'])
        counts[result['status']] = counts.get(result['status'], 0) + 1
        entries.append({'id': entry['id'], 'review': result})
        if len(json.dumps(entries, ensure_ascii=True).encode()) > MAX_RESULT_BYTES - 4096:
            raise ValueError('combined citation report exceeds 1 MB')
    status = ('blocked' if counts.get('blocked') else 'needs-review' if any(
        name != 'ready-for-review' for name in counts) else 'ready-for-review')
    report = {'format': 'merge-citation-ledger/v1', 'status': status,
            'entry_count': len(entries), 'status_counts': dict(sorted(counts.items())),
            'source_verified': False, 'entries': entries,
            'limits': ['Every entry refers to a proposed in-memory merge, never an applied file.',
                       'Ready for review still requires human context and factual review.',
                       'At most 100 anchors; 1 MB combined JSON result; inherited tree bounds.',
                       'Stable inputs required; two reads do not provide an atomic snapshot.']}
    if len(json.dumps(report, ensure_ascii=True, indent=2).encode()) > MAX_RESULT_BYTES - 64:
        raise ValueError('combined citation report exceeds 1 MB')
    return report


def from_directories(paths, ledger):
    if len(paths) != 3:
        raise ValueError('provide exactly three source directories')
    budget = [0]
    sources = [single.tree.snapshot(path, budget) for path in paths]
    report = inspect(sources, ledger)
    budget = [0]
    after = [single.tree.snapshot(path, budget) for path in paths]
    if any(single.tree.manifest(a) != single.tree.manifest(b)
           for a, b in zip(sources, after)):
        raise ValueError('source tree changed during ledger review')
    report['source_trees_rechecked'] = True
    return report


def demo():
    raw = single.anchor_tool.engine.read_bytes(
        single.anchor_tool.engine.workspace_path(single.HERE / 'examples/zto.md'), 1_000_000)
    # Two claims from the inherited real historical ZTO document. No new RPC
    # observation or claim of present chain state is made by this example.
    ledger = {'format': 'citation-ledger/v1', 'entries': [
        {'id': name, 'anchor': single.anchor_tool.capture_bytes(raw, 'zto.md', start, end)}
        for name, start, end in [('token-metadata', 3, 6), ('historical-warning', 11, 14)]]}
    text = raw.decode('utf-8')
    sources = [{'files': {'zto.md': version}, 'directories': set()} for version in
               (text, '# Reading copy\n\n' + text, text + '\nReview before use.\n')]
    report = inspect(sources, ledger)
    report['demo'] = 'Two saved claims in historical ZTO evidence; illustrative edits only.'
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('demo')
    p = sub.add_parser('review')
    for name in ('base', 'ours', 'theirs', 'ledger'):
        p.add_argument(name)
    args = parser.parse_args(argv)
    try:
        report = demo() if args.command == 'demo' else from_directories(
            [args.base, args.ours, args.theirs], ledger_tool.load(args.ledger))
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 0 if report['status'] == 'ready-for-review' else 1
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        print(json.dumps({'status': 'invalid', 'error': str(error)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
