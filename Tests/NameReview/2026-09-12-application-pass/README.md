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
- `physical-source-context-verification.json` — pinned preparation, source-context
  guards, mapped SDK AST observations and explicit missing dependency identities
- `generated-source-scope-verification.json` — native whole-scope observation audit
  and read-only structural candidate joins, with no naming retirement verdict
- `printed-reference-verification.json` — token-writer bindings and targeted mapped-source verification
- `iterator-region-order-verification.json` — 39 exact iterator-owner witnesses,
  synthetic cleanup traces, actual CvNext source compilation and unchanged-caller probes
- `session-status-scoped-withdrawal-verification-v434.json` — native atomic
  withdrawal of an unsupported callback definition alias with four proven new
  body scopes. Every other alias and decision is retained. Full native checks,
  65 focused assertions, 158 portable tests and 109 cached joins pass; printed
  ownership and consolidated ETS build/runtime compatibility remain pending.
- `secure-session-definition-corrections-verification-v433.json` — session-key
  getter, full secure-handshake overload and exact connect/disconnect predicate
  corrections, with every other alias/scope/decision retained. Native SDK/contract
  checks and 109 cached joins pass; validated portable helpers remain unchanged.
- `secure-session-handshake-send-keepalive-coverage-v432.json` — secure key
  exchange, server/user authentication, connection setup, serialized sending,
  disposal and timer keepalive chains; 379 exact aliases with prior names retained.
  Twenty-two generated definitions stay unresolved pending printed owner evidence.
  SDK/contract checks, 150 portable tests and 109 cached joins pass; 20,823
  candidates remain. Consolidated ETS export/build/runtime checks are pending.
- `connection-description-alias-correction-verification-v431.json` — replaces
  historical `ToString2` with `GetConnectionDescription` from endpoint/channel
  formatting, checking distinct ledger/map preimages. Original `ToString` and
  all other aliases/scopes/decisions are retained; SDK/contract checks, 150
  portable tests and 109 cached joins pass. Consolidated ETS checks are pending.
- `record_method_alias_corrections.py` — reusable correction evidence recorder
  with explicit preimages and guards against unintended alias/scope/ledger edits.
- `ip-connection-request-response-coverage-v430.json` — connection setup,
  request/response listeners, disconnect/disposal, device-management properties
  and tunneling features; 300 exact aliases with prior names retained. Reconnect
  and deferred-request dispatch prove the wakeup message role. Twenty-six
  generated/accessor definitions remain explicitly unresolved. SDK/contract,
  143 portable tests and 109 cached joins pass; 20,951 candidates remain.
  Consolidated ETS export/build, printed ownership and runtime checks are pending.
- `layer-timer-connectionless-dispatch-coverage-v429.json` — shared layer timers,
  worker dispatch, message/event interfaces and connectionless/local transports;
  153 exact aliases with all prior names retained. Synthetic event provenance is
  checked through disconnect producers, confirmation forwarding and waiter error
  branches. Seven definitions remain explicitly unresolved, including a redundant
  diagnostic field whose invented collision suffix was rejected. SDK/contract
  checks, 143 portable tests and 109 cached joins pass; 21,057 candidates remain.
  Consolidated ETS export/build, printed ownership and runtime checks are pending.
- `scoped-generated-alias-withdrawal-verification-v428.json` — removes the
  unsupported listener `set_LocalIPAddress` alias with exact map/ledger preimages,
  retaining the known `message` scope and explicit owner uncertainty. Native
  commit 1276712b passes the full suite/33 focused assertions; 143 portable
  checks and 109 cached joins pass. Previous helper snapshots resolve historical
  proof bindings; consolidated ETS verification remains pending.
- `application-layer-confirmed-service-coverage-v427.json` — complete application-layer
  contracts, ordinary request contexts, timeout helpers and remote/local
  acknowledgement, response, security, reconnect and translation chains;
  470 actual aliases, all prior names retained, 109 cached joins, 24 generated
  definitions explicitly unresolved; consolidated ETS verification pending.
- `retained-definition-verification-v427.json` — native updater commit 1cf93161
  preserves restated family/ordinary aliases while validating new scopes;
  unchanged ETS map bytes, exact edit counts, full native suite, 19 focused
  assertions and 140 portable checks pass. Primary tool integration pending.
- `local-management-usb-feature-coverage-v426.json` — local-interface property,
  response/timeout/cancellation/readback chains and USB feature/configuration/RF/PL scopes.
- `definition-only-scopes-verification-v426.json` — guarded native scope aliases
  on explicitly unresolved definitions, regression cases and historical helper bindings.
