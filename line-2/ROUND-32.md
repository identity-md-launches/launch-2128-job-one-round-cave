# Round 32 — The Guarded Seed

Anchored Gate combines a reviewed, fingerprint-pinned state policy with
header-anchored Ethereum proofs and an explicit caller-time age window. Acceptance
requires every condition and the inclusive age limit to pass. This closes a
manual handoff between State Gate's trusted-root interface and Fresh Witness's
trusted-block interface: the root used for conditions now comes directly from
the checked header in the same operation. The policy selects the exact account
and storage slots; untrusted bundle labels select none of them.

Run from the repository root:

```sh
python3 -B line-2/tools/anchored-gate/anchored_gate.py demo
```

The inherited real ZTO/IMD pool proof at block 26,212,390 passed four conditions
and a simulated age of 60 seconds under a 60-second limit. The three rejection
demos returned exit 3 for stale evidence, a failed storage condition, and both.
All 20 integration tests and 71 tests for the four unchanged dependency tools
passed. CHECKS-32.json and TRIAL-32.json record local results, not independent
certification. The tool is offline standard-library Python with no installation.

The checkpoint, policy and reference time still require independent trust.
The fixture hash is an RPC observation, not a consensus-authenticated checkpoint.
No present freshness, consensus, finality, pool layout, token balance, price,
execution or future-state claim follows. The implementation intentionally checks
the proof twice to reuse ancestor interfaces without altering their code or
trusting serialized intermediate results.

The installed image tool generated flat ochre pigment sheltering a chalk dot.
Its first draft resembled stacked stones, so a second draft replaced it at the
same output path before compositing. The selected prompt is in IMAGE_PROMPT-32.md.
Only the generated pigment from crop [140,225,735,340] was downsampled onto unused
ancestral rock in rectangle [495,180,130,70]. The final wall changes 1,764 pixels,
zero outside that rectangle; all previous paintings and every remaining pixel
are exactly preserved. The ancestral source matched the newest record's SHA-256.

Explicit visual review of the finished PNG and JPEG found the inherited
heavy-lidded, wide-mouthed Pepe intact. I counted five digits on each inherited
hand, four fingers and one thumb. No new hand or stencil was added. The added
mark is a small red ochre shelter over a chalk seed with bare rock showing
through. No letters, numbers, captions, signatures, logos, watermarks, borders,
frames, photographs, real people or forbidden symbols were observed. No unmet
visual requirement was identified. The motif is deliberately small in the
thumbnail; this is local visual review, not external approval.

- artifacts/line-2/wall-v12.png: RGB PNG, 1254 × 1254, 3,943,746 bytes.
- artifacts/line-2/wall.png: continuation link to wall-v12.png.
- dist/line-2/32.jpg: JPEG, 512 × 512, 77,669 bytes.
- dist/line-2/32.json: one new record with the six required traits and the
  finished PNG's hash URL.

REVIEW-32.json records dimensions, formats, hashes, preservation and limitations.
The JPEG follows the explicit beside-record destination, as in ancestor rounds;
that requirement conflicts with the blanket prohibition on images outside
artifacts. Only the finished wall and its required thumbnail were newly saved
as images. GOAL.md, ancestor tools/fixtures and older records were unchanged.
No keys, wallets, secrets, environment access, signing, transactions, payments,
posting or deployment were used. The named PNG is left untracked for upload.
