"""Offline real ZTO verification and adversarial code/proof bindings."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('code_witness', Path(__file__).with_name('code_witness.py'))
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class CodeWitness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.header, cls.bundle, cls.code = c.demo_inputs()

    def check(self, **changes):
        args = dict(header=self.header, bundle=self.bundle, code_hex=self.code,
                    trusted_hash=c.a.DEMO_HASH, address=c.w.ZTO, slots=['0x0', '0x1'])
        args.update(changes)
        return c.verify(**args)

    def test_real_zto_code(self):
        result = self.check()
        self.assertTrue(result['verified'])
        self.assertEqual(result['code']['byteLength'], 1287)
        self.assertEqual(result['code']['keccak256'],
                         '0x24e03ed7d7d3d6dc010b9a9836e419a3eb4215383b463f4e6685b4816435f16d')
        self.assertEqual(result['code']['storedCodeKind'], 'nonempty')
        self.assertEqual(result['anchor']['blockHash'], c.a.DEMO_HASH)
        self.assertTrue(result['state']['accountExists'])

    def test_tampered_truncated_appended_empty_and_init_code_fail(self):
        raw = c.w.hex_data(self.code)
        variants = [b'', raw[:-1], raw+b'\0', bytes([raw[0]^1])+raw[1:], b'\x60\x00'+raw]
        for raw in variants:
            with self.subTest(length=len(raw)), self.assertRaises(c.w.Invalid):
                self.check(code_hex=c.w.hex0(raw))

    def test_wrong_anchor_address_slots_and_claim_fail(self):
        for changes in ({'trusted_hash': '0x'+'12'*32}, {'address': c.w.POOL_MANAGER},
                        {'slots': []}, {'slots': ['0x0','0x0']}):
            with self.subTest(changes=changes), self.assertRaises(c.w.Invalid):
                self.check(**changes)
        bundle = copy.deepcopy(self.bundle)
        bundle['proof']['codeHash'] = c.w.hex0(c.w.keccak256(b'changed'))
        with self.assertRaises(c.w.Invalid):
            self.check(bundle=bundle, code_hex='0x6368616e676564')

    def test_changed_header_cannot_supply_new_root(self):
        header = dict(self.header, stateRoot='0x'+'12'*32)
        with self.assertRaises(c.w.Invalid):
            self.check(header=header)

    def test_metadata_cannot_supply_code_identity(self):
        bundle = copy.deepcopy(self.bundle)
        bundle.update(source='forged', address='forged', codeHash='forged')
        result = self.check(bundle=bundle)
        self.assertNotIn('forged', json.dumps(result))

    def test_strict_code_format(self):
        for value in (None, 12, [], '6000', '0X6000', '0x0', '0xgg',
                      '0x60 00', '0x00\n', '0x'+'00'*(c.MAX_CODE+1)):
            with self.subTest(value=str(value)[:30]), self.assertRaises(c.w.Invalid):
                c.decode_code(value)
        self.assertEqual(c.decode_code('0x'), b'')
        self.assertEqual(c.decode_code('0xABcd'), bytes.fromhex('abcd'))

    def test_empty_and_delegation_reports_are_only_stored_code(self):
        # Unit isolation: these cases test reporting after the ancestor proof
        # verifier; the real commitment path is exercised in the tests above.
        for raw, exists, kind in [(b'', False, 'empty'), (b'', True, 'empty'),
                                  (bytes.fromhex('ef0100')+c.w.hex_data(c.w.ZTO), True, 'delegation-indicator')]:
            state = {'codeHash': c.w.hex0(c.w.keccak256(raw)), 'accountExists': exists}
            with mock.patch.object(c.a, 'verify', return_value={'state': state, 'trust': ''}):
                result = self.check(code_hex=c.w.hex0(raw))
            self.assertEqual(result['state']['accountExists'], exists)
            self.assertEqual(result['code']['storedCodeKind'], kind)
            self.assertIn('execution behavior are not verified', result['trust'])
            if kind == 'delegation-indicator':
                self.assertEqual(result['code']['delegationTarget'], c.w.ZTO)

    def test_bounded_workspace_file_reader(self):
        for raw in (b'0x00', b'0x00\n'):
            with mock.patch.object(c.w, 'workspace_path') as path:
                path.return_value.open.return_value.__enter__.return_value.read.return_value = raw
                self.assertEqual(c.load_code('unused'), '0x00')
        for raw in (b'0x00\n\n', b'0x00\r\n', b'\xff', b'x'*(2+c.MAX_CODE*2+2)):
            with mock.patch.object(c.w, 'workspace_path') as path:
                path.return_value.open.return_value.__enter__.return_value.read.return_value = raw
                with self.assertRaises(ValueError):
                    c.load_code('unused')
        with self.assertRaises(c.w.Invalid):
            c.load_code(Path.cwd().parent/'outside.hex')

    def test_cli_demo_and_bad_code_fail_without_partial_success(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(c.main(['demo']), 0)
        self.assertTrue(json.loads(out.getvalue())['code']['verified'])
        args = ['verify', str(c.a.HERE/'examples'/'zto-header-mainnet.json'),
                str(c.HERE.parent/'state-witness'/'examples'/'zto-mainnet.json'),
                str(c.HERE/'examples'/'zto-runtime.hex'), '--block-hash', c.a.DEMO_HASH,
                '--address', c.w.ZTO]  # Deliberately missing the required fixture slots.
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(c.main(args), 1)
        self.assertEqual(out.getvalue(), '')
        self.assertFalse(json.loads(err.getvalue())['verified'])


if __name__ == '__main__':
    unittest.main()
