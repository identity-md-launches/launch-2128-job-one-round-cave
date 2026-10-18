#!/usr/bin/env python3
"""Review repeated direct Python bindings in a recomputed three-way merge."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

SPEC = importlib.util.spec_from_file_location(
    'binding_tree', Path(__file__).resolve().parents[1] / 'tree-review' / 'tree_review.py')
tree = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tree)
LIMITS = [
    'Repeated bindings are review prompts, not proof of a bug or lost runtime value.',
    'Only direct module and class bindings are inventoried; function bodies are ignored.',
    'Conditional/loop/try/with/match statements, wildcard imports, deletes, augmented '
    'assignments and assignment expressions make an inventory incomplete.',
    'Attribute/subscript writes and annotation-only declarations do not bind names here.',
    'No execution, import resolution, control-flow, decorator, inheritance or alias analysis.',
    'AST hashes identify syntax, not values or authors. Line numbers do not affect comparison.',
    'An inherited collision is still reported; branch presence is not approval.',
    'Bounded stable UTF-8 workspace trees; no atomic snapshot or race protection.']


def inventory(text):
    """Return ordered binding events keyed by unambiguous lexical scope and name."""
    if text is None:
        return {'complete': True, 'bindings': [], 'problems': []}
    tree.validate_text(text)
    try:
        compile(text, '<binding-input>', 'exec', dont_inherit=True)
        module = ast.parse(text, filename='<binding-input>')
    except SyntaxError as error:
        return {'complete': False, 'bindings': [], 'problems': [
            {'kind': 'syntax-error', 'line': error.lineno, 'column': error.offset}]}
    except (ValueError, OverflowError, RecursionError):
        return {'complete': False, 'bindings': [], 'problems': [{'kind': 'parser-limit'}]}
    groups, problems = {}, []

    def problem(node, scope, kind):
        problems.append({'kind': kind, 'scope': list(scope), 'line': node.lineno})

    def bind(name, node, scope, kind, syntax=None):
        key = (scope, name)
        digest = hashlib.sha256((syntax if syntax is not None else
            ast.dump(node, include_attributes=False)).encode('utf-8')).hexdigest()
        groups.setdefault(key, []).append({'kind': kind, 'line': node.lineno,
                                          'ast_sha256': digest})

    def target(node, statement, scope):
        if isinstance(node, ast.Name):
            bind(node.id, statement, scope, 'assignment')
        elif isinstance(node, (ast.Tuple, ast.List)):
            for child in node.elts:
                target(child, statement, scope)
        elif isinstance(node, ast.Starred):
            target(node.value, statement, scope)

    def visit(body, scope):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                bind(node.name, node, scope, 'class' if isinstance(node, ast.ClassDef)
                     else 'async-function' if isinstance(node, ast.AsyncFunctionDef) else 'function')
                # Repeated class names must not conflate their distinct method scopes.
                if isinstance(node, ast.ClassDef):
                    occurrence = len(groups[(scope, node.name)])
                    visit(node.body, scope + ((node.name, occurrence),))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    if alias.name == '*':
                        problem(node, scope, 'wildcard-import')
                    else:
                        name = alias.asname or (alias.name.split('.')[0]
                                               if isinstance(node, ast.Import) else alias.name)
                        syntax = ast.dump(alias, include_attributes=False)
                        if isinstance(node, ast.ImportFrom):
                            syntax = repr((node.level, node.module)) + syntax
                        bind(name, node, scope, 'import', syntax)
            elif isinstance(node, ast.Assign):
                for item in node.targets:
                    target(item, node, scope)
            elif isinstance(node, ast.AnnAssign):
                if node.value is not None:
                    target(node.target, node, scope)
            elif not isinstance(node, (ast.Expr, ast.Pass)):
                problem(node, scope, 'unsupported-statement:' + type(node).__name__)
            # Assignment expressions can bind names inside expressions/defaults/bases.
            # Do not traverse function bodies, which belong to ignored local scopes.
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                expressions = [node.args, *node.decorator_list]
                if node.returns:
                    expressions.append(node.returns)
            elif isinstance(node, ast.ClassDef):
                expressions = [*node.bases, *node.keywords, *node.decorator_list]
            else:
                expressions = [node]
            if any(isinstance(child, ast.NamedExpr) for expression in expressions
                   for child in ast.walk(expression)):
                problem(node, scope, 'assignment-expression')

    visit(module.body, ())
    bindings = [{'scope': [list(part) for part in scope], 'name': name, 'events': events}
                for (scope, name), events in sorted(groups.items())]
    return {'complete': not problems, 'bindings': bindings, 'problems': problems}


def keyed(version):
    return {(tuple(tuple(part) for part in group['scope']), group['name']): group['events']
            for group in version['bindings']}


def event_signature(events):
    return [(event['kind'], event['ast_sha256']) for event in events]


def inspect(sources):
    if len(sources) != 3:
        raise ValueError('exactly three source trees are required')
    packet = tree.combine(sources)
    files = []
    for entry in packet['files']:
        name = entry['path']
        item = {'path': name, 'merge_status': entry['status'],
                'candidate_sha256': entry['candidate_sha256']}
        if entry['status'].endswith('conflict'):
            item['status'] = 'blocked'
        elif entry['candidate'] is None:
            item['status'] = 'deleted'
        elif Path(name).suffix not in ('.py', '.pyi'):
            item['status'] = 'skipped'
        else:
            versions = {side: inventory(source['files'].get(name))
                        for side, source in zip(tree.SIDES, sources)}
            versions['candidate'] = inventory(entry['candidate'])
            maps = {side: keyed(version) for side, version in versions.items()}
            collisions = []
            for key, events in maps['candidate'].items():
                if len(events) < 2:
                    continue
                occurrences = {side: mapping.get(key, []) for side, mapping in maps.items()}
                same = [side for side in tree.SIDES if
                        event_signature(occurrences[side]) == event_signature(events)]
                collisions.append({'scope': [list(part) for part in key[0]], 'name': key[1],
                                   'classification': 'seen-in-branch' if any(
                                       side in same for side in ('ours', 'theirs'))
                                       else 'new-combination',
                                   'same_sequence_in': same, 'versions': occurrences})
            complete = all(version['complete'] for version in versions.values())
            item.update(status='incomplete' if not complete else
                        'review' if collisions else 'checked', complete=complete,
                        collisions=collisions,
                        problems={side: version['problems'] for side, version in versions.items()})
        files.append(item)
    counts = {status: sum(item['status'] == status for item in files)
              for status in ('blocked', 'deleted', 'skipped', 'incomplete', 'review', 'checked')}
    return {'schema': 'binding-review/v1', 'review_required': any(counts[status] for status in
            ('blocked', 'incomplete', 'review')), 'text_merge_clean': packet['clean'],
            'inputs': packet['inputs'], 'counts': counts, 'files': files, 'limits': LIMITS}


def from_directories(paths):
    if len(paths) != 3:
        raise ValueError('exactly three source directories are required')
    budget = [0]
    return inspect([tree.snapshot(path, budget) for path in paths])


def demo():
    base = 'from decimal import Decimal as amount\n\n# separate contributions\n\nlimit = 10\n'
    return inspect([{'files': {'prices.py': text}, 'directories': set()} for text in
                    (base, base.replace('as amount', 'as value'),
                     base.replace('limit =', 'value ='))])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='*', help='BASE_DIR OURS_DIR THEIRS_DIR')
    parser.add_argument('--demo', action='store_true')
    args = parser.parse_args(argv)
    if args.demo and args.paths or not args.demo and len(args.paths) != 3:
        parser.error('provide three source trees or --demo')
    try:
        report = demo() if args.demo else from_directories(args.paths)
    except (OSError, UnicodeError, ValueError, RecursionError, OverflowError) as error:
        print('binding-review: ' + ascii(str(error)), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 1 if report['review_required'] else 0


if __name__ == '__main__':
    sys.exit(main())