- `usb-bus-connector-coverage-v425.json` — USB open/discovery/disposal/reset
  storage and complete connector-match/local-management send/register/remove families.
- `parameter-original-name-count-verification-v425.json` — native metadata-name
  preservation counts, real alias restoration and actual Falcon replay.
- `usb-interface-body-coverage-v424.json` — USB feature/read/write/reconnect body
  scopes, preserved definition identities and explicit unresolved evidence
- `record_additive_naming_block.py` — reusable additive-block evidence recorder;
  verifies native reports, preserved aliases and cached whole-scope joins
- `ip-connection-layer-coverage-v423.json` — IP connection transitions, sequence
  handling, retries, frame envelopes and unresolved generated-owner evidence
- `asynchronous-state-transition-coverage-v422.json` — shared transition helper
  naming checkpoint, exact IP/link/USB callers and unresolved owner evidence.
- `link-layer-coverage-v421.json` — physical queue, timing, filtering and
  confirmation-chain naming checkpoint and unresolved evidence.
- `connection-oriented-transport-coverage-v419.json` — physical transport-chain
  decisions, complete interface families, native checks and whole-scope joins
- `transport-alias-correction-verification-v420.json` — exact historical method
  corrections with preserved scopes and checked ledger/map preimages

Rules:

- `managed-body-scope-verification-v418.json` pins the protected managed-body
  scope fix, explicit-method parameter restoration and awaited-result source
  identity transfer. Current validated tools live on isolated
  `tonycloud/protected-body-scopes` branches (paths and commits in that proof).
  Integrate them without overwriting the parallel primary-checkout changes.
  Scope-only aliases preserve method names and families; the SDK whitelist and
  physical token/type/name/hash/MVID guards still apply. The v418 lexical worklist
  reuses exact old-tool inventory flags and rejoins the current map/ledger; the
  changed Falcon scope eligibility has a fresh new-tool inventory and preflight.

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

For an unsupported standalone method alias, prepare an unresolved review with
`RemoveExistingAlias: true` and the exact current `ExpectedAlias`. Native
`--update-map` checks the physical definition, alias preimage, SDK/contracts and
absence of accepted scoped names before removing that map row. Ordinary unresolved
reviews never remove aliases. Checkpoint with `--remove-reviewed-aliases` after the
native gates; the ledger retains the former decision in `AliasWithdrawals` and
removes the operational marker so later reviews cannot replay the request.

When new behavioral evidence resolves a previously unresolved definition, prepare
`ResolveExistingUnresolved: true` and `PreviousUnresolvedEvidence` containing its
exact earlier `Reason` and `UnresolvedReason`. Checkpoint with
`--resolve-reviewed-unresolved` after native update/check. The guard requires an
unmapped previous definition, exact native addition and final alias, plus checked
scope identities. It preserves annotations and the former rationale in
`UnresolvedResolutions`, rejects duplicate scope positions and removes replay
markers. No earlier scoped alias may be discarded.

`prepare_physical_review.py --spec <spec.json> --output <fresh-review.json>`
normalizes native inventory roots to exact application-relative physical paths
and validates current hashes. Specs support evidence-backed aliases, explicit
preservation and unresolved decisions; unresolved rows cannot carry aliases.
It writes review JSON only. Run `python test_physical_review.py` for its guards.
Native `--update-map` and `--check-map` remain required before checkpointing.

`verify_native_library_lifetime.py` reproduces a prepared physical review plus
its explicit scope annotations and compares the native-checked maps. It verifies
that every prior alias, scope and module binding survives, distinguishes new
aliases from repeated accepted requests, and checks input/report hashes. This
read-only verification writes evidence JSON; it does not modify ETS artifacts.

For explicit CLR async/iterator MethodImpl contracts, use the native
`de4dotEx/tools/FrameworkContractInspection` against the pinned reference manifest.
`framework_contract_preservation.py` prepares review JSON from an exact spec and
hash-bound proof. Checkpoint with `--review-only --preserve-framework-contract-methods
--framework-contract-evidence <proof.json>` after native zero-edit update/check.
The guard rejects aliases, existing map/ledger definitions, stale inputs, incomplete
proofs and unsupported roles. It removes the operational marker from the ledger
while retaining declaration provenance and the unproven source-merging annotation.

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

