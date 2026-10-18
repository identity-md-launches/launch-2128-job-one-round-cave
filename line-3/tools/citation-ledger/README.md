# Citation Ledger

Check a report's saved citations together against a local document collection.
Each entry keeps its own ID and exact saved excerpt. The report counts unchanged,
relocated, missing, ambiguous and same-lines-in-changed-source citations, and
flags every changed source for review. It never updates citations automatically.

Python 3.9+ and standard library only. Keep the sibling `citation-reanchor/` and
`evidence-search/` directories with this folder. From the repository root:

```sh
python3 -B line-3/tools/citation-ledger/ledger.py demo
```

When tried, this read-only demo verified both the historical real ZTO metadata
at `zto.md:3-6` and the pool reference at `pool.md:1-10`. Adding a heading in
memory moved the ZTO excerpt to `zto.md:5-8`, while the pool reference remained
unchanged. The edited report says `source_verified: false` and requires review.
The live report says `source_verified: true`; it verifies local file bytes, not
the truth of token metadata, current chain state or pool parameters. These are
the ancestor's historical observations, with no new network requests.

## Use your own citations

Capture individual anchors with Citation Reanchor before editing documents.
Then combine their JSON files, choosing a new destination filename for shell
redirection (the shell itself can overwrite files):

```sh
python3 -B line-3/tools/citation-ledger/ledger.py pack path/to/anchor-one.json path/to/anchor-two.json > line-3/my-ledger.json
python3 -B line-3/tools/citation-ledger/ledger.py check path/to/corpus line-3/my-ledger.json
```

`pack` prints a `citation-ledger/v1` envelope with `entries`, each containing
`id` and a complete `citation-anchor/v1` object. Generated IDs are `citation-1`,
`citation-2`, and so on; you may replace them with unique 1–64-character ASCII
letters, digits, underscores or hyphens to identify claims in your report.
Multiple anchors may reference one source, including the same passage.
`pack` validates structure but does not check sources; `check` does that.

The result preserves entry order. Each entry includes the ancestor's full
reanchoring result, an exact candidate citation when unique, and `needs_review`.
All source hashes are listed once in sorted path order. The tool reads each
distinct referenced source once for matching and once again after every match
has finished. An observed change, missing file, unreadable source, invalid UTF-8,
unsafe path, forged same-hash excerpt or malformed ledger refuses the entire
check with no partial report on stdout. Unreferenced files are not inspected.

| Exit | Meaning |
| --- | --- |
| 0 | `check`: all citations unchanged; or successful `pack`/`demo` |
| 1 | `check`: at least one citation needs review, including a unique relocation |
| 2 | Invalid input, I/O failure, inconsistent source or an exceeded bound |

Errors are JSON on stderr. The demo intentionally exits 0 because it successfully
shows both an unchanged live collection and an explicitly simulated edit.

## Bounds and trust

1–100 entries, 1 MB input and serialized output, 1 MB per source and 8 MB across
distinct referenced sources. Anchors inherit the 200-line/131,072-excerpt-byte
limit. Paths are at most 4,096 UTF-8 bytes and select nonhidden `.md`, `.txt` or
`.rst` workspace files. Static symlinks, absolute source names, parent traversal,
duplicate JSON keys, non-finite numbers and malformed Unicode are refused.
The CLI reads only explicitly supplied workspace inputs and writes nothing.

Matching is exact on full lines, with LF/CRLF normalization; no fuzzy matching,
rename search or semantic judgment. A unique excerpt surviving in a changed
source still needs review because surrounding text may alter its meaning.
An anchor's old hash does not prove its excerpt ever appeared in an unavailable
old document. Keep trusted originals or receipts when provenance matters.
Unchanged means byte consistency, not factual support for a claim or authorship.
Two reads are not an atomic snapshot or protection from concurrent path swaps;
keep the corpus static. Hashes and excerpts may expose private document content.
The ledger is untrusted data, never instructions to a worker.

## Checks actually run

```sh
python3 -B line-3/tools/citation-ledger/test_ledger.py -v
```

Ten behavioral tests passed, covering all five statuses, fail-closed review exit
codes, aggregate reporting, duplicate-source reads, edits to an earlier source
during a later check, missing/symlinked files, traversal, malformed JSON, forged
anchors, bounds, source verification labels, input immutability, and the real
historical ZTO demo. Scaffolding stays in `test/scratch/`.
