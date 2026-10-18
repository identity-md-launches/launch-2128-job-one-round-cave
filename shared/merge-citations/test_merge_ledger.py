"""Behavioral checks for multi-claim merge review; only workspace scratch writes."""
import copy
import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import merge_ledger as m


class LedgerMerge(unittest.TestCase):
    def setUp(self):
        self.text = 'intro\nZTO\n18 decimals\nend\n'
        self.ledger = {'format': 'citation-ledger/v1', 'entries': [
            {'id': 'token', 'anchor': m.single.anchor_tool.capture_bytes(
                self.text.encode(), 'note.md', 2, 2)},
            {'id': 'units', 'anchor': m.single.anchor_tool.capture_bytes(
                self.text.encode(), 'note.md', 3, 3)}]}
        self.sources = [{'files': {'note.md': t}, 'directories': set()} for t in
                        (self.text, 'heading\n' + self.text, self.text + 'footnote\n')]

    def test_real_historical_evidence_and_context(self):
        report = m.demo()
        self.assertEqual(report['entry_count'], 2)
        self.assertEqual(report['status'], 'ready-for-review')
        warning = report['entries'][1]['review']['candidate_context']
        self.assertIn('not an independent proof', '\n'.join(
            row['text'] for row in warning['context']['lines']))
        self.assertFalse(warning['source_verified'])

    def test_all_claims_share_candidate_and_preserve_inputs(self):
        before = copy.deepcopy((self.sources, self.ledger))
        report = m.inspect(self.sources, self.ledger)
        self.assertEqual((self.sources, self.ledger), before)
        self.assertFalse(report['source_verified'])
        self.assertEqual(report['status_counts'], {'ready-for-review': 2})
        self.assertEqual(len({row['review']['candidate_sha256'] for row in report['entries']}), 1)
        self.assertEqual([row['id'] for row in report['entries']], ['token', 'units'])

    def test_missing_and_duplicate_claims_require_review(self):
        for text, expected in [(self.text.replace('18 decimals', '19 decimals'), 'missing'),
                               (self.text + '18 decimals\n', 'ambiguous')]:
            self.sources[1]['files']['note.md'] = text
            self.sources[2]['files']['note.md'] = self.text
            report = m.inspect(self.sources, self.ledger)
            self.assertEqual(report['status'], 'needs-review')
            self.assertEqual(report['entries'][1]['review']['candidate']['status'], expected)

    def test_unrelated_conflict_blocks_every_claim(self):
        for source, text in zip(self.sources, ['base\n', 'ours\n', 'theirs\n']):
            source['files']['other.md'] = text
        report = m.inspect(self.sources, self.ledger)
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['status_counts'], {'blocked': 2})

    def test_deletion(self):
        self.sources[1]['files'].clear()
        self.sources[2]['files']['note.md'] = self.text
        report = m.inspect(self.sources, self.ledger)
        self.assertEqual(report['status_counts'], {'deleted': 2})
        self.assertEqual(report['status'], 'needs-review')

    def test_forged_anchor_or_duplicate_id_refuses_entire_report(self):
        self.ledger['entries'][1]['anchor']['sha256'] = 'a' * 64
        with self.assertRaises(ValueError):
            m.inspect(self.sources, self.ledger)
        self.ledger['entries'][1]['id'] = 'token'
        with self.assertRaises(ValueError):
            m.inspect(self.sources, self.ledger)

    def test_changed_source_after_batch(self):
        changed = copy.deepcopy(self.sources)
        changed[0]['files']['note.md'] += 'later\n'
        with patch.object(m.single.tree, 'snapshot', side_effect=self.sources + changed):
            with self.assertRaisesRegex(ValueError, 'changed during'):
                m.from_directories(['base', 'ours', 'theirs'], self.ledger)

    def test_output_bound(self):
        with patch.object(m, 'MAX_RESULT_BYTES', 4200):
            with self.assertRaisesRegex(ValueError, 'exceeds'):
                m.inspect(self.sources, self.ledger)

    def test_cli_immutability_errors_and_portability(self):
        Path('test/scratch').mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir='test/scratch') as folder:
            root = Path(folder)
            paths = [root / name for name in ('base', 'ours', 'theirs')]
            for path, source in zip(paths, self.sources):
                path.mkdir()
                (path / 'note.md').write_text(source['files']['note.md'])
            ledger = root / 'ledger.json'
            ledger.write_text(json.dumps(self.ledger))
            before = [p.read_bytes() for p in [ledger, *[r / 'note.md' for r in paths]]]
            args = ['review', *map(str, paths), str(ledger)]
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(m.main(args), 0)
            self.assertTrue(json.loads(out.getvalue())['source_trees_rechecked'])
            self.assertEqual(before, [p.read_bytes() for p in [ledger, *[r / 'note.md' for r in paths]]])
            (paths[1] / 'note.md').write_text(self.text.replace('ZTO', 'missing'))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(m.main(args), 1)
            ledger.write_text('{"format":1,"format":2}')
            with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(m.main(args), 2)
            self.assertEqual(out.getvalue(), '')
            copied = root / 'portable'
            shutil.copytree(Path(m.__file__).parent, copied)
            result = subprocess.run([sys.executable, '-B', str(copied / 'merge_ledger.py'), 'demo'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['entry_count'], 2)


if __name__ == '__main__':
    unittest.main()
