# Binding Review

Find repeated Python names in a freshly recomputed three-way text merge before
one contribution overwrites another at runtime. Direct assignments and imports
are included alongside functions and classes. Interface Review already handles
callable signatures; this tool adds import/assignment collision locations and
compares the ordered binding sequences with the base and both contributors.
Python 3.10+ standard library only. No installation or network needed.

From the repository root, one command shows it working:

```sh
python3 -B line-1/tools/binding-review/bindings.py --demo
```

Expected exit **1**: the text merge is clean, but independent edits rename an
import and a constant to `value`. Each branch binds that name once; the candidate
binds it twice. The JSON lists `new-combination`, both line numbers, binding kinds,
per-version AST hashes, candidate byte hash and source manifests. It never prints
source snippets or assignment values. Names and paths are JSON-escaped.

For three stable workspace trees, in base/ours/theirs order:

```sh
python3 -B line-1/tools/binding-review/bindings.py BASE_DIR OURS_DIR THEIRS_DIR
```

Exit **0** means no findings in the supported subset, **1** means review required
(collision, incomplete inventory or merge conflict), and **2** means invalid or
unsupported filesystem input. An error emits no partial JSON to stdout. No input
is modified, and no candidate is imported, executed, staged or applied. Keep the
sibling `tree-review`, `merge-review` and `threeway` folders with this tool.

## What was tried

All **22 tests passed**:

```sh
python3 -B line-1/tools/binding-review/test_bindings.py
```

Tests cover candidate-only and inherited collisions, import aliases and relative
imports, chained/unpacked/starred assignments, annotation-only declarations,
class and nested class scopes, duplicate classes, ignored function locals,
unsupported control flow, invalid Python, provenance independent of line shifts,
UTF-8/CRLF, deletion, path conflicts, input bounds, CLI exits and input immutability.

An additional real-file trial copies the six inherited Threeway source,
documentation and example files into disposable trees. Two independent edits
make an import alias and a constant share `shared_value`. The text merge stays
clean and the new combination is reported, with unchanged source and input
hashes. The inventory also reports incomplete coverage because the real module
contains control flow, including its main guard. The candidate is never run:

```sh
python3 -B line-1/tools/binding-review/trial.py
```

Recorded observations: `../../REAL-TRIAL-31.json`.

## Limits

A repeated binding is a review prompt, not necessarily a bug: deliberate updates,
overloads, property accessors and repeated package imports can be intentional.
Every collision remains visible, including those inherited from a branch.
`seen-in-branch` means the same ordered kind/AST-hash sequence occurred there;
it does not mean the branch approved it. Changed function bodies can change the
sequence hash. This tool does not detect single-binding semantic changes.

Only direct module/class statements are inventoried. Functions' local scopes are
ignored. Class scopes use lists of `[class_name, occurrence]` pairs, keeping
repeated classes distinct; occurrence counts include previous bindings of that
name. Imports, assignments, definitions and value-bearing annotated assignments
bind names. Bare annotations and attribute/subscript writes do not count.
Conditional/loop/try/with/match statements, wildcard imports, augmented
assignments, deletes and assignment expressions mark the inventory incomplete.
Unsupported syntax is reported even if outside the changed region. Collision
findings remain available when coverage is incomplete. Missing files are empty
inventories; conflicted candidates are blocked, deleted candidates are explicit,
and non-Python files are skipped.

Compilation and AST parsing check syntax without running code. They cannot model
dynamic mutation, decorators, alias relationships, import resolution, inheritance,
control flow or actual values. Passing is not correctness or approval. Python
grammar depends on the current interpreter. SHA-256 is identification, not author
authentication. Bounds inherited from Tree Review: 128 files and 256 directories
per tree, depth 16, 1 MiB/4,000 lines per file and 8 MiB across all three trees.
Only UTF-8 without NUL; no symlinks, binaries, external workspace paths, rename or
permission handling. Reads require stable trusted inputs; no atomic snapshot or
protection against path replacement races. No coin or payment is involved.
