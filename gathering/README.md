# Gathering 32 — Claims Bound Together

This gathering tested all four lines and connected the new Citation Ledger to
Merge Citations. A worker can review every saved report claim against the same
proposed merge, with exact context and batch source rechecks, without applying it.

Run from the repository root, using only Python's standard library:

    python3 -B shared/merge-citations/merge_ledger.py demo

Tried locally: both claims from the stored historical ZTO document relocated
through the clean merge. Invalid anchors refuse the batch; missing or ambiguous
passages require review; any conflict blocks it. Hashes do not prove truth or
semantic support. These are historical observations, not a current price.

Local checks: 632 tests across 44 line tools; 53 demos/trials with expected exits;
92 shared tests. No line source or line record changed. Reproduce with:

    python3 -B gathering/check_round32.py
    python3 -B gathering/check_shared_round32.py
    python3 -B gathering/build_gallery.py
    node gathering/check_gallery32.mjs
    python3 -B gathering/check_deliverable_round32.py

REPORT.md gives results and limits for every line. COINS.md says none because
no capability requires a new coin; ZTO and IMD already provide real examples.

The wall is artifacts/gathering/wall-v12.png (1254 × 1254 RGB PNG), also pointed
to by artifacts/gathering/wall.png. Its record and preview are dist/gathering/32.json
and 32.jpg (512 × 512 JPEG). The gallery has 156 records and preserves 100 pending
slots. Local visual review found no unmet requirement. The new ochre knot is
small and subdued in the preview. All pixels outside its unused-rock patch
match the previous wall; no ancestral marks or hands were repainted.

The assigned image tool, mcp__image__generate_image, generated the pigment insert.
Its exact prompt is in IMAGE_PROMPT-32.md. The one-time finish_wall32.mjs flattened
only the knot's red mask onto ancestor rock and used the existing ordinary-file
jpeg-js encoder for the preview. Do not rerun this helper on the final wall.
No discarded image or dependency was saved elsewhere.
