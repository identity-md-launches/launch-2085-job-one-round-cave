# Conflict Core

Find the root requirements that make a finite dependency catalog impossible to
resolve. The tool removes unnecessary roots, then gives a compatible assignment
for removing each remaining root. This helps a worker isolate a conflicting set
without guessing which requirements to investigate.

From the repository root, run the complete offline demonstration:

```sh
python3 -B line-4/tools/conflict-core/core.py demo
```

The demo returns exit 0 after reducing and auditing a real release-metadata
snapshot. Four initial roots reduce to `requests ==2.25.1` and `idna >=3.10`:
Requests 2.25.1 requires `idna >=2.5,<3`. Removing the idna root allows idna 2.10;
removing the Requests root allows idna 3.11. The certifi and urllib3 roots are
unnecessary to this conflict. Reduction took **15 search states over five solver
calls**; the final core audit took two more states. No network is needed.

This tool uses Python 3.9+ and the standard library, importing the unchanged
adjacent [Offline Resolver](../offline-resolver/README.md). Keep both tool folders
together and run from their containing workspace. It never installs or executes
package code, fetches data, accesses accounts, or sends transactions.

## Your own catalog

Use the inherited resolver's JSON format and numeric version grammar. For example:

```json
{"packages":{"app":{"1":{"shared":"==1"}},"other":{"1":{"shared":"==2"}},"shared":{"1":{},"2":{}}},"roots":{"app":"*","other":"*"}}
```

Save it in the workspace. Reduction writes JSON to stdout. To retain a report,
redirect it to a new file in your workspace:

```sh
python3 -B line-4/tools/conflict-core/core.py reduce path/to/catalog.json > path/to/core.json
python3 -B line-4/tools/conflict-core/core.py audit path/to/catalog.json path/to/core.json
```

The first command exits **1** for an irreducible conflict; that is its expected
result, so do not chain the audit with `&&`. Resolved catalogs return an assignment
with exit 0. Invalid input returns 2. Incomplete search or incomplete minimization
returns 3. Audit returns 0 for a checked claim, 2 for a rejected claim/input, and 3
when its core search cannot finish. The demo wraps a successful reduction and
audit and returns 0 despite its intentionally incompatible roots.

Both commands accept `--max-steps N` (1–1,000,000; default 10,000). Reduction shares
one budget across the initial solve and every deletion trial. Audit has its own
budget. With `demo --max-steps 1`, initial resolution is inconclusive. With
`reduce ... --max-steps 2` on the included example, impossibility is known but
irreducibility is not. The report keeps these two claims separate. Existing depth
and input-size limits also apply; no wall-clock guarantee is claimed.

## What the report proves and what it does not

- `core` is an unchanged subset of the original roots. All catalog versions and
  all transitive dependency constraints are retained. No requirements are edited.
- `minimality: irreducible` means removing **any one** core root permits a
  solution. It does not mean minimum cardinality, a unique conflict, or a proposed
  repair. Another conflict can remain among roots outside this core.
- Each `removal_witnesses` entry gives exactly the reachable selected versions
  for the other core roots. A removed root's package can still be needed
  transitively. Removing the only root has the valid empty assignment.
- Deletion proceeds in canonical package-name order. When later deletions make
  an earlier witness contain irrelevant packages, only its reachable dependency
  closure is retained. Cycles are checked without recursion in the auditor.
- An interrupted reduction retains a known-impossible subset, with
  `minimality: inconclusive`; it never promotes a budget-limited solve to a proof
  of impossibility or a partially checked core to an irreducible one.
- The SHA-256 binds the normalized JSON catalog, including roots. Key order and
  package-name aliases normalize; differently spelled constraints and equivalent
  version strings can still change the digest. It is not a publisher signature.
- Audit checks assignments and every reachable dependency without a search, but
  **reuses the inherited solver to check core impossibility**. It is not an
  independent proof checker. Trial history, performance counts and explanatory
  prose are informational, not claims certified by audit.
- `representative_conflict` retains the inherited solver's failed branch for the
  final core, including dependency sources and constraints. It can help explain
  the conflict, but is still only one branch, not an exhaustive proof; audit does
  not certify this diagnostic field.

These are finite-catalog compatibility results, not an installable lockfile or
version recommendations. The grammar is not full PEP 440. Python versions,
platform markers, extras, artifact hashes and package security remain outside
scope. Adding omitted releases may change a catalog's satisfiability.

## Real data and checks

The example extends the inherited Requests snapshot with public metadata for
[Requests 2.25.1](https://pypi.org/pypi/requests/2.25.1/json),
[idna 2.10](https://pypi.org/pypi/idna/2.10/json), and
[chardet 4.0.0](https://pypi.org/pypi/chardet/4.0.0/json).
They were fetched with the tool's own User-Agent. `examples/sources.json` records
URLs, observation times, the original requirements, and projection limits. Only
unmarked mandatory dependencies enter the example; interpreter requirements and
extras are explicitly excluded. The stored snapshot is sufficient offline.

```sh
python3 -B -m unittest discover -s line-4/tools/conflict-core -p 'test_*.py' -v
```

All 15 tests passed. They include 350 seeded catalogs checked against an
independent exhaustive satisfiability oracle, every demo budget boundary,
missing packages, cycles, empty removal witnesses, non-minimum irreducible cores,
input immutability, tampered reports/catalogs, false impossibility claims, and
CLI exit codes. The original resolver's 17 tests also passed, including its 400
randomized oracle comparisons. Test scratch files stay in `test/scratch/`.
