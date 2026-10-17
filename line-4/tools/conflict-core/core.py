#!/usr/bin/env python3
"""Reduce finite dependency conflicts and audit their root-removal witnesses."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ENGINE = Path(__file__).resolve().parent.parent / 'offline-resolver' / 'resolve.py'
if not ENGINE.is_relative_to(Path.cwd().resolve()):
    raise RuntimeError('run within the workspace containing this tool')
spec = importlib.util.spec_from_file_location('offline_core_engine', ENGINE)
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)
Invalid = resolver.Invalid


def normalized(data):
    packages, roots = resolver.validate(data)
    return {'packages': packages, 'roots': roots}


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True).encode('ascii')).hexdigest()


def selection(packages, roots, chosen, project=False):
    """Check every reachable edge without searching; optionally discard extras."""
    if not isinstance(chosen, dict):
        raise Invalid('selected versions must be an object')
    for p, v in chosen.items():
        if resolver.name(p) != p or not isinstance(v, str) or v not in packages.get(p, {}):
            raise Invalid('selection contains unknown package or release: ' + p)
    pending = list(roots.items())
    reached = set()
    while pending:
        p, constraint = pending.pop()
        if p not in chosen or not resolver.accepts(chosen[p], constraint):
            raise Invalid('selection fails requirement: ' + p + ' ' + constraint)
        if p not in reached:
            reached.add(p)
            pending.extend(packages[p][chosen[p]].items())
    if not project and reached != set(chosen):
        raise Invalid('selection contains unreachable packages')
    return {p: chosen[p] for p in sorted(reached)}


def budget(value):
    if type(value) is not int or not 1 <= value <= 1_000_000:
        raise Invalid('max_steps must be an integer between 1 and 1000000')


def analyze(data, max_steps=10000):
    """Deletion-based irreducible root core, with one shared search budget.

    Satisfiability is monotone under removal of roots. A successful assignment
    found before later deletions remains a witness after projecting its closure.
    No package constraints or available releases are removed or relaxed.
    """
    budget(max_steps)
    data = normalized(data)
    packages, roots = data['packages'], data['roots']
    steps = calls = 0

    def run(subset):
        nonlocal steps, calls
        if not subset:
            return {'status': 'resolved', 'selected': {}, 'steps': 0}
        if steps >= max_steps:
            return {'status': 'inconclusive', 'reason': 'shared search budget exhausted', 'steps': 0}
        calls += 1
        result = resolver.solve({'packages': packages, 'roots': subset}, max_steps - steps)
        steps += result['steps']
        return result

    initial = run(roots)
    report = {'schema': 1, 'catalog_sha256': digest(data), 'roots': roots,
              'status': initial['status']}
    if initial['status'] == 'resolved':
        report['selected'] = selection(packages, roots, initial['selected'])
    elif initial['status'] == 'inconclusive':
        report['reason'] = initial['reason']
    else:
        core, witnesses, trials = dict(roots), {}, []
        dead_end = initial['conflict']
        minimality, reason = 'irreducible', None
        for p in sorted(roots):
            trial_roots = {q: s for q, s in core.items() if q != p}
            result = run(trial_roots)
            trials.append({'removed_root': p, 'status': result['status'],
                           'steps': result['steps']})
            if result['status'] == 'unsatisfiable':
                core = trial_roots
                dead_end = result['conflict']
            elif result['status'] == 'resolved':
                witnesses[p] = result['selected']
            else:
                minimality, reason = 'inconclusive', result['reason']
                break
        witnesses = {p: selection(packages, {q: s for q, s in core.items() if q != p},
                                 chosen, project=True)
                     for p, chosen in sorted(witnesses.items())}
        report.update(core=core, dropped_roots={p: s for p, s in roots.items() if p not in core},
                      minimality=minimality, removal_witnesses=witnesses, trials=trials,
                      representative_conflict=dead_end,
                      explanation='The core has no solution in this finite catalog. '
                      'Each removal witness satisfies all other core roots. '
                      'Irreducible means no single core root can be removed; '
                      'it does not mean smallest possible core or a suggested repair.')
        if reason:
            report['minimality_reason'] = reason
    report['search'] = {'steps': steps, 'max_steps': max_steps, 'solver_calls': calls}
    return report


def audit(data, report, max_steps=10000):
    """Bind to catalog, verify assignments, and rerun core impossibility search.

    The unsatisfiability check still trusts the inherited solver. This is not a
    separately checkable exhaustive proof or publisher authenticity check.
    """
    budget(max_steps)
    data = normalized(data)
    packages, roots = data['packages'], data['roots']
    if not isinstance(report, dict) or type(report.get('schema')) is not int or report['schema'] != 1:
        raise Invalid('unknown report schema')
    if report.get('catalog_sha256') != digest(data) or report.get('roots') != roots:
        raise Invalid('report does not match this catalog and its roots')
    if report.get('status') == 'resolved':
        selection(packages, roots, report.get('selected'))
        return {'status': 'verified', 'claim': 'resolved', 'assignment_checked': True}
    if report.get('status') != 'unsatisfiable':
        raise Invalid('only resolved or unsatisfiable reports contain an auditable claim')
    core = report.get('core')
    if not isinstance(core, dict) or not core or any(p not in roots or roots[p] != s for p, s in core.items()):
        raise Invalid('core must be a nonempty unchanged subset of original roots')
    if report.get('dropped_roots') != {p: s for p, s in roots.items() if p not in core}:
        raise Invalid('dropped roots do not match the core')
    minimality, witnesses = report.get('minimality'), report.get('removal_witnesses')
    if minimality not in ('irreducible', 'inconclusive') or not isinstance(witnesses, dict):
        raise Invalid('invalid minimality claim or removal witnesses')
    if not set(witnesses) <= set(core) or (minimality == 'irreducible' and set(witnesses) != set(core)):
        raise Invalid('missing or unexpected removal witness')
    for p, chosen in witnesses.items():
        selection(packages, {q: s for q, s in core.items() if q != p}, chosen)
    result = resolver.solve({'packages': packages, 'roots': core}, max_steps)
    if result['status'] == 'resolved':
        raise Invalid('claimed impossible core has a solution')
    if result['status'] == 'inconclusive':
        return {'status': 'inconclusive', 'reason': result['reason'], 'steps': result['steps']}
    return {'status': 'verified', 'claim': 'unsatisfiable', 'minimality': minimality,
            'removal_witnesses_checked': len(witnesses), 'core_search_steps': result['steps'],
            'method': 'Independent assignment checks and inherited-solver core search; '
                      'not an independently certified unsatisfiability proof.'}


def demo_catalog():
    return resolver.load(Path(__file__).parent / 'examples' / 'requests-conflict.json')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    demo = sub.add_parser('demo', help='reduce and audit a real metadata snapshot offline')
    demo.add_argument('--max-steps', type=int, default=10000)
    reduce = sub.add_parser('reduce', help='print a conflict core or compatible assignment')
    reduce.add_argument('catalog')
    reduce.add_argument('--max-steps', type=int, default=10000)
    verify = sub.add_parser('audit', help='check saved report against a workspace catalog')
    verify.add_argument('catalog')
    verify.add_argument('report')
    verify.add_argument('--max-steps', type=int, default=10000)
    args = parser.parse_args(argv)
    try:
        if args.command == 'audit':
            result = audit(resolver.load(args.catalog), resolver.load(args.report), args.max_steps)
            code = 0 if result['status'] == 'verified' else 3
        else:
            data = demo_catalog() if args.command == 'demo' else resolver.load(args.catalog)
            result = analyze(data, args.max_steps)
            code = {'resolved': 0, 'unsatisfiable': 1, 'inconclusive': 3}[result['status']]
            if result.get('minimality') == 'inconclusive':
                code = 3
            if args.command == 'demo' and result['status'] != 'inconclusive':
                checked = audit(data, result, args.max_steps)
                result = {'report': result, 'audit': checked}
                code = 0 if checked['status'] == 'verified' and result['report'].get('minimality') == 'irreducible' else 3
    except (Invalid, OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        result, code = {'status': 'invalid', 'error': str(exc)}, 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return code


if __name__ == '__main__':
    sys.exit(main())
