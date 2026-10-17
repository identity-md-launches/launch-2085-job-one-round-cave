"""Offline tests; temporary data is confined to test/scratch/."""
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import tree_review as tr

SCRIPT = str(Path(tr.__file__).resolve())


def tree(files=None, directories=()):
    return {'files': files or {}, 'directories': set(directories)}


def leaf(base, ours, theirs):
    return tr.combine([tree({} if text is None else {'file': text})
                       for text in (base, ours, theirs)])


class TreeTests(unittest.TestCase):
    def test_clean_demo_keeps_all_changes(self):
        report = tr.demo()
        self.assertTrue(report['clean'])
        entries = {e['path']: e for e in report['files']}
        self.assertEqual(entries['guide.md']['candidate'], 'Source: verified-source.txt\nReview: required\n')
        self.assertEqual(entries['notes.txt']['candidate'], 'Keep the source receipt.\n')
        self.assertEqual(entries['obsolete.txt']['status'], 'deleted')
        self.assertIsNone(entries['obsolete.txt']['candidate'])

    def test_delete_modify_retains_versions(self):
        for texts in [('old', None, 'edited'), ('old', 'edited', None)]:
            report = leaf(*texts)
            self.assertFalse(report['clean'])
            entry = report['files'][0]
            self.assertEqual(entry['status'], 'delete-modify-conflict')
            self.assertEqual(entry['versions'], dict(zip(tr.SIDES, texts)))
            self.assertIsNone(entry['candidate'])

    def test_missing_is_not_empty(self):
        report = leaf('old', None, '')
        self.assertFalse(report['clean'])
        self.assertEqual(report['files'][0]['inputs']['ours']['kind'], 'missing')
        self.assertEqual(report['files'][0]['inputs']['theirs']['kind'], 'file')
        for values, status, candidate in [
            ((None, '', None), 'ours', ''), ((None, None, ''), 'theirs', ''),
            (('', None, ''), 'deleted', None), (('', '', None), 'deleted', None),
            (('old', None, None), 'deleted', None), ((None, '', ''), 'agreed', '')]:
            entry = leaf(*values)['files'][0]
            self.assertEqual((entry['status'], entry['candidate']), (status, candidate))

    def test_add_add_conflict(self):
        report = leaf(None, 'one', 'two')
        self.assertFalse(report['clean'])
        entry = report['files'][0]
        self.assertEqual(entry['status'], 'text-conflict')
        self.assertIsNone(entry['candidate'])
        self.assertEqual(entry['review']['conflicts'][0]['base'], '')

    def test_same_addition_once(self):
        entry = leaf(None, 'same', 'same')['files'][0]
        self.assertEqual(entry['candidate'], 'same')
        self.assertEqual(entry['status'], 'agreed')

    def test_literal_conflict_markers_are_not_parsed(self):
        text = '<<<<<<< OURS\n||||||| BASE\n=======\n>>>>>>> THEIRS\n'
        report = leaf('', text, '')
        self.assertTrue(report['clean'])
        self.assertEqual(report['files'][0]['candidate'], text)

    def test_file_directory_collision_blocks_descendants(self):
        report = tr.combine([tree({'a': 'base'}), tree({'a/b': 'new'}, ['a']), tree({'a': 'base'})])
        self.assertFalse(report['clean'])
        self.assertEqual(report['path_conflicts'], ['a'])
        for entry in report['files']:
            self.assertEqual(entry['status'], 'path-conflict')
            self.assertIsNone(entry['candidate'])
            self.assertEqual(entry['blocked_by'], ['a'])
        self.assertEqual(report['files'][0]['inputs']['ours']['kind'], 'directory')

    def test_path_collision_does_not_block_similar_prefix(self):
        report = tr.combine([tree({'a': 'base'}), tree({'a/b': 'new', 'ab': 'okay'}, ['a']), tree()])
        entry = next(e for e in report['files'] if e['path'] == 'ab')
        self.assertEqual(entry['candidate'], 'okay')

    def test_nested_paths_and_deterministic_order(self):
        files = {'z': 'z', 'a/x': 'x', 'é': 'frog'}
        first = tr.combine([tree(files, ['a'])] * 3)
        second = tr.combine([tree(dict(reversed(list(files.items()))), ['a'])] * 3)
        self.assertEqual(first, second)
        self.assertEqual([e['path'] for e in first['files']], sorted(files))

    def test_manifest_covers_content_path_and_empty_directories(self):
        initial = tr.manifest(tree({'a': 'one'}, ['d']))['sha256']
        for changed in [tree({'a': 'two'}, ['d']), tree({'b': 'one'}, ['d']),
                        tree({'a': 'one'}), tree({'a': 'one'}, ['e'])]:
            self.assertNotEqual(tr.manifest(changed)['sha256'], initial)

    def test_crlf_unicode_and_final_newline(self):
        text = '🐸\r\nlast'
        entry = leaf('old', text, 'old')['files'][0]
        self.assertEqual(entry['candidate'], text)
        self.assertEqual(entry['candidate_sha256'], hashlib.sha256(text.encode()).hexdigest())
        self.assertEqual(entry['inputs']['ours']['bytes'], len(text.encode()))
        self.assertIn('No newline at end of file', entry['diffs']['ours'])

    def test_display_escapes_paths_and_contents(self):
        report = tr.combine([tree(), tree({'\x1b[2J\u202e': '\x1b[2J'}), tree()])
        output = tr.render(report)
        self.assertNotIn('\x1b', output)
        self.assertNotIn('\u202e', output)
        self.assertIn('\\u001b', output)

    def test_seeded_file_merge_matches_existing_engine(self):
        rng = random.Random(2301)
        for _ in range(200):
            texts = [''.join(rng.choice(['a\n', 'b\n', '🐸\r\n', 'end'])
                             for _ in range(rng.randrange(12))) for _ in range(3)]
            expected = tr.review.engine.merge(*texts)
            report = leaf(*texts)
            self.assertEqual(report['clean'], expected['clean'])
            entry = report['files'][0]
            if expected['clean']:
                self.assertEqual(entry['candidate'], expected['merged'])
            else:
                self.assertEqual(entry['review']['merged'], expected['merged'])

    def test_all_presence_cases_identity_and_side_symmetry(self):
        for base in (None, '', 'base'):
            for ours in (None, '', 'ours'):
                for theirs in (None, '', 'theirs'):
                    first, second = leaf(base, ours, theirs), leaf(base, theirs, ours)
                    self.assertEqual(first['clean'], second['clean'])
                    if first['clean']:
                        self.assertEqual([e['candidate'] for e in first['files']],
                                         [e['candidate'] for e in second['files']])


