import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('ledger', Path(__file__).with_name('ledger.py'))
l = importlib.util.module_from_spec(spec)
spec.loader.exec_module(l)


class LedgerTests(unittest.TestCase):
    def setUp(self):
        Path('test/scratch').mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir='test/scratch')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sources = {'a.md': b'intro\nZTO\n18 decimals\nend\n', 'b.txt': b'pool\nIMD\n'}
        for name, raw in self.sources.items():
            (self.root / name).write_bytes(raw)
        self.ledger = {'format': l.FORMAT, 'entries': [
            {'id': 'token', 'anchor': l.anchor.capture_bytes(self.sources['a.md'], 'a.md', 2, 3)},
            {'id': 'pool', 'anchor': l.anchor.capture_bytes(self.sources['b.txt'], 'b.txt', 1, 1)}]}

    def test_live_and_bytes_flags_and_immutability(self):
        before = copy.deepcopy(self.ledger)
        live = l.check_live(self.root, self.ledger)
        self.assertTrue(live['all_unchanged'])
        self.assertEqual(live['status_counts'], {'unchanged': 2})
        self.assertTrue(all(e['result']['source_verified'] for e in live['entries']))
        snapshot = l.check_bytes(self.ledger, self.sources)
        self.assertFalse(snapshot['source_verified'])
        self.assertFalse(any(e['result']['source_verified'] for e in snapshot['entries']))
        self.assertEqual(self.ledger, before)
        for name, raw in self.sources.items():
            self.assertEqual((self.root / name).read_bytes(), raw)

    def test_all_five_statuses_and_review_policy(self):
        variants = [
            (self.sources['a.md'], 'unchanged'),
            (b'intro\nZTO\n18 decimals\nchanged', 'same_lines_changed_source'),
            (b'new\n' + self.sources['a.md'], 'relocated'),
            (b'ZTO\n18 decimals\n' * 2, 'ambiguous'),
            (b'no longer here', 'missing')]
        for raw, status in variants:
            result = l.check_bytes(self.ledger, dict(self.sources, **{'a.md': raw}))
            item = result['entries'][0]
            self.assertEqual(item['result']['status'], status)
            self.assertEqual(item['needs_review'], status != 'unchanged')
            self.assertEqual(result['all_unchanged'], status == 'unchanged')
            self.assertEqual(result['entries'][1]['result']['status'], 'unchanged')

    def test_shared_source_read_only_twice(self):
        ledger = copy.deepcopy(self.ledger)
        ledger['entries'][1] = {'id': 'other', 'anchor': ledger['entries'][0]['anchor']}
        with patch.object(l.anchor, 'read_source', wraps=l.anchor.read_source) as read:
            report = l.check_live(self.root, ledger)
        self.assertEqual(read.call_count, 2)
        self.assertEqual(report['source_count'], 1)
        self.assertEqual(report['entry_count'], 2)

    def test_earlier_source_change_detected_after_all_matches(self):
        original = l.anchor.read_source
        calls = []
        def read(root, name):
            calls.append(name)
            if len(calls) == 3:
                return b'changed after second file was processed'
            return original(root, name)
        with patch.object(l.anchor, 'read_source', side_effect=read):
            with self.assertRaises(l.engine.SearchError):
                l.check_live(self.root, self.ledger)
        self.assertEqual(calls, ['a.md', 'b.txt', 'a.md'])

    def test_missing_file_symlink_and_traversal_fail(self):
        (self.root / 'b.txt').unlink()
        with self.assertRaises(l.engine.SearchError):
            l.check_live(self.root, self.ledger)
        (self.root / 'b.txt').symlink_to('a.md')
        with self.assertRaises(l.engine.SearchError):
            l.check_live(self.root, self.ledger)
        for path in ['../escape', '/outside-workspace']:
            with self.assertRaises(l.engine.SearchError):
                l.check_live(path, self.ledger)

    def test_envelope_ids_paths_and_bounds(self):
        bad_values = [{}, [], dict(self.ledger, extra=1), dict(self.ledger, entries=[]),
                      dict(self.ledger, entries=self.ledger['entries'] * 51)]
        for bad in bad_values:
            with self.assertRaises(l.engine.SearchError):
                l.validate(bad)
        for value in ['', 'bad id', 'x' * 65, '\ud800', 3, None]:
            bad = copy.deepcopy(self.ledger)
            bad['entries'][0]['id'] = value
            with self.assertRaises(l.engine.SearchError):
                l.validate(bad)
        for value in ['../x.md', '/x.md', '.hidden.md', 'x.py', '\ud800.md', 'x' * 4097 + '.md']:
            bad = copy.deepcopy(self.ledger)
            bad['entries'][0]['anchor']['path'] = value
            with self.assertRaises(l.engine.SearchError):
                l.validate(bad)
        bad = copy.deepcopy(self.ledger)
        bad['entries'][1]['id'] = 'token'
        with self.assertRaises(l.engine.SearchError):
            l.validate(bad)

    def test_forged_anchor_and_invalid_source_no_partial_result(self):
        bad = copy.deepcopy(self.ledger)
        bad['entries'][0]['anchor']['text'] = 'forged\ntext'
        with self.assertRaises(l.engine.SearchError):
            l.check_bytes(bad, self.sources)
        for raw in [b'\xff', b'\x00', b'x' * 1_000_001, 'not bytes']:
            with self.assertRaises(l.engine.SearchError):
                l.check_bytes(self.ledger, dict(self.sources, **{'a.md': raw}))
        for sources in [{}, dict(self.sources, extra=b'x')]:
            with self.assertRaises(l.engine.SearchError):
                l.check_bytes(self.ledger, sources)
        with patch.object(l, 'MAX_TOTAL_BYTES', 3):
            with self.assertRaises(l.engine.SearchError):
                l.check_bytes(self.ledger, self.sources)
            with self.assertRaises(l.engine.SearchError):
                l.check_live(self.root, self.ledger)
        with patch.object(l, 'MAX_JSON_BYTES', 5):
            with self.assertRaises(l.engine.SearchError):
                l.validate(self.ledger)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-B', l.__file__, *map(str, args)],
                              capture_output=True, text=True)

    def test_pack_and_cli_exit_codes(self):
        paths = []
        for i, entry in enumerate(self.ledger['entries']):
            path = self.root / f'anchor-{i}.json'
            path.write_text(json.dumps(entry['anchor']))
            paths.append(path)
        packed = self.run_cli('pack', *paths)
        self.assertEqual(packed.returncode, 0, packed.stderr)
        saved = self.root / 'ledger.json'
        saved.write_text(packed.stdout)
        saved_bytes = saved.read_bytes()
        self.assertEqual(self.run_cli('check', self.root, saved).returncode, 0)
        (self.root / 'a.md').write_bytes(b'new\n' + self.sources['a.md'])
        moved = self.run_cli('check', self.root, saved)
        self.assertEqual(moved.returncode, 1, moved.stderr)
        self.assertEqual(json.loads(moved.stdout)['status_counts'], {'relocated': 1, 'unchanged': 1})
        (self.root / 'b.txt').unlink()
        missing = self.run_cli('check', self.root, saved)
        self.assertEqual(missing.returncode, 2)
        self.assertEqual(missing.stdout, '')
        self.assertEqual(saved.read_bytes(), saved_bytes)

    def test_bad_json_refused(self):
        path = self.root / 'bad.json'
        for raw in [b'{"format":1,"format":2}', b'{"x":NaN}', b'\xff', b'[]',
                    ('{"x":' + '9' * 5000 + '}').encode()]:
            path.write_bytes(raw)
            result = self.run_cli('check', self.root, path)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertEqual(result.stdout, '')
            self.assertIn('error', json.loads(result.stderr))

    def test_historical_demo(self):
        result = l.demo()
        self.assertTrue(result['live']['all_unchanged'])
        edited = result['layout_edit_in_memory']
        self.assertEqual(edited['status_counts'], {'relocated': 1, 'unchanged': 1})
        self.assertFalse(edited['source_verified'])
        self.assertIn('0xd782bdea4ef02a0bd391eb9089470c8080f0a68e',
                      result['ledger']['entries'][0]['anchor']['text'])
        self.assertEqual(self.run_cli('demo').returncode, 0)


if __name__ == '__main__':
    unittest.main()
