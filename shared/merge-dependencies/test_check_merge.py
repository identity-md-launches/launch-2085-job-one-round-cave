"""Exercise the seam between text merging and dependency compatibility."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import check_merge as tool


def encode(data):
    return json.dumps(data, sort_keys=True, indent=2) + '\n'


class IntegrationTests(unittest.TestCase):
    def test_real_clean_text_merge_is_incompatible(self):
        report = tool.demo()
        self.assertTrue(report['merge']['clean'])
        self.assertEqual(set(report['demo_branches'].values()), {'resolved'})
        self.assertEqual(report['status'], 'unsatisfiable')
        self.assertEqual(report['dependencies']['core'],
                         {'idna': '>=3.10', 'requests': '==2.25.1'})
        self.assertEqual(report['audit']['removal_witnesses_checked'], 2)
        self.assertEqual(tool.exit_code(report), 1)

    def test_compatible_change_retained_exactly(self):
        base = encode({'packages': {'app': {'1': {}, '2': {}}}, 'roots': {'app': '==1'}})
        ours = base.replace('"==1"', '"==2"')
        report = tool.check(base, ours, base)
        self.assertEqual(report['status'], 'resolved')
        self.assertEqual(report['merge']['merged'], ours)
        self.assertEqual(report['dependencies']['selected'], {'app': '2'})
        self.assertEqual(report['audit']['status'], 'verified')

    def test_text_conflict_never_enters_solver(self):
        with patch.object(tool.core, 'analyze', side_effect=AssertionError('must not solve')):
            report = tool.check('base\n', 'ours\n', 'theirs\n')
        self.assertEqual(report['status'], 'text_conflict')
        self.assertIsNone(report['dependencies'])
        self.assertIsNone(report['audit'])
        conflict = report['merge']['conflicts'][0]
        self.assertEqual((conflict['base'], conflict['ours'], conflict['theirs']),
                         ('base\n', 'ours\n', 'theirs\n'))

    def test_invalid_clean_text_is_not_compatibility(self):
        for text in ['not json', '{}', '{"packages":{},"roots":{}}',
                     '{"packages":{},"packages":{},"roots":{"x":"*"}}',
                     '{"packages":{},"roots":{"x":NaN}}',
                     '{"packages":{},"roots":{"x":"^1"}}']:
            with self.subTest(text=text):
                report = tool.check(text, text, text)
                self.assertTrue(report['merge']['clean'])
                self.assertEqual(report['status'], 'invalid_catalog')
                self.assertEqual(tool.exit_code(report), 2)

    def test_low_budget_never_claims_impossibility(self):
        texts = [tool.review.engine.read_text(tool.HERE/'examples'/(name+'.json'))
                 for name in ('base', 'ours', 'theirs')]
        result = tool.check(*texts, max_steps=1)
        self.assertEqual(result['status'], 'inconclusive')
        self.assertEqual(tool.exit_code(result), 3)
        self.assertIsNone(result['audit'])

    def test_incomplete_minimization_is_reported(self):
        texts = [tool.review.engine.read_text(tool.HERE/'examples'/(name+'.json'))
                 for name in ('base', 'ours', 'theirs')]
        report = tool.check(*texts, max_steps=2)
        self.assertEqual(report['status'], 'inconclusive')
        self.assertEqual(report['dependencies']['status'], 'unsatisfiable')
        self.assertEqual(report['dependencies']['minimality'], 'inconclusive')

    def test_rejected_audit_does_not_claim_completion(self):
        text = encode({'packages': {'app': {'1': {}}}, 'roots': {'app': '*'}})
        with patch.object(tool.core, 'audit', return_value={'status': 'inconclusive'}):
            self.assertEqual(tool.check(text, text, text)['status'], 'inconclusive')

    def test_strict_budget_and_text_bounds(self):
        for budget in (0, True, 1000001):
            with self.assertRaises(ValueError):
                tool.check('', '', '', budget)
        for text in ('\x00', 'x' * (tool.review.engine.MAX_BYTES + 1)):
            with self.assertRaises(ValueError):
                tool.check(text, text, text)

    def test_determinism_and_side_symmetry(self):
        first = tool.demo()
        self.assertEqual(first, tool.demo())
        texts = [tool.review.engine.read_text(tool.HERE/'examples'/(name+'.json'))
                 for name in ('base', 'ours', 'theirs')]
        swapped = tool.check(texts[0], texts[2], texts[1])
        self.assertEqual(first['dependencies'], swapped['dependencies'])
        self.assertEqual(first['merge']['merged'], swapped['merge']['merged'])

    def test_cli_preserves_inputs_and_statuses(self):
        scratch = Path('test/scratch'); scratch.mkdir(parents=True, exist_ok=True)
        script = str(tool.HERE/'check_merge.py')
        def run(*args):
            return subprocess.run([sys.executable, '-B', script, *map(str, args)], capture_output=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            paths = [Path(folder)/f'{name}.json' for name in ('base', 'ours', 'theirs')]
            for name, path in zip(('base', 'ours', 'theirs'), paths):
                path.write_bytes((tool.HERE/'examples'/(name+'.json')).read_bytes())
            before = [p.read_bytes() for p in paths]
            proc = run('check', *paths)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)['status'], 'unsatisfiable')
            self.assertEqual(run('check', *paths, '--max-steps', '1').returncode, 3)
            self.assertEqual(run('check', paths[0], paths[0], paths[0]).returncode, 0)
            self.assertEqual([p.read_bytes() for p in paths], before)
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()), sorted(p.name for p in paths))
            paths[1].write_bytes(b'\xff')
            invalid = run('check', *paths)
            self.assertEqual(invalid.returncode, 2)
            self.assertEqual(invalid.stdout, b'')
        self.assertEqual(run('demo').returncode, 0)
        self.assertEqual(run('check', '../never-read', '../never-read', '../never-read').returncode, 2)


if __name__ == '__main__':
    unittest.main()
