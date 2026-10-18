#!/usr/bin/env python3
"""Check caller-pinned state conditions and header age under one trusted hash."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent


def sibling(name, path):
    spec = importlib.util.spec_from_file_location(name, HERE.parent / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


f = sibling('fresh_for_anchored_gate', 'fresh-witness/fresh_witness.py')
g = sibling('conditions_for_anchored_gate', 'state-gate/gate.py')
w = f.w
INVALID = (w.Invalid, g.w.Invalid)


def fingerprint(policy):
    """State Gate canonical JSON: key order/whitespace do not affect the hash."""
    g.validate(policy)
    canonical = json.dumps(policy, sort_keys=True, separators=(',', ':'),
                           ensure_ascii=True).encode('ascii')
    w.require(len(canonical) <= g.MAX_POLICY, 'canonical policy exceeds 64 KiB')
    return hashlib.sha256(canonical).hexdigest()


def evaluate(policy, header, witness, block_hash, policy_sha256, at, max_age):
    """Only accept if pinned policy, cryptographic evidence and age all pass.

    Inputs are not mutated. No anchor or expectations come from bundle labels.
    Invalid evidence raises; valid evidence can fail age or state conditions.
    """
    w.require(isinstance(policy_sha256, str) and
              re.fullmatch(r'[0-9a-f]{64}', policy_sha256) is not None,
              'policy SHA-256 must be 64 lowercase hex digits without 0x')
    digest = fingerprint(policy)
    w.require(digest == policy_sha256, 'policy differs from caller-pinned SHA-256')
    fresh = f.evaluate(header, witness, block_hash, policy['address'],
                       [row['slot'] for row in policy['storage']], at, max_age)
    # Only the checked header supplies the root. Reuse State Gate unchanged;
    # its second proof verification is intentional rather than trusting a report.
    gate = g.evaluate(policy, witness, fresh['evidence']['anchor']['stateRoot'])
    w.require(gate['policySha256'] == digest, 'policy fingerprint disagreement')
    reasons = []
    if not fresh['accepted']:
        reasons.append(fresh['reason'])
    if not gate['accepted']:
        reasons.append('state-conditions-failed')
    return {
        'format': 'anchored-gate/1', 'verified': True, 'accepted': not reasons,
        'reasons': reasons, 'policySha256': digest,
        'anchor': fresh['evidence']['anchor'], 'address': gate['address'],
        'age': {key: fresh[key] for key in ('atUnixSeconds', 'maxAgeSeconds',
                                           'headerUnixSeconds', 'ageSeconds')},
        'checks': gate['checks'], 'state': fresh['evidence']['state'],
        'trust': 'Authenticate the block hash, chain, policy fingerprint and reference time '
                 'independently. The policy selects the exact account and slots. This proves '
                 'only sampled state and header timestamp age, not consensus, finality, '
                 'storage layout, present freshness, execution, or future state.',
    }


def demo_inputs():
    policy = g.load_policy(HERE.parent / 'state-gate/examples/pool-policy.json')
    header = f.a.load_header(HERE.parent / 'header-anchor/examples/zto-header-mainnet.json')
    witness = w.load_bundle(HERE.parent / 'state-witness/examples/zto-pool-mainnet.json')
    return policy, header, witness


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    demo = sub.add_parser('demo', help='real historical ZTO/IMD pool; simulated reference time')
    demo.add_argument('--reject', choices=('stale', 'condition', 'both'))
    identify = sub.add_parser('fingerprint', help='validate and fingerprint a reviewed policy')
    identify.add_argument('policy')
    check = sub.add_parser('check', help='require independently trusted caller inputs')
    check.add_argument('policy')
    check.add_argument('header')
    check.add_argument('witness')
    check.add_argument('--block-hash', required=True)
    check.add_argument('--policy-sha256', required=True)
    check.add_argument('--at', required=True, type=f.seconds)
    check.add_argument('--max-age', required=True, type=f.seconds)
    args = parser.parse_args(argv)
    try:
        if args.command == 'fingerprint':
            print(json.dumps({'policySha256': fingerprint(g.load_policy(args.policy))}))
            return 0
        if args.command == 'demo':
            policy, header, witness = demo_inputs()
            if args.reject in ('condition', 'both'):
                policy['storage'][0]['value'] = {'equals': '0'}
            at = int(header['timestamp'], 16) + (61 if args.reject in ('stale', 'both') else 60)
            result = evaluate(policy, header, witness, f.a.DEMO_HASH,
                              fingerprint(policy), at, 60)
            result['demo'] = ('Real historical ZTO/IMD pool proof; simulated reference time '
                              'at header +60 seconds (+61 for stale/both). Demo hash and '
                              'policy are illustrative, not independently authenticated. '
                              'Rejection modes intentionally alter the demo time or policy.')
        else:
            result = evaluate(g.load_policy(args.policy), f.a.load_header(args.header),
                              w.load_bundle(args.witness), args.block_hash,
                              args.policy_sha256, args.at, args.max_age)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result['accepted'] else 3
    except INVALID as error:
        print(json.dumps({'verified': False, 'accepted': False, 'error': str(error)}), file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        print(json.dumps({'verified': False, 'accepted': False,
                          'error': 'Unreadable or malformed policy, header or witness.'}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
