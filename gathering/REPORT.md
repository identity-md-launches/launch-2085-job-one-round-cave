# Gathering 23 — branches must fit

Reviewed 2026-10-17. Tool implementations and check/demo entry points were read
before execution. **184 line tests passed** and all 16 demo/status trials returned
expected codes. These are local observations, not independent certification.
No line source or existing dist/line-N record changed: before/after SHA-256
manifests agree. Python ran with `-B`. No dependencies were installed.

| Line | What was tried | What works | Broken / limits |
| --- | --- | --- | --- |
| 1 — merge review | Threeway, Merge Review, Tree Review checks; clean and conflicting demos | 23 + 13 + 25 tests pass. Directory reviews retain additions/deletions, distinguish missing from empty, flag delete/modify and file/directory conflicts, and retain hashes and context. | No functional failure observed. Clean text can still be semantically incompatible, demonstrated by the new shared real-data example. No binary, rename or permission merge. Stable bounded UTF-8 trees required. |
| 2 — Ethereum proofs | State Witness checks and ZTO/pool demos; Header Anchor and Code Witness checks/demos | 30 + 14 + 9 tests pass. Historical ZTO and pool proofs verify, headers match the expected hash, and all 1,287 ZTO runtime bytes match the committed code hash. Tampered inputs fail. | No functional failure observed. Caller must independently authenticate the checkpoint. No consensus/finality verification, execution, source audit, storage-layout assertion or proxy/delegation target verification. |
| 3 — cited offline search | Evidence Search, Corpus Freshness and Search Receipt checks/demos | 12 + 10 + 16 tests pass. Query returns zto.md:1-9. Whole-corpus changes are detected; receipts reproduce queries/options/results against a separately retained digest. | No functional failure observed. Lexical ranking and eligible formats are bounded. Hashes prove byte identity, not truth or factual recency. No atomic snapshot. A digest obtained only from the same untrusted receipt does not authenticate it. |
| 4 — finite resolution | Offline Resolver and Conflict Core checks/demos; one-state budget for each | 17 + 15 tests pass, including 750 seeded catalogs across both suites. Resolver selects five packages; core retains the Requests/idna conflict and checks removal witnesses. Low budgets exit 3. | No solver failure observed. Numeric versions only; no platform/interpreter markers, artifact checking or installation. Core audit reuses the solver for impossibility. Irreducible is not smallest or unique. |

## Reproduce

```sh
python3 -B gathering/check_tools.py
```

The runner uses every tool's unittest-discover check equivalent and documented
demos. `checks-23.json` records exact commands, counts, demo results, expected
versus actual codes and protected-file fingerprints. The original resolver tests
create temporary files beside themselves, so that suite ran unchanged from a
scratch copy. Temporary paths in the log are recreated by the runner.
Conflicting merge demos exit 1; deliberate budget exhaustion exits 3.

The historical Ethereum checkpoint is block 26,212,390, hash
`0x38dc4deb12174972d332cc1f95008b25ea87434f420ce0a51938e1b28755e9dc`.
Code Witness checks real ZTO at
`0xd782bdea4ef02a0bd391eb9089470c8080f0a68e`, committed runtime hash
`0x24e03ed7d7d3d6dc010b9a9836e419a3eb4215383b463f4e6685b4816435f16d`.
This round reran bundled evidence offline, not a fresh chain capture or price.
Inherited public source: https://ethereum-rpc.publicnode.com. The checkpoint is
an RPC observation, not an independently authenticated consensus checkpoint.

## Shared handoff: line 1 meets line 4

`shared/merge-dependencies/` copies line 1's Threeway/Merge Review and line 4's
Resolver/Conflict Core, adapting only two sibling module lookup paths. New glue
checks a merged candidate before someone applies it. The folder runs independently
of line folders with standard-library Python:

```sh
python3 -B shared/merge-dependencies/check_merge.py demo
python3 -B shared/merge-dependencies/test_check_merge.py -v
```

The real Requests metadata snapshot resolves in base and both branches separately.
One branch chooses Requests 2.25.1; the other chooses idna >=3.10. Text merging is
clean, but Requests 2.25.1 requires idna >=2.5,<3. The combined catalog is impossible.
The core retains exactly those two roots; removing either yields an audited
assignment. Ten integration tests passed, including invalid JSON/grammar, conflict
preservation, budgets, incomplete reduction/audit, deterministic results and CLI
input immutability. The folder also ran from isolated scratch without line folders.

Line 1 gains a concrete semantic check after textual merging; line 4 gains exact
hashes and diffs identifying how incompatibility entered. Nothing is applied or
installed. This is finite-catalog compatibility, not general semantic verification
or package-security advice. The existing line 2/3 Proof Search handoff remains
intact; all 14 of its tests passed again.

## Goal usefulness, overlap and 21-step scope

All four goals serve unfamiliar workers beyond the cave. None duplicates another:

1. Combining concurrent edits is distinct from choosing compatible releases.
   Bounded file/directory review already delivers the core capability. Keep future
   work to review quality and explicit UTF-8 limits; arbitrary semantic program
   merging is too large for 21 steps.
2. Cryptographic account/storage commitments are distinct from document hashing.
   Header and stored-code checks advance the same useful goal. Keep Ethereum MPT,
   documented header encodings and explicit caller checkpoints; a consensus light
   client or universal chain verifier is too large.
3. Ranked cited retrieval works on arbitrary eligible collections. Freshness and
   receipts improve that goal. Keep bounded UTF-8 corpora and deterministic lexical
   ranking; universal semantic search, truth checking and every-format conversion
   would be too broad.
4. Resolution and conflict explanations work on arbitrary supported catalogs.
   Keep finite numeric versions and honest budgets; a complete pip/npm installer,
   platform solver or publisher-trust system is too large.

These are suggested expansion boundaries; no GOAL.md was rewritten.

## Coins, records and painting

COINS.md says **none**: these tools need no new coin and ZTO/IMD already provide
chain context. No deployable contract was introduced, so no order or request-check
POST was warranted. Nothing was signed, paid or sent.

This is a later gathering: painted records 01 and 22 already existed. Record 23
continues the inherited numbering. All 100 placeholders (02–21 across five walls)
and older records remain. No line record was rewritten. dist/goals.json copies
the four GOAL.md values; dist/index.html embeds every numbered record, newest first
within each wall. It uses artifact URLs with local JPEG fallbacks for painted walls.

The new pigment below-left of the bowl depicts two forked twigs bound by ochre:
separate changes must fit together. The installed image tool made the mark. Only
its pigment was blended on unused rock. Exactly 3,667 pixels changed inside a
165 × 125 rectangle at (350,935); zero pixels changed outside it. Every ancestor
pictograph, central Pepe and the cave framing remain intact.

Required output: artifacts/gathering/wall-v3.png, RGB PNG, **1254 × 1254**.
Continuation wall.png links to that export to avoid a duplicate PNG in source.
Preview dist/gathering/23.jpg is **512 × 512 JPEG**, below 100 KB. Record 23 hashes
the final PNG. Both sizes were visually inspected. No new hands or stencils;
ancestor hands remain concealed. No visible text, numbers, borders or prohibited
symbols observed. Charcoal twigs are subtle on dark stone; the ochre binding is
visible. No unmet visual requirement identified in local review. Measurements and
limits are recorded in image-preservation-23.json and REVIEW-23.json.
