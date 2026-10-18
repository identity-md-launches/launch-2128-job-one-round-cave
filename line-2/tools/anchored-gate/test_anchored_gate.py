import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('anchored_gate_tests', HERE / 'anchored_gate.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)


class AnchoredGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy, cls.header, cls.witness = t.demo_inputs()
        cls.timestamp = int(cls.header['timestamp'], 16)

    def check(self, policy=None, header=None, witness=None, offset=60, max_age=60,
              block_hash=None, digest=None):
        policy = self.policy if policy is None else policy
        return t.evaluate(policy, self.header if header is None else header,
                          self.witness if witness is None else witness,
                          t.f.a.DEMO_HASH if block_hash is None else block_hash,
                          t.fingerprint(policy) if digest is None else digest,
                          self.timestamp + offset, max_age)

    def test_real_pool_all_requirements_pass(self):
        out = self.check()
        self.assertTrue(out['verified'])
        self.assertTrue(out['accepted'])
        self.assertEqual(out['reasons'], [])
        self.assertEqual(out['address'], t.w.POOL_MANAGER)
        self.assertEqual(out['anchor']['blockHash'], t.f.a.DEMO_HASH)
        self.assertEqual(out['state']['storage'][0]['slot'], t.f.a.POOL_SLOT)
        self.assertTrue(all(row['passed'] for row in out['checks']))

    def test_stale_proof_is_valid_but_not_accepted(self):
        out = self.check(offset=61)
        self.assertTrue(out['verified'])
        self.assertFalse(out['accepted'])
        self.assertEqual(out['reasons'], ['stale-header'])
        self.assertTrue(all(row['passed'] for row in out['checks']))

    def test_future_and_zero_age_boundary(self):
        self.assertEqual(self.check(offset=-1)['reasons'], ['future-header'])
        self.assertTrue(self.check(offset=0, max_age=0)['accepted'])
        self.assertFalse(self.check(offset=1, max_age=0)['accepted'])

    def test_valid_proof_wrong_condition(self):
        policy = copy.deepcopy(self.policy)
        policy['storage'][0]['value'] = {'equals': '0'}
        out = self.check(policy=policy)
        self.assertTrue(out['verified'])
        self.assertFalse(out['accepted'])
        self.assertEqual(out['reasons'], ['state-conditions-failed'])
        self.assertEqual(sum(not row['passed'] for row in out['checks']), 1)

    def test_reports_both_independent_rejections(self):
        policy = copy.deepcopy(self.policy)
        policy['account']['exists'] = False
        out = self.check(policy=policy, offset=61)
        self.assertEqual(out['reasons'], ['stale-header', 'state-conditions-failed'])

    def test_weakened_policy_cannot_reuse_old_fingerprint(self):
        policy = copy.deepcopy(self.policy)
        policy['storage'][0].pop('value')
        with self.assertRaisesRegex(t.INVALID, 'caller-pinned'):
            self.check(policy=policy, digest=t.fingerprint(self.policy))

    def test_wrong_checkpoint_rejected(self):
        with self.assertRaises(t.INVALID):
            self.check(block_hash='0x' + '11' * 32)

    def test_tampered_header_timestamp_rejected(self):
        header = copy.deepcopy(self.header)
        header['timestamp'] = hex(self.timestamp + 60)
        with self.assertRaises(t.INVALID):
            self.check(header=header)

    def test_invalid_proof_cannot_be_reported_as_only_stale(self):
        witness = copy.deepcopy(self.witness)
        witness['proof']['accountProof'] = []
        with self.assertRaises(t.INVALID):
            self.check(witness=witness, offset=61)

    def test_proof_slot_cannot_select_expectation(self):
        witness = copy.deepcopy(self.witness)
        witness['proof']['storageProof'][0]['key'] = '0x1'
        with self.assertRaises(t.INVALID):
            self.check(witness=witness)

    def test_account_cannot_select_expectation(self):
        policy = copy.deepcopy(self.policy)
        policy['address'] = t.w.ZTO
        with self.assertRaises(t.INVALID):
            self.check(policy=policy)

    def test_extra_or_missing_slot_proof_rejected(self):
        for entries in ([], self.witness['proof']['storageProof'] * 2):
            witness = copy.deepcopy(self.witness)
            witness['proof']['storageProof'] = entries
            with self.assertRaises(t.INVALID):
                self.check(witness=witness)

    def test_bundle_labels_do_not_supply_trust(self):
        witness = copy.deepcopy(self.witness)
        witness['block'] = {'timestamp': hex(self.timestamp + 10000), 'stateRoot': 'untrusted'}
        witness['address'] = t.w.ZTO
        witness['slots'] = ['0x1']
        self.assertEqual(self.check(witness=witness), self.check())

    def test_bad_fingerprint_syntax_and_value(self):
        for digest in ('', True, 'a' * 63, 'A' * 64, '0x' + 'a' * 64, '1' * 64):
            with self.assertRaises(t.INVALID):
                self.check(digest=digest)

    def test_canonical_fingerprint_matches_state_gate(self):
        reordered = json.loads(json.dumps(self.policy, sort_keys=True, indent=4))
        self.assertEqual(t.fingerprint(reordered), t.fingerprint(self.policy))
        out = self.check()
        gate = t.g.evaluate(self.policy, self.witness, out['anchor']['stateRoot'])
        self.assertEqual(out['policySha256'], gate['policySha256'])

    def test_invalid_policy_rejected(self):
        for change in ('unknown', 'duplicate', 'empty'):
            policy = copy.deepcopy(self.policy)
            if change == 'unknown':
                policy['trustMe'] = True
            elif change == 'duplicate':
                policy['storage'] *= 2
            else:
                policy['account'], policy['storage'] = {}, []
            with self.assertRaises(t.INVALID):
                self.check(policy=policy)

    def test_invalid_time_types(self):
        for value in (True, -1, '60', 1 << 64):
            with self.assertRaises(t.INVALID):
                self.check(max_age=value)

    def test_inputs_unchanged(self):
        before = copy.deepcopy((self.policy, self.header, self.witness))
        self.check()
        self.assertEqual(before, (self.policy, self.header, self.witness))

    def test_demo_exit_codes(self):
        for mode in (None, 'stale', 'condition', 'both'):
            out = io.StringIO()
            args = ['demo'] + (['--reject', mode] if mode else [])
            with contextlib.redirect_stdout(out):
                code = t.main(args)
            result = json.loads(out.getvalue())
            self.assertEqual(code, 3 if mode else 0)
            self.assertTrue(result['verified'])
            self.assertEqual(result['accepted'], mode is None)

    def test_cli_full_check_and_fingerprint(self):
        p = str(HERE.parent / 'state-gate/examples/pool-policy.json')
        h = str(HERE.parent / 'header-anchor/examples/zto-header-mainnet.json')
        b = str(HERE.parent / 'state-witness/examples/zto-pool-mainnet.json')
        args = ['check', p, h, b, '--block-hash', t.f.a.DEMO_HASH,
                '--policy-sha256', t.fingerprint(self.policy),
                '--at', str(self.timestamp + 60), '--max-age', '60']
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(t.main(args), 0)
        self.assertTrue(json.loads(out.getvalue())['accepted'])
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            args[args.index('--policy-sha256') + 1] = '1' * 64
            self.assertEqual(t.main(args), 1)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(t.main(['fingerprint', p]), 0)
        self.assertEqual(json.loads(out.getvalue())['policySha256'], t.fingerprint(self.policy))


if __name__ == '__main__':
    unittest.main()
