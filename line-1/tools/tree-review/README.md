# Tree review

Review concurrent edits across three small UTF-8 directory trees. This read-only
Python 3.10+ tool combines the existing three-way merger and review packets with
file additions, deletions, path conflicts, and deterministic input manifests.
It uses only the standard library. Keep the sibling `threeway` and `merge-review`
folders when copying it. No installation, network, Git, credentials or coin is needed.

Run from the workspace root:

```sh
python3 -B line-1/tools/tree-review/tree_review.py --demo clean
```

When tried, this returned 0 and kept both contributors' changes in `guide.md`,
retained the newly added `notes.txt`, and explicitly marked `obsolete.txt` deleted.
`--demo conflict` returns 1: one contributor deletes a file that the other edits,
so the report retains the original, edited text and absence for human review.
Neither command writes any files.

For actual trees, replace the three directory arguments with your workspace paths:

```sh
python3 -B line-1/tools/tree-review/tree_review.py BASE_DIR OURS_DIR THEIRS_DIR --format json
```

Use three existing, stable directories inside the current workspace. Select only
the ordinary text files you intend to review; every regular file in those trees
is included. There are no implicit ignore rules. Do not redirect output onto an
input file: the shell would truncate it before this program starts. Capture a
report outside all three input trees if needed.

Exit codes: **0** means no textual or path conflict; **1** means review conflicts;
**2** means invalid inputs or arguments, with no partial report on stdout. A clean
result still requires semantic review. The tool never applies a merge, creates an
output tree, or deletes a file. Its text display quotes input-derived strings to
make terminal controls visible; JSON preserves their exact underlying characters.

## What the report means

`tree-review/v1` contains `clean`, three input manifests, status `counts`, sorted
`path_conflicts`, sorted `files`, and `limits`. Each file has:

- Its relative `path`, and per-side `inputs`: `file` with exact UTF-8 byte SHA-256
  and size, `directory`, or `missing`. An empty file is different from absence.
- A `status`: `unchanged`, `agreed`, `ours`, `theirs`, `merged`, `deleted`,
  `text-conflict`, `delete-modify-conflict`, or `path-conflict`.
- `candidate` and `candidate_sha256` for a clean retained file. The candidate can
  be the empty string. Both fields are null for a deletion or conflict: inspect
  `status` to distinguish them. A conflicted tree may have other clean candidates;
  it must not be treated as an approved complete output tree.
- Both contributors' unified `diffs` against base, with missing-final-newline
  notices. Presence/type metadata disambiguates missing versus empty files.
- A full sibling merge-review `review` packet when differing contributions both
  need text merging; it retains contextual conflicts and all conflicting text.
  Delete/modify and path conflicts instead retain nullable `versions` for each
  side. `blocked_by` names file/directory collisions affecting a path.

If one contributor deletes an unchanged file, the result is a deletion. If the
other edits it, the result is a conflict. Equal additions appear once; different
additions are reviewed against an empty text base. Any file/directory collision
across inputs is conservatively a conflict, including descendants, even where a
human could safely accept a type replacement. Conflict-marker-like input text is
ordinary text; status comes from structured comparisons, not marker detection.

Each manifest hash commits to a JSON mapping of every relative path to its file
fingerprint or directory kind, including empty directories. Encoding is UTF-8,
`ensure_ascii=True`, sorted keys, and compact separators `(',', ':')`. Entries
for files contain `kind`, `sha256`, and `bytes`; directory entries contain only
`kind`. Root folder names are excluded so relocating identical trees retains the
manifest. Manifests are identifiers, not author authentication or snapshots.

## Checks performed

```sh
python3 -B line-1/tools/tree-review/test_tree_review.py
```

All 25 tests passed. They cover clean and conflicting file combinations, empty
versus missing files, file/directory collisions and descendants, exact CRLF and
Unicode fingerprints, literal conflict markers, deterministic manifests, safe
display, symlink/special-file rejection, workspace containment, resource bounds,
CLI statuses and unchanged source bytes. Two hundred seeded text cases agree
with the original merger; presence combinations are also checked symmetrically.
Temporary test data lives in `test/scratch/`.

The 23 original merger tests and 13 existing review tests passed unchanged.
An additional real-file trial copied the inherited merger's six source/example
files into scratch trees, combined two independent README edits, retained a new
file, and marked one removed example as deleted. All three input trees stayed
byte-identical after review. These are local observations, not independent certification.

## Limits

Each tree supports at most 128 regular files, 256 subdirectories and 16 directory
levels. Each file is limited to 1 MiB and 4,000 lines; all three trees together
are limited to 8 MiB. UTF-8 is required; NUL, symlinks, special files, parent
traversal and paths outside the workspace are rejected. Rejection never produces
a partial plan. No binary merge, rename detection, permission merge, empty-folder
merge, automatic conflict resolution or write/apply operation is provided.

Reads require trusted, stable input trees. There is no atomic filesystem snapshot
or defense against a concurrent process swapping paths while the tool reads them.
The inherited line matcher can be ambiguous on repeated text and has quadratic
worst cases; bounds are not a hard execution deadline. The JSON report duplicates
some content for diffs and context, so it can be larger than the source trees.
