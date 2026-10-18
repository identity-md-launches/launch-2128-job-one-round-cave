#!/usr/bin/env python3
"""Check a bounded collection of saved citations together, without rewriting it."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

spec = importlib.util.spec_from_file_location(
    'ledger_reanchor', Path(__file__).absolute().parents[1] / 'citation-reanchor/reanchor.py')
anchor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(anchor)
engine = anchor.engine
FORMAT = 'citation-ledger/v1'
MAX_ENTRIES = 100
MAX_JSON_BYTES = 1_000_000
MAX_TOTAL_BYTES = 8_000_000


def bounded(value):
    try:
        text = json.dumps(value, ensure_ascii=False, indent=2)
        if len(text.encode('utf-8')) > MAX_JSON_BYTES:
            raise engine.SearchError('ledger JSON exceeds byte limit')
    except (UnicodeError, RecursionError, ValueError) as error:
        raise engine.SearchError('invalid or oversized ledger JSON') from error
    return value


def validate(ledger):
    if (not isinstance(ledger, dict) or set(ledger) != {'format', 'entries'}
            or ledger['format'] != FORMAT or not isinstance(ledger['entries'], list)
            or not 1 <= len(ledger['entries']) <= MAX_ENTRIES):
        raise engine.SearchError('expected citation-ledger/v1 with 1 to 100 entries')
    seen = set()
    for entry in ledger['entries']:
        if not isinstance(entry, dict) or set(entry) != {'id', 'anchor'}:
            raise engine.SearchError('entry must contain id and anchor only')
        label = entry['id']
        if not isinstance(label, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', label):
            raise engine.SearchError('id must contain 1 to 64 ASCII letters, digits, _ or -')
        if label in seen:
            raise engine.SearchError('duplicate ledger id')
        seen.add(label)
        anchor.validate(entry['anchor'])
        name = entry['anchor']['path']
        try:
            if len(name.encode('utf-8')) > 4096:
                raise engine.SearchError('source path exceeds byte limit')
        except UnicodeError:
            raise engine.SearchError('source path is not valid Unicode') from None
    return bounded(ledger)


def load(path):
    raw = engine.read_bytes(engine.workspace_path(path), MAX_JSON_BYTES)
    def reject(value):
        raise engine.SearchError('non-finite JSON number')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=engine.reject_duplicates,
                           parse_constant=reject)
    except (UnicodeError, ValueError, RecursionError):
        raise engine.SearchError('invalid UTF-8 ledger JSON') from None
    return validate(value)


def check_bytes(ledger, sources):
    """Check explicitly supplied bytes; these are never marked live-verified."""
    validate(ledger)
    names = sorted({entry['anchor']['path'] for entry in ledger['entries']})
    if not isinstance(sources, dict) or set(sources) != set(names):
        raise engine.SearchError('sources must contain exactly the referenced paths')
    total = 0
    hashes = {}
    for name in names:
        raw = sources[name]
        if not isinstance(raw, bytes):
            raise engine.SearchError('source must be bytes')
        total += len(raw)
        if total > MAX_TOTAL_BYTES:
            raise engine.SearchError('total source byte limit exceeded')
        document, _ = anchor.source(raw, name)
        hashes[name] = document['sha256']
    entries, counts = [], {}
    for entry in ledger['entries']:
        result = anchor.check_bytes(entry['anchor'], sources[entry['anchor']['path']])
        status = result['status']
        counts[status] = counts.get(status, 0) + 1
        entries.append({'id': entry['id'], 'needs_review': status != 'unchanged',
                        'result': result})
    return bounded({'format': 'citation-ledger-result/v1', 'mode': 'bytes',
                    'source_verified': False, 'entry_count': len(entries),
                    'source_count': len(names), 'source_sha256': hashes,
                    'all_unchanged': counts.get('unchanged', 0) == len(entries),
                    'status_counts': dict(sorted(counts.items())), 'entries': entries})


def check_live(root, ledger):
    validate(ledger)
    names = sorted({entry['anchor']['path'] for entry in ledger['entries']})
    sources, total = {}, 0
    for name in names:
        raw = anchor.read_source(root, name)
        total += len(raw)
        if total > MAX_TOTAL_BYTES:
            raise engine.SearchError('total source byte limit exceeded')
        sources[name] = raw
    report = check_bytes(ledger, sources)
    # Recheck the whole referenced set after ALL matches, including early files.
    # This catches ordinary edits, but does not claim an atomic filesystem snapshot.
    for name in names:
        if engine.digest(anchor.read_source(root, name)) != report['source_sha256'][name]:
            raise engine.SearchError('source changed during ledger check; retry with static files')
    report['mode'] = 'live'
    report['source_verified'] = True
    for entry in report['entries']:
        entry['result']['source_verified'] = True
    return bounded(report)


def pack(paths):
    if not 1 <= len(paths) <= MAX_ENTRIES:
        raise engine.SearchError('pack requires 1 to 100 anchor files')
    return validate({'format': FORMAT, 'entries': [
        {'id': f'citation-{i}', 'anchor': anchor.load_anchor(path)}
        for i, path in enumerate(paths, 1)]})


def demo():
    root = Path(__file__).absolute().parents[1] / 'evidence-search/examples/docs'
    ledger = {'format': FORMAT, 'entries': [
        {'id': 'zto-metadata', 'anchor': anchor.capture(root, 'zto.md', 3, 6)},
        {'id': 'pool-reference', 'anchor': anchor.capture(root, 'pool.md', 1, 10)}]}
    sources = {name: anchor.read_source(root, name) for name in ['zto.md', 'pool.md']}
    sources['zto.md'] = b'# Reading copy\n\n' + sources['zto.md']
    return {'example': 'historical ZTO-first documents, not current chain state',
            'ledger': ledger, 'live': check_live(root, ledger),
            'layout_edit_in_memory': check_bytes(ledger, sources)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    subs.add_parser('demo')
    p = subs.add_parser('pack', help='print a ledger from saved citation-anchor/v1 files')
    p.add_argument('anchors', nargs='+')
    p = subs.add_parser('check', help='check every anchor against a static local corpus')
    p.add_argument('root')
    p.add_argument('ledger')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            result = demo()
        elif args.command == 'pack':
            result = pack(args.anchors)
        else:
            result = check_live(args.root, load(args.ledger))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get('all_unchanged') is False else 0
    except (engine.SearchError, OSError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
