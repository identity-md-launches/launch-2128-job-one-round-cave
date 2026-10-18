"""Offline checks of collision provenance, scope boundaries and real tree reads."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('bindings', Path(__file__).with_name('bindings.py'))
api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api)


def source(files, directories=()):
    return {'files': files, 'directories': set(directories)}


def compare(base, ours=None, theirs=None):
    return api.inspect([source({'a.py': text}) for text in
                        (base, base if ours is None else ours,
                         base if theirs is None else theirs)])


def collision(text):
    return compare(text)['files'][0]['collisions'][0]


class BindingTests(unittest.TestCase):
    def test_new_combination_demo(self):
        report = api.demo()
        self.assertTrue(report['text_merge_clean'])
        self.assertTrue(report['review_required'])
        item = report['files'][0]['collisions'][0]
        self.assertEqual(item['name'], 'value')
        self.assertEqual(item['classification'], 'new-combination')
        self.assertEqual(item['same_sequence_in'], [])
        self.assertEqual([e['kind'] for e in item['versions']['candidate']],
                         ['import', 'assignment'])
        self.assertEqual([e['line'] for e in item['versions']['candidate']], [1, 5])

    def test_inherited_rebinding_still_needs_review(self):
        item = collision('x = 1\nx = 2\n')
        self.assertEqual(item['same_sequence_in'], ['base', 'ours', 'theirs'])
        self.assertEqual(item['classification'], 'seen-in-branch')

    def test_line_numbers_and_comments_do_not_change_provenance(self):
        base = 'x = 1\nx = 2\n'
        report = compare(base, '# added\n' + base)
        item = report['files'][0]['collisions'][0]
        self.assertEqual(item['same_sequence_in'], ['base', 'ours', 'theirs'])
        self.assertEqual(item['versions']['candidate'][0]['line'], 2)

    def test_import_rules(self):
        for text, name in [('import a.b\na = 1\n', 'a'),
                           ('import a.b as c\nc = 1\n', 'c'),
                           ('from a import b\nb = 1\n', 'b'),
                           ('from .a import b as c\nc = 1\n', 'c'),
                           ('import a, a\n', 'a')]:
            with self.subTest(text=text):
                self.assertEqual(collision(text)['name'], name)

    def test_import_module_identity_part_of_fingerprint(self):
        first = api.inventory('from .a import b\n')['bindings'][0]['events'][0]
        for text in ('from a import b\n', 'from .c import b\n', 'import b\n'):
            other = api.inventory(text)['bindings'][0]['events'][0]
            self.assertNotEqual(first['ast_sha256'], other['ast_sha256'])

    def test_assignments_unpacking_chaining_and_starred(self):
        for text in ('x = y = 1\nx = 2\n',
                     '(x, [y, *rest]) = data\nrest = []\n',
                     'x, x = data\n', 'x: int = 1\nx = 2\n'):
            with self.subTest(text=text):
                self.assertTrue(compare(text)['review_required'])

    def test_annotation_attribute_subscript_not_name_bindings(self):
        text = 'x: int\nobj.x = 1\nobj.x = 2\na[0] = 1\na[0] = 2\n'
        result = api.inventory(text)
        self.assertTrue(result['complete'])
        self.assertEqual(result['bindings'], [])

    def test_function_import_and_class_collisions(self):
        for text in ('import f\ndef f(): pass\n',
                     'x = 1\nclass x: pass\n',
                     'def f(): pass\nasync def f(): pass\n'):
            self.assertEqual(len(compare(text)['files'][0]['collisions']), 1)

    def test_class_scopes_separate_from_module_and_each_other(self):
        text = 'x = 0\nclass C:\n x = 1\nclass D:\n x = 2\n'
        self.assertFalse(compare(text)['review_required'])
        text = 'class C:\n x = 1\n x = 2\n'
        self.assertEqual(collision(text)['scope'], [['C', 1]])

    def test_duplicate_classes_do_not_merge_method_scopes(self):
        text = 'class C:\n def f(self): pass\nclass C:\n def f(self): pass\n'
        result = compare(text)['files'][0]['collisions']
        self.assertEqual([(c['scope'], c['name']) for c in result], [([], 'C')])

    def test_nested_classes(self):
        text = 'class C:\n class D:\n  x = 1\n  x = 2\n'
        self.assertEqual(collision(text)['scope'], [['C', 1], ['D', 1]])

    def test_function_locals_ignored(self):
        text = 'def f():\n x = 1\n x = 2\n if True:\n  def local(): pass\n'
        result = api.inventory(text)
        self.assertTrue(result['complete'])
        self.assertEqual([g['name'] for g in result['bindings']], ['f'])

    def test_unsupported_syntax_is_incomplete(self):
        texts = ('if True:\n x = 1\n', 'for x in []: pass\n',
                 'try:\n x = 1\nexcept Exception: pass\n',
                 'with ctx as x: pass\n', 'from a import *\n',
                 'x += 1\n', 'del x\n', 'print(x := 1)\n',
                 'def f(x=(y := 1)): pass\n')
        for text in texts:
            with self.subTest(text=text):
                report = compare(text)
                self.assertTrue(report['review_required'])
                self.assertEqual(report['files'][0]['status'], 'incomplete')

    def test_branch_incomplete_even_when_candidate_valid(self):
        base = 'if True:\n x = 1\n'
        result = compare(base, 'x = 1\n', 'x = 1\n')['files'][0]
        self.assertEqual(result['status'], 'incomplete')
        self.assertTrue(result['problems']['base'])

    def test_invalid_python_and_bounds(self):
        for text in ('return 1\n', 'def f(a, a): pass\n', 'def (:\n'):
            self.assertFalse(api.inventory(text)['complete'])
        for text in ('x\x00', 'x\n' * 4001, 'x' * (1024 * 1024 + 1)):
            with self.assertRaises(ValueError):
                api.inventory(text)

    def test_never_executes_candidate(self):
        text = 'raise RuntimeError("NEVER_EXECUTE")\nimport nonexistent\n'
        # Raise is unsupported, but it and the import must never run.
        self.assertFalse(api.inventory(text)['complete'])
        self.assertTrue(api.inventory('@missing\ndef f(a=missing()): pass\n')['complete'])

    def test_values_not_disclosed(self):
        result = compare('x = "DO_NOT_ECHO_CONTENT"\nx = 2\n')
        self.assertNotIn('DO_NOT_ECHO_CONTENT', json.dumps(result))

    def test_deleted_missing_empty_and_skipped_files(self):
        result = api.inspect([source({'a.py': 'x = 1\n', 'b.txt': 'hi'}) ,
                              source({'b.txt': 'hi'}), source({'a.py': 'x = 1\n', 'b.txt': 'hi'})])
        self.assertEqual(result['counts']['deleted'], 1)
        self.assertEqual(result['counts']['skipped'], 1)
        self.assertFalse(result['review_required'])
        self.assertTrue(api.inventory(None)['complete'])
        self.assertFalse(compare('')['review_required'])

    def test_conflicts_and_file_directory_collisions(self):
        result = compare('x = 1\n', 'x = 2\n', 'x = 3\n')
        self.assertEqual(result['files'][0]['status'], 'blocked')
        result = api.inspect([source({'a': ''}), source({}, ['a']), source({'a': ''})])
        self.assertTrue(result['review_required'])

    def test_unicode_crlf_and_pyi(self):
        text = 'café = 1\r\ncafé = 2\r\n'
        result = api.inspect([source({'a.pyi': text})] * 3)
        self.assertEqual(result['files'][0]['collisions'][0]['name'], 'café')

    def test_filesystem_cli_and_source_immutability(self):
        scratch = Path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            roots = [Path(folder) / side for side in api.tree.SIDES]
            for root in roots:
                root.mkdir()
                (root / 'a.py').write_bytes(b'x = 1\r\n')
            before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                      for root in roots for p in root.rglob('*') if p.is_file()}
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(api.main([str(p) for p in roots]), 0)
            self.assertFalse(json.loads(out.getvalue())['review_required'])
            self.assertEqual(before, {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                     for root in roots for p in root.rglob('*') if p.is_file()})
            (roots[1] / 'a.py').write_text('x = 1\nx = 2\n')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(api.main([str(p) for p in roots]), 1)
            (roots[1] / 'link.py').symlink_to('a.py')
            with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(api.main([str(p) for p in roots]), 2)
                self.assertEqual(out.getvalue(), '')

    def test_cli_demo_bad_arity_and_workspace_escape(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(api.main(['--demo']), 1)
        self.assertTrue(json.loads(out.getvalue())['text_merge_clean'])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            api.main(['one'])
        for path in ('../escape', '/outside-workspace'):
            with self.assertRaises(ValueError):
                api.from_directories([path] * 3)


if __name__ == '__main__':
    unittest.main()
