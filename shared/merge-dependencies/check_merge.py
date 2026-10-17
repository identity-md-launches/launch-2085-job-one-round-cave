#!/usr/bin/env python3
"""Review concurrent catalog edits, then check the merged dependency graph."""
import argparse
import json
from pathlib import Path
import sys

import core
import review

HERE = Path(__file__).resolve().parent


def parse(text):
    def invalid_constant(value):
        raise ValueError('non-finite JSON constant')
    return json.loads(text, object_pairs_hook=core.resolver.unique_object,
                      parse_constant=invalid_constant)


def check(base, ours, theirs, max_steps=10000):
    core.budget(max_steps)
    packet = review.packet(base, ours, theirs)
    result = {'format': 'dependency-merge-review/v1', 'status': 'text_conflict',
              'merge': packet, 'dependencies': None, 'audit': None,
              'limits': [
                  'Review only; no files are applied and no packages are installed.',
                  'Compatibility is confined to this finite numeric-version catalog.',
                  'Audit reuses the inherited solver for impossibility; it is not an independent proof.',
                  'Hashes identify input bytes, not authors or publisher authenticity.']}
    if not packet['clean']:
        return result
    try:
        data = parse(packet['merged'])
        report = core.analyze(data, max_steps)
    except (ValueError, TypeError, RecursionError):
        result['status'] = 'invalid_catalog'
        result['error'] = 'Clean text merge is not a supported dependency catalog.'
        return result
    result['dependencies'] = report
    result['status'] = report['status']
    if report['status'] in ('resolved', 'unsatisfiable'):
        result['audit'] = core.audit(data, report, max_steps)
        if result['audit']['status'] != 'verified' or report.get('minimality') == 'inconclusive':
            result['status'] = 'inconclusive'
    return result


def demo():
    texts = [review.engine.read_text(HERE / 'examples' / (name + '.json'))
             for name in ('base', 'ours', 'theirs')]
    result = check(*texts)
    result['demo_branches'] = {
        name: core.resolver.solve(parse(text))['status']
        for name, text in zip(('base', 'ours', 'theirs'), texts)}
    result['demo_note'] = 'Real Requests metadata snapshot; both branches resolve separately but their clean text merge conflicts on idna.'
    return result


def exit_code(result):
    return {'resolved': 0, 'unsatisfiable': 1, 'text_conflict': 1,
            'invalid_catalog': 2, 'inconclusive': 3}[result['status']]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('demo', help='show a clean merge that breaks real dependency compatibility')
    run = sub.add_parser('check', help='review three workspace catalog files without changing them')
    run.add_argument('base')
    run.add_argument('ours')
    run.add_argument('theirs')
    run.add_argument('--max-steps', type=int, default=10000)
    args = parser.parse_args(argv)
    try:
        result = demo() if args.command == 'demo' else check(
            *(review.engine.read_text(p) for p in (args.base, args.ours, args.theirs)),
            max_steps=args.max_steps)
        code = exit_code(result)
        # The demonstration succeeds when the deliberate incompatibility is found.
        if args.command == 'demo':
            code = 0 if (result['status'] == 'unsatisfiable' and
                         all(v == 'resolved' for v in result['demo_branches'].values()) and
                         result['audit']['status'] == 'verified') else 3
        print(json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False))
        return code
    except (ValueError, OSError, TypeError, RecursionError):
        print(json.dumps({'status': 'invalid', 'error': 'Invalid input files or search budget.'}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