class DiskTests(unittest.TestCase):
    def setUp(self):
        Path('test/scratch').mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir='test/scratch')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.paths = [self.root / side for side in tr.SIDES]
        for folder in self.paths:
            folder.mkdir()

    def cli(self, *args):
        return subprocess.run([sys.executable, '-B', SCRIPT, *map(str, args)], capture_output=True)

    def test_real_inputs_unchanged(self):
        values = [b'a\r\nb\r\n', b'A\r\nb\r\n', b'a\r\nB\r\n']
        for folder, value in zip(self.paths, values):
            (folder / 'text').write_bytes(value)
        run = self.cli(*self.paths, '--format', 'json')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)['files'][0]['candidate'], 'A\r\nB\r\n')
        self.assertEqual([(p / 'text').read_bytes() for p in self.paths], values)
        self.assertEqual([sorted(x.name for x in p.iterdir()) for p in self.paths], [['text']] * 3)

    def test_symlinks_rejected_without_following(self):
        (self.paths[0] / 'link').symlink_to(self.paths[1].resolve(), target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            tr.snapshot(self.paths[0], [0])
        with self.assertRaisesRegex(ValueError, 'symlink'):
            tr.snapshot(self.paths[0] / 'link', [0])

    def test_escape_rejected(self):
        with self.assertRaisesRegex(ValueError, 'workspace'):
            tr.snapshot(Path.cwd().parent, [0])
        with self.assertRaisesRegex(ValueError, 'parent traversal'):
            tr.snapshot(self.paths[0] / '..', [0])

    def test_special_file_rejected(self):
        import os
        os.mkfifo(self.paths[0] / 'pipe')
        with self.assertRaisesRegex(ValueError, 'regular'):
            tr.snapshot(self.paths[0], [0])

    def test_invalid_utf8_nul_size_lines(self):
        for data in [b'\xff', b'\x00', b'x' * (tr.review.engine.MAX_BYTES + 1), b'\n' * 4001]:
            (self.paths[0] / 'bad').write_bytes(data)
            with self.assertRaises((UnicodeError, ValueError)):
                tr.snapshot(self.paths[0], [0])

    def test_file_directory_depth_and_total_bounds(self):
        (self.paths[0] / 'a').write_text('abc')
        (self.paths[0] / 'b').write_text('def')
        with patch.object(tr, 'MAX_FILES', 1), self.assertRaisesRegex(ValueError, '128 files'):
            tr.snapshot(self.paths[0], [0])
        with patch.object(tr, 'MAX_TOTAL_BYTES', 5), self.assertRaisesRegex(ValueError, '8 MiB'):
            tr.snapshot(self.paths[0], [0])
        (self.paths[1] / 'a' / 'b').mkdir(parents=True)
        with patch.object(tr, 'MAX_DIRS', 1), self.assertRaisesRegex(ValueError, '256 directories'):
            tr.snapshot(self.paths[1], [0])
        with patch.object(tr, 'MAX_DEPTH', 1), self.assertRaisesRegex(ValueError, '16 levels'):
            tr.snapshot(self.paths[1], [0])

    def test_total_budget_is_shared_across_three_trees(self):
        for folder in self.paths:
            (folder / 'file').write_text('abc')
        with patch.object(tr, 'MAX_TOTAL_BYTES', 8), self.assertRaisesRegex(ValueError, '8 MiB'):
            tr.from_directories(self.paths)

    def test_empty_trees_and_empty_directories(self):
        (self.paths[0] / 'empty').mkdir()
        report = tr.from_directories(self.paths)
        self.assertTrue(report['clean'])
        self.assertEqual(report['files'], [])
        self.assertEqual(report['inputs']['base']['directories'], 1)

    def test_cli_conflict_has_no_publishable_candidate(self):
        for folder, text in zip(self.paths, ['base', 'ours', 'theirs']):
            (folder / 'file').write_text(text)
        run = self.cli(*self.paths, '--format', 'json')
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertIsNone(json.loads(run.stdout)['files'][0]['candidate'])

    def test_cli_invalid_outputs_no_partial_report(self):
        (self.paths[2] / 'bad').write_bytes(b'\xff')
        for args in [[], self.paths[:2], ['--demo', 'clean', *self.paths], self.paths]:
            run = self.cli(*args)
            self.assertEqual(run.returncode, 2, run.stderr)
            self.assertEqual(run.stdout, b'')

    def test_cli_demos(self):
        for kind, code in [('clean', 0), ('conflict', 1)]:
            run = self.cli('--demo', kind, '--format', 'json')
            self.assertEqual(run.returncode, code, run.stderr)
            self.assertEqual(json.loads(run.stdout)['clean'], code == 0)


if __name__ == '__main__':
    unittest.main()
