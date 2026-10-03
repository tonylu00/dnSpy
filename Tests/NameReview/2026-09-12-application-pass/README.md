# ETS 6.3 / 6.4 naming pass — checkpoint sink

This directory holds the machine-readable records. It is not the state document.

Read first:

- `D:\knx_analysis\STATE.json` — current maps, hashes, coverage, backlog, next items
- `D:\knx_analysis\POLICY.md` — compatibility policy
- `D:\knx_analysis\PLAYBOOK.md` — pipeline, gates, evidence routes, working rules

What lives here:

- `progress.json` — tool-facing record of the current map paths and checkpoint
- `reviewed63.json` — cumulative behavioural review ledger (the row-level evidence)
- `checkpoint-waveNNN.json`, `checkpoint64-vN.json` — accepted per-block records
- `map-update63.json`, `devkit*63-review-check.json` — last update/check reports
- `archive/` — the former handoff and README journals (history; do not read to resume)

Rules:

- One block = one evidence-backed review and inexpensive map/reference checks.
  `checkpoint_naming_block.py --review-only` also records explicit preservation or
  unresolved decisions when native update/check reports prove the map is byte-identical.
  It rejects aliases and map changes and keeps the current map/version in place.
  Commit validated milestones; defer full `--wave` audits/application and ETS
  export/build until application-wide mapping freezes.
- No per-block narrative, no commit-hash prose, no wave reports. `git log` is the log.
- `AppliedToSource` stays `false` until the consolidated Phase 4 export/build/verification.
  Metadata apply and `--verify-applied` do not prove source rebuilding or ETS runtime behaviour.

For scoped additions to previously reviewed methods, run `checkpoint_naming_block.py`
with `--merge-reviewed-scopes` after the native update and check gates. It preserves
earlier parameter/local aliases and verifies physical identity. Locals absent from an
older ledger require matching entries in the native-checked map.
`--replace-reviewed-aliases` additionally permits explicit field/type/method/parameter
corrections only when the native change report records the exact previous and new
aliases. Method corrections retain earlier scope aliases and annotations; every
retained or newly added scope alias must match the native-checked map. These options
edit review records; they do not modify ETS source or binaries.
The merge guards can be verified with `python test_review_ledger.py`.

`prepare_physical_review.py --spec <spec.json> --output <fresh-review.json>`
normalizes native inventory roots to exact application-relative physical paths
and validates current hashes. Specs support evidence-backed aliases, explicit
preservation and unresolved decisions; unresolved rows cannot carry aliases.
It writes review JSON only. Run `python test_physical_review.py` for its guards.
Native `--update-map` and `--check-map` remain required before checkpointing.

Native coverage validates current physical identities and scoped metadata.
For legacy missing method owners or field signatures stored in `Type`, use native
`--normalize-review-owners <review> <fresh-review> <fresh-report>` before coverage.
It verifies exact bytes/definitions/scopes and preserves all naming decisions;
strict coverage still rejects arbitrary or stale owner annotations.
Its `NotFlagged` count means the inventory did not request a readable name;
it is not evidence of a completed behavioral review. Selected inventories
measure their supplied rows only, not application-wide scope or compatibility.

`inventory_physical_scope.py --scope <physical-scope.json> --cli <NameCandidates.dll>`
`--map <checked-map.xml> --ledger <reviewed.json> --output <fresh-directory>`
measures every definition in an explicit physical module scope using native
inventories. Modules run sequentially and retain one native report at a time.
It reports unreviewed native candidates separately from mapped, preserved and
unresolved rows, plus total and aliased parameter/local positions. Unflagged
names and missing scoped aliases do not establish readability or obfuscation.
`--reuse-inventory <earlier-summary.json>` reuses native reports only after their
hashes, scope, tool and current physical identities are checked again.
`UnappliedLedgerAlias` separates historical proposals absent from the checked map
from applied names and newly unreviewed definitions. Keep those proposals as
history; whitelist/family exclusions must not become applied aliases in counts.
Review preparation retains only requested definitions from native inventories;
all inventory-root and physical-path escape guards still apply.

For a corrected rationale, `checkpoint_naming_block.py --review-only`
`--refresh-reviewed-evidence` requires `PreviousEvidence` with the exact previous
`Reason` and `UnresolvedReason`. It preserves every naming decision and physical
identity; native update/check must prove a byte-identical map. Arbitrary ledger
overwrites and stale rationale preimages remain rejected.
