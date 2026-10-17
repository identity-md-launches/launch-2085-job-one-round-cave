"""Behavioral checks; the small exhaustive oracle does not call the solver."""
import copy
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

from core import Invalid, analyze, audit, demo_catalog, digest, normalized, selection


def brute(packages, roots):
    def accepts(value, spec):
        return spec == '*' or value == spec[2:]
    for values in itertools.product(*[[None] + list(v) for v in packages.values()]):
        chosen = dict(zip(packages, values))
        if any(chosen.get(p) is None or not accepts(chosen[p], s) for p, s in roots.items()):
            continue
        if all(chosen.get(d) is not None and accepts(chosen[d], s)
               for p, v in chosen.items() if v is not None
               for d, s in packages[p][v].items()):
            return True
    return False


class CoreTests(unittest.TestCase):
    def test_real_snapshot(self):
        data = demo_catalog()
        result = analyze(data)
        self.assertEqual(result['core'], {'idna': '>=3.10', 'requests': '==2.25.1'})
        self.assertEqual(set(result['dropped_roots']), {'certifi', 'urllib3'})
        self.assertEqual(result['minimality'], 'irreducible')
        self.assertEqual(result['representative_conflict']['package'], 'idna')
        self.assertIn({'source': 'requests@2.25.1', 'constraint': '>=2.5,<3'},
                      result['representative_conflict']['requirements'])
        self.assertEqual(result['removal_witnesses']['requests'], {'idna': '3.11'})
        self.assertEqual(result['removal_witnesses']['idna']['idna'], '2.10')
        self.assertEqual(audit(data, result)['status'], 'verified')

    def test_random_cores_against_exhaustive_oracle(self):
        rng = random.Random(73722)
        unsatisfiable = 0
        for case in range(350):
            names = ['a', 'b', 'c']
            packages = {p: {v: {q: rng.choice(['*', '==1', '==2'])
                                for q in names if rng.random() < .35}
                            for v in ['1', '2']} for p in names}
            roots = {p: rng.choice(['*', '==1', '==2']) for p in names if rng.random() < .7}
            roots.setdefault('a', '*')
            data = {'packages': packages, 'roots': roots}
            result = analyze(data)
            self.assertEqual(result['status'] == 'resolved', brute(packages, roots), case)
            if result['status'] == 'unsatisfiable':
                unsatisfiable += 1
                core = result['core']
                self.assertFalse(brute(packages, core), case)
                self.assertEqual(result['minimality'], 'irreducible')
                for p in core:
                    reduced = {q: s for q, s in core.items() if q != p}
                    self.assertTrue(brute(packages, reduced), case)
                    selection(packages, reduced, result['removal_witnesses'][p])
            self.assertEqual(audit(data, result)['status'], 'verified')
        self.assertGreater(unsatisfiable, 20)

    def test_single_missing_root_and_empty_witness(self):
        data = {'packages': {}, 'roots': {'absent': '*'}}
        result = analyze(data, 1)
        self.assertEqual(result['core'], data['roots'])
        self.assertEqual(result['removal_witnesses'], {'absent': {}})
        self.assertEqual(result['search']['steps'], 1)
        self.assertEqual(audit(data, result, 1)['status'], 'verified')

    def test_conflict_inside_single_root(self):
        data = {'packages': {'a': {'1': {'b': '==1'}}, 'b': {'1': {'a': '==2'}}},
                'roots': {'a': '*'}}
        result = analyze(data)
        self.assertEqual(result['core'], {'a': '*'})
        self.assertEqual(result['removal_witnesses'], {'a': {}})

    def test_success_and_cyclic_assignment_audit(self):
        data = {'packages': {'a': {'1': {'b': '*'}}, 'b': {'1': {'a': '*'}}},
                'roots': {'a': '*'}}
        result = analyze(data)
        self.assertEqual(result['selected'], {'a': '1', 'b': '1'})
        self.assertEqual(audit(data, result)['claim'], 'resolved')
        result['selected'].pop('b')
        with self.assertRaises(Invalid):
            audit(data, result)

    def test_all_budget_boundaries(self):
        data = demo_catalog()
        full = analyze(data)
        found_partial = False
        for limit in range(1, full['search']['steps'] + 1):
            result = analyze(data, limit)
            self.assertLessEqual(result['search']['steps'], limit)
            if result['status'] == 'unsatisfiable':
                self.assertEqual(audit(data, result)['status'], 'verified')
                found_partial |= result['minimality'] == 'inconclusive'
            else:
                self.assertEqual(result['status'], 'inconclusive')
                self.assertNotIn('core', result)
        self.assertTrue(found_partial)

    def test_depth_inconclusive_without_false_core(self):
        packages = {f'p{i}': {'1': {f'p{i+1}': '*'}} for i in range(202)}
        packages['p202'] = {'1': {}}
        result = analyze({'packages': packages, 'roots': {'p0': '*'}})
        self.assertEqual(result['status'], 'inconclusive')
        self.assertNotIn('core', result)

    def test_determinism_immutability_and_aliases(self):
        data = demo_catalog()
        before = copy.deepcopy(data)
        reversed_data = json.loads(json.dumps(data), object_pairs_hook=lambda p: dict(reversed(p)))
        self.assertEqual(analyze(data), analyze(reversed_data))
        self.assertEqual(data, before)
        aliased = {'packages': {'A_B': {'1': {}}}, 'roots': {'a.b': '*'}}
        self.assertEqual(analyze(aliased)['selected'], {'a-b': '1'})

    def test_nonminimum_core_is_documented(self):
        # Deletion order can retain a size-two core even when another size-one
        # core exists. The tool deliberately claims irreducibility, not minimum.
        data = {'roots': {'a': '*', 'b': '*', 'c': '*'}, 'packages': {
            'a': {}, 'b': {'1': {'shared': '==1'}},
            'c': {'1': {'shared': '==2'}}, 'shared': {'1': {}, '2': {}}}}
        result = analyze(data)
        self.assertEqual(set(result['core']), {'b', 'c'})
        self.assertFalse(brute(data['packages'], {'a': '*'}))

    def test_catalog_tampering_rejected(self):
        data = demo_catalog()
        result = analyze(data)
        data['packages']['requests']['2.25.1']['idna'] = '*'
        with self.assertRaises(Invalid):
            audit(data, result)

    def test_forged_unsatisfiable_claim_rejected_even_with_new_hash(self):
        data = demo_catalog()
        result = analyze(data)
        data['packages']['requests']['2.25.1']['idna'] = '*'
        result['catalog_sha256'] = digest(normalized(data))
        with self.assertRaisesRegex(Invalid, 'has a solution'):
            audit(data, result)

    def test_witness_tampering_rejected(self):
        data = demo_catalog()
        original = analyze(data)
        for mutate in [
            lambda r: r['removal_witnesses'].pop('idna'),
            lambda r: r['removal_witnesses']['idna'].update(idna='3.11'),
            lambda r: r['removal_witnesses']['requests'].update(certifi='2025.10.5'),
            lambda r: r.update(core={}),
            lambda r: r.update(dropped_roots={}),
            lambda r: r.update(schema=True),
        ]:
            result = copy.deepcopy(original)
            mutate(result)
            with self.assertRaises(Invalid):
                audit(data, result)

    def test_audit_budget_cannot_certify(self):
        data = demo_catalog()
        self.assertEqual(audit(data, analyze(data), 1)['status'], 'inconclusive')

    def test_invalid_grammar_and_budgets(self):
        data = demo_catalog()
        for limit in [0, -1, True, 1000001, '1']:
            with self.assertRaises(Invalid):
                analyze(data, limit)
        data['roots']['requests'] = '^2'
        with self.assertRaises(Invalid):
            analyze(data)

    def test_cli_results_and_file_validation(self):
        scratch = Path('test/scratch/conflict-core')
        scratch.mkdir(parents=True, exist_ok=True)
        script = str(Path(__file__).with_name('core.py'))
        def run(*args):
            proc = subprocess.run([sys.executable, '-B', script, *args], capture_output=True, text=True)
            return proc.returncode, json.loads(proc.stdout)
        with tempfile.TemporaryDirectory(dir=scratch) as temp:
            catalog = Path(temp) / 'catalog.json'
            report = Path(temp) / 'report.json'
            catalog.write_text(json.dumps(demo_catalog()))
            code, result = run('reduce', str(catalog))
            self.assertEqual(code, 1)
            report.write_text(json.dumps(result))
            self.assertEqual(run('audit', str(catalog), str(report))[0], 0)
            self.assertEqual(run('audit', str(catalog), str(report), '--max-steps', '1')[0], 3)
            self.assertEqual(run('demo')[0], 0)
            self.assertEqual(run('demo', '--max-steps', '1')[0], 3)
            self.assertEqual(run('reduce', str(catalog), '--max-steps', '2')[0], 3)
            self.assertEqual(run('reduce', str(catalog), '--max-steps', '0')[0], 2)
            catalog.write_text('{"packages":{},"packages":{},"roots":{"x":"*"}}')
            self.assertEqual(run('reduce', str(catalog))[0], 2)
            catalog.write_text(json.dumps({'packages': {'a': {'1': {}}}, 'roots': {'a': '*'}}))
            self.assertEqual(run('reduce', str(catalog))[0], 0)
        self.assertEqual(run('reduce', str(Path.cwd().parent / 'never-read.json'))[0], 2)


if __name__ == '__main__':
    unittest.main()
