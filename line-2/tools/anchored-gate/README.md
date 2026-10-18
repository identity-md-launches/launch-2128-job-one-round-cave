# Anchored Gate

Require a reviewed state policy, a verified execution header, an account/storage
proof and a caller-time age limit to pass together. A worker can use one decision
instead of manually passing a root between separate tools and accidentally
accepting a condition checked against a different checkpoint.

From the repository root, Python 3.9+ and only its standard library:

```sh
python3 -B line-2/tools/anchored-gate/anchored_gate.py demo
```

This verified the inherited **real historical ZTO/IMD pool** witness at Ethereum
block 26,212,390. All four conditions passed: PoolManager account exists, its
stored-code hash matches, the selected pool storage word exists and its exact
uint256 value matches. A **simulated** reference time 60 seconds after the
committed header timestamp passed the inclusive 60-second window. The fixture's
public source is https://ethereum-rpc.publicnode.com; the demo makes no network
request and makes no claim about present pool state, balance or price.

```sh
python3 -B line-2/tools/anchored-gate/anchored_gate.py demo --reject stale
python3 -B line-2/tools/anchored-gate/anchored_gate.py demo --reject condition
python3 -B line-2/tools/anchored-gate/anchored_gate.py demo --reject both
```

These intentionally return **3**, with `verified: true`, `accepted: false`.
`stale` advances the simulated reference time to +61 seconds. `condition` asks
for zero instead of the proven nonzero storage word. `both` reports both reasons.
No conditions or timestamps in the stored ancestor fixtures are changed.

## Checking your own evidence

Use the [State Gate policy schema](../state-gate/README.md) (`state-gate/1`):
explicit account address, account conditions, and exact requested storage slots
with existence or numeric conditions. Input filenames must resolve inside the
current workspace. Policies and headers are bounded to 64 KiB; witnesses to
1 MB, with inherited proof-node and slot limits. Duplicate JSON fields and
unknown policy/header fields fail closed.

After independently reviewing the policy, record its canonical SHA-256:

```sh
python3 -B line-2/tools/anchored-gate/anchored_gate.py fingerprint line-2/tools/state-gate/examples/pool-policy.json
```

This prints `9f9f773cc0c683693b10d5b9a084910eb036ea6de67a73a1f4b50d0e280d2d10`
for the inherited pool policy. The hash is over ASCII JSON with sorted object
keys, no spaces and `ensure_ascii=True`, exactly as in State Gate. Object key
order and whitespace do not matter; array order, casing and string spelling do.
Hashing an unreviewed file does not establish its authority.

Here is the full offline historical check, with concrete fixture inputs:

```sh
python3 -B line-2/tools/anchored-gate/anchored_gate.py check \
  line-2/tools/state-gate/examples/pool-policy.json \
  line-2/tools/header-anchor/examples/zto-header-mainnet.json \
  line-2/tools/state-witness/examples/zto-pool-mainnet.json \
  --block-hash 0x38dc4deb12174972d332cc1f95008b25ea87434f420ce0a51938e1b28755e9dc \
  --policy-sha256 9f9f773cc0c683693b10d5b9a084910eb036ea6de67a73a1f4b50d0e280d2d10 \
  --at 1792241555 --max-age 60
```

For an actual decision, obtain the block hash and chain identity independently,
pin the fingerprint of your reviewed policy and supply a trusted reference time.
Never obtain those trusted inputs solely from the evidence producer. `--at` and
`--max-age` are canonical decimal uint64 seconds; no system clock is read.
The mandatory fingerprint prevents a changed policy from silently weakening
your requested conditions. The header supplies the state root; witness labels
cannot select an address, slot, timestamp or checkpoint.

Exit **0** means every check passed. Exit **3** means valid evidence failed age,
conditions, or both. Exit **1** means invalid/malformed evidence, mismatched policy
fingerprint or an unreadable input; no partial verified result is printed.
Argument syntax errors use argparse exit **2**. Consumers must require
`accepted: true`, not merely `verified: true`.

## Checks and limits

```sh
python3 -B -m unittest discover -s line-2/tools/anchored-gate -p 'test_*.py' -v
```

All **20 tests passed**, covering real pool acceptance, combined rejections,
inclusive age boundaries, future headers, proof/header/address/slot tampering,
weakened policies, canonical fingerprints, ignored metadata, invalid inputs,
immutability and CLI exit codes. Round 32's local trial and check reports live
at `line-2/TRIAL-32.json` and `line-2/CHECKS-32.json`.

Fresh Witness, Header Anchor, State Witness and State Gate are reused unchanged.
The underlying proof is intentionally verified twice, once by Fresh Witness and
once by State Gate, to compose their existing interfaces without trusting a
serialized intermediate report. There are no new runtime packages.

This checks sampled raw storage, not token balances, pool layout, execution,
consensus, canonicality or finality. Header age is not proof capture age and does
not establish current freshness without independently trusted time and checkpoint.
The stored demo checkpoint is an RPC observation, not consensus-authenticated.
No network access, secrets, signing, transaction sending or deployment is used.