`inventory_generated_owners.py --scope <physical-scope.json>`
`--cli <GeneratedOwnerInspection.dll> --inventory <whole-inventory-summary.json>`
`--map <checked-map.xml> --ledger <reviewed.json> --output <fresh-directory>`
joins every remaining candidate to native ownership evidence using physical paths,
hashes/MVIDs, tokens and signatures. It verifies inputs before and after inspection,
runs at most two module workers, retains per-module reports and records elapsed
time and optional observed RSS. `candidate-owners.jsonl` preserves overlapping
attribute/container/accessor/delegate/state-machine facts and raw operands.
Distinct owners are counted separately within each evidence kind: an iterator
accessor's property and kickoff are different roles, not competing kickoffs.
Unresolved external bindings remain explicit. These facts never retire candidates,
assign aliases or establish decompiler merging, readability or runtime compatibility.
`--reuse-inventory <earlier-generated-summary.json>` verifies native report hashes,
scope, tool/dependencies and every physical input before reuse. The native reports
do not depend on aliases; the new worklist must still bind the current map, ledger
and candidate inventory. Do not reuse a stale candidate worklist.

For a corrected rationale, `checkpoint_naming_block.py --review-only`
`--refresh-reviewed-evidence` requires `PreviousEvidence` with the exact previous
`Reason` and `UnresolvedReason`. It preserves every naming decision and physical
identity; native update/check must prove a byte-identical map. Arbitrary ledger
overwrites and stale rationale preimages remain rejected.

For a supported historical proposal absent from the current map, use
`ApplyExistingProposal: true`, with `PreviousProposalEvidence` from
`review_ledger.proposal_preimage(previous)`, then checkpoint with
`--apply-reviewed-proposals`. The alias must remain exactly the same; physical
identity, earlier decision/scopes, fresh native addition and final map are checked.
Complete interface/override families and every retained scope alias are required.
The ledger retains `ProposalApplications` history and removes operational markers.

`prepare_application_property_review.py` binds reviewed field/property roles and
coupled accessors to native getter bodies, physical graph references and complete
native families. It checks every graph input hash, the selected first-party scope,
exact SDK whitelist and previous decisions. It writes review/evidence JSON only;
native update/check and the explicit checkpoint guards remain required.

`prepare_constructor_parameter_review.py` prepares constructor scope decisions
from native direct-storage proposals, original bodies and physical graph uses.
It preserves constructor identity and meaningful existing names, binds role
provenance to exact field aliases/metadata, and records unresolved parameter/local
positions with the missing evidence. `--preservations` accepts explicit physical
and parameter/proposal preimages plus behavioral rationale for meaningful names
that should remain unchanged. This workflow writes review JSON only; native map
update/check and an application-wide coverage record remain separate gates.

`prepare_forwarded_parameter_review.py` binds native direct-call parameter
proposals to exact caller/callee bodies and physical graph references. Every
eligible proposal requires an identity-bound accept, preserve or defer decision
with its parameter/proposal preimage and domain rationale. Callee scope aliases
and original metadata names are checked independently; SDK-protected callers and
third-party modules are excluded. Meaningful short names remain intact, generic
`value`/arithmetic labels retain missing evidence, and existing ledger scopes are
merged only after native update/check. Scripts write review/evidence JSON only.

An accepted parameter role does not resolve its opaque method owner. Such rows
carry `UnresolvedDefinitionEvidence`; the whole physical inventory reports
`ScopedOnly` and keeps flagged definitions in the remaining selection. Scoped
readability cannot silently become whole-method preservation or naming coverage.

`prepare_parameter_field_review.py` binds native constructor-storage proposals to
the complete physical graph, exact field references, constructor callers and
native method bodies. Run once without `--bodies`/`--decisions` to collect native
inspection requests, then provide both for an explicit domain review. Every
eligible field requires its physical preimage, ExpectedProposal and a rename,
preserve or unresolved decision with rationale. SDK tokens, mapped fields and
third-party inputs are excluded; historical ledger decisions require a separate
guarded transition. It writes review/evidence JSON only. Preserve useful original
names when a proposal merely removes a suffix or loses domain specificity.
Resolved graph writes must match native constructor tokens and IL offsets in the
same physical module. Foreign/static/unsupported writers and field-address edges
are rejected independently of the native local-body scan.

The v403 constructor-storage checkpoint adds 56 field aliases in eight physical
modules, preserves 10 meaningful existing names and clarifies 24 proposed roles.
Evidence retains 282 native method bodies across nine physical modules and checks
all 111 graph input hashes. SDK/contract checks pass with no collision suffixes,
strict ledger coverage has zero invalid/conflicting rows, and spec/review/evidence
reproduce byte-for-byte. The 109-module inventory has 25,088 remaining native
candidates, including six opaque definitions with scoped aliases only. The map
is staged; the latest consolidated ETS export/build and runtime compatibility
remain pending. See `parameter-field-milestone-v403.json` for checks and limits.

`prepare_forwarded_parameter_review.py --property-parameters` additionally binds
generic setter inputs to the exact property token/signature/name exposed by native
inspection. Every proposal still requires its physical and parameter preimages
and a domain decision. `AcceptedName` can clarify the caller role when the property
is intermediate storage; `ExpectedCallerAlias` guards supporting checked method
aliases. The generic setter role must be original metadata `value` or an exact
checked scope alias. Prefixes and adjacent tokens cannot establish ownership.
Scope merges retain previous uncertainty in history and retire active missing
evidence for accepted positions. Run `test_property_parameter_review.py` and
`test_review_ledger.py` for these guards. See `property-parameter-milestone-v404.json`
for the measured whole-tree proposal scan, review decisions and verification limits.

`checkpoint_naming_block.py --review-only --retire-rejected-sdk-proposals`
records explicit preservation of historical proposals rejected by the SDK
whitelist. `sdk_proposal_retirement.py` requires the exact prior decision/scopes,
physical module identity, token/signature and map-bound whitelist hash. It rejects
any existing map entry, including scoped-only bindings, and preserves the prior
proposal and its evidence in `RejectedSdkProposals`. Native update/check must
produce zero edits and a byte-identical map. This is ledger consistency and SDK
contract preservation; it does not count as new semantic names or reconstructed
source. Run `test_sdk_proposal_retirement.py` for stale identity, scope, history,
whitelist and path guards. The v407 review retires 1,567 rejected proposals and
166 proposed scope aliases; actual checked names and runtime metadata are intact.

Native `SdkContractInspection` also proves inherited protection through complete
physical CLR families. `checkpoint_naming_block.py --review-only` accepts
`--retire-rejected-contract-sdk-proposals` for exact prior unapplied proposals or
`--preserve-sdk-contract-methods` for previously unreviewed methods, together with
`--contract-sdk-evidence`. The review must bind that report's path/SHA256.
`contract_sdk_proposal_retirement.py` checks seed/map/manifest hashes, physical
input hashes, membership hashes and exact SDK symbol identities before recording
preservation. Existing map entries, incomplete families, stale preimages and
scope changes are rejected. Proposal history remains intact; these decisions
add no aliases and make no generated-source reconstruction claim.

Run `test_contract_sdk_proposal_retirement.py <native-fixture-directory>` after
the de4dotEx native fixture. The v411 contract block retires 59 historical
proposals and preserves 280 additional methods in 130 complete protected
families. This reduces whole-tree candidates from 23,211 to 22,874 (337), with
the map byte-identical. See `sdk-contract-verification-v411.json`; consolidated
ETS export/build/runtime and ETS 6.4 verification remain pending.

The v408 Bus/connection checkpoint adds 133 coupled aliases (two types, 12
methods, 34 fields, 38 parameters and 47 locals) and corrects nine earlier names
that described only a guard, logging or a collision suffix. Complete original
send/security/RF, response wait, disposal and shared connection lifetime bodies
support those roles. `GetAsync2` becomes `OpenConnectorAsync`; the shared
connection acquisition overload retains `GetAsync`. All older scopes and physical
bindings remain intact. Native SDK/contract checks accept 142 exact edits with
zero errors, ledger coverage has no invalid rows, and preparation reproduces
byte-for-byte. See `falcon-bus-connection-verification-v408.json`. The map is
staged; consolidated source/build/runtime and unchanged-App verification remain
pending. The 109-module inventory has 23,292 remaining native candidates.

The mapped source checkpoint is `mapped-generated-source-verification.json`.
Native SDK C# inspection of Common applies v412 across all 109 pinned export
inputs, preserving physical compatibility contexts and the SDK whitelist. It
records 228 roots, 116 positive body witnesses and 71 captured-field bindings;
606 definition, 431 parameter and 153 local aliases are explicit. Original
metadata definitions remain byte-for-byte equivalent as report data. The ILSpy
capture fix uses the checked physical field alias for reconstructed locals and
avoids nested lambda parameter shadowing. Two mapped synthetic sources compile
and reproduce 46 additional behavior cases; the 47 native/6 guard/77 baseline
suite also passes. Plugins for net48/net10 build with zero errors.

`df529ce7c` contains the signed-CLR runtime Invoke parameter-only fix in the
attached `delegate-source-scope` worktree. Its 34 native guards and SDK export,
metadata restoration, unchanged caller and stable incremental build pass.
Primary concurrent SourceNameMap/MethodContractFamilies edits are preserved;
include the isolated fix in the next exporter build. The portable exact-context
resolver passes 33 guards and records requested/effective identities with pinned
per-source config provenance. Missing dependencies and one ambiguous request
remain explicit. This checkpoint changes no maps or candidate counts and proves
no application-wide retirement, consolidated ETS build, unchanged ETS Apps or
ETS 6.4 runtime compatibility.
