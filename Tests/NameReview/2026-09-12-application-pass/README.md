# ETS 6.3 / 6.4 naming pass — checkpoint sink

This directory holds the machine-readable records. It is not the state document.

Read first:

- `D:\knx_analysis\STATE.json` — current maps, hashes, coverage, backlog, next items
- `D:\knx_analysis\POLICY.md` — compatibility policy
- `D:\knx_analysis\PLAYBOOK.md` — pipeline, gates, evidence routes, working rules

What lives here:

- `reserved-accessor-verification-v505.json` — fixes the one CS0082 exposed by
  the actual v504 solution build. Falcon's ordinary configuration storage method
  is now `SetInterfaceConfiguration`; its former alias occupied the setter slot
  reserved by a getter-only property. Native de4dotEx and dnSpy preflight reject
  reserved property/event signatures while preserving valid overloads. The full
  native suite, 17 source-consumer cases, nine invalid-alias repairs and tool builds
  pass. Fresh Falcon source builds with zero errors; visible contracts have zero
  differences. Its 3,197 strict metadata differences remain open. Fresh v505 full
  verification covers 109 physical inputs and 1,050 frozen file pins; consult
  STATE.json and the recorded session/result before inferring completion.
- `consolidated-v504-freeze-verification.json` — immutable start observation for
  the earlier 1,046-pin run. Its actual 109-project build failed with one CS0082;
  it is retained as the compiler-defect reproduction, not a successful build.
- `managed-stack-verification-v504.json` — current naming checkpoint: 268 new
  aliases connect lifecycle, REST/configuration/security/update payloads and
  point-API monitor correlation across 35 complete interface families. All prior
  aliases are preserved; the native SDK/contract checks and both cached
  109-module inventories pass. There are 18,623 lexical candidates remaining.
  Firmware-name updates still throw the original `NotImplementedException`;
  46 residual local slots remain unresolved. Next: consolidate the accumulated
  v493–v504 changes into a fresh export/build with HTTP dependency context02.
  The last full-build and partial runtime baseline remains v492.
- `point-discovery-verification-v503.json` — preceding naming checkpoint: 158 new
  aliases and 14 behavior-backed corrections connect mDNS service records,
  serial-number lookup and concurrent CoAP/mDNS endpoint discovery across six
  complete families. Thirty-four captures have exact native producer evidence;
  twelve formerly unresolved fields now have proven source roles. Native
  SDK/contract checks and both cached 109-module inventories pass; 18,641 lexical
  candidates remain. Three closure containers and 62 local slots retain explicit
  uncertainty. v503 is unexported; v492 remains the full-build and partial runtime
  baseline.
- `checkpoint_original_parameters.py` — extends the checkpoint entry point to
  preserve an original parameter name when the map correctly omits a redundant
  rename. Exact physical native reports verify the input hash, assembly identity,
  MVID, method token/signature and parameter sequence/spelling. The actual
  discovery callback retains `sender`; all 79 ledger regressions pass.
- `discovery-group-verification-v502.json` — preceding naming checkpoint: 304 new
  aliases connect multicast discovery, group reception and OSCORE context providers
  across 21 complete contract families. Eight method-name corrections describe
  the actual send/register/receive behavior. Native SDK/contract checks and both
  cached 109-module inventories pass; 18,709 lexical candidates remain. The two
  discovery-loop captures have exact producer evidence. The stop-listening entry
  point remains unresolved because its native body still joins the group. v502
  is unexported; v492 remains the full-build and partial runtime baseline.
- `stack-resources-verification-v501.json` — preceding naming checkpoint: 314 new
  aliases connect endpoint/token stores, REST requests, authentication/resource
  events and response correlation across 19 complete contract families. All prior
  aliases are preserved. Native SDK/contract checks and both cached 109-module
  inventories pass; 18,776 lexical candidates remain. The previously unknown
  stack-resource argument and both response-queue tasks have exact evidence;
  ambiguous local slots remain unresolved. v501 is unexported; v492 remains the
  actual full-build and partial runtime baseline.
- `spake-verification-v500.json` — preceding naming checkpoint: 317 new aliases
  connect the SPAKE prover/verifier flows, password derivation, point arithmetic,
  transcript, key schedule and network callbacks. Exact native producers establish
  twelve more captured-field roles; the authentication password uncertainty is
  resolved. Native SDK/contract checks pass. Remaining closure/local uncertainty
  is recorded explicitly; source/build/runtime verification remains at v492.
- `checkpoint_scope_evidence_completion.py` — ledger checkpoint entry point that
  also retires the last unresolved scope entry when a native-checked alias resolves
  it. It preserves historical evidence and extends the immutable older helpers.
  `scope-evidence-reconciliation-v500.json` records the exact historical replay
  used to repair one existing ledger row. All 71 ledger regressions pass.
- `point-components-verification-v499.json` — preceding naming checkpoint: 348 new
  aliases across group communication, access-token security and software update,
  plus the behavior-backed `ParseOscoreAccessToken` correction. All 29 interface
  families have consistent declaration and implementation scopes. Native SDK
  and contract checks and both cached 109-module inventories pass; 19,012 lexical
  candidates remain. Three captured fields, one SPAKE argument and residual
  locals retain explicit uncertainty. v499 is unexported; v492 remains the last
  actual full build and partial runtime baseline.
- `progress.json` — tool-facing record of the current map paths and checkpoint
- `automatic-field-source-verification-v492.json` — completed 109-module source
  audit and join to the actual compiled files: 3,834 of 3,912 strict metadata
  differences have exact compiled-source owner/binding evidence; 78 lack direct
  evidence in this baseline. All differences remain unresolved runtime contracts.
  Five settings source mismatches contain only the added `partial` modifier.
  The audit retains 5,421 unresolved printed references and retires no candidates.
- `captured-receiver-verification-v492.json` — native observation now records
  fields replaced by `this` separately from captured variables. Four actual ETS
  fields gain exact owner evidence across three roots whose compiled source is
  unchanged. Native, behavioral and malformed-evidence checks pass; this does
  not waive runtime contracts or replace the pending whole-scope source audit.
- `timing-context-verification-v493.json` — naming-only checkpoint: 82 aliases
  connect UTC timing, CoAP settings and OSCORE context factories; the historical
  `GetTickCount642` collision becomes `GetElapsedMilliseconds`. Native SDK and
  contract checks and both 109-module cached joins pass, leaving 19,658 naming
  candidates. Configured-interval semantics and 46 local slots retain explicit
  uncertainty. v493 is unexported; the compiled/runtime baseline remains v492.
- `automatic-field-verification-v492.json` — latest 109-project source build,
  public/SDK audits and 878 restored automatic-property storage contracts.
- `automatic-field-runtime-v492.json` — latest staged Chinese startup, protected
  fixture reopening, SDK history persistence and partial unchanged-App checks.
  All 4,630 protected files were restored; 55 installed App files are unchanged.
  Broader behavior and the recurring MyKNX shutdown error remain unresolved.
  Fresh source inspection is tracked by `STATE.json`; naming coverage is open.
- `reviewed63.json` — cumulative behavioural review ledger (the row-level evidence)
- `checkpoint-waveNNN.json`, `checkpoint64-vN.json` — accepted per-block records
- `map-update63.json`, `devkit*63-review-check.json` — last update/check reports
- `archive/` — the former handoff and README journals (history; do not read to resume)
- `consolidated-v467-verification.json` — frozen 109-project solution compiles with
  zero errors; exact staging and SDK whitelist audits pass. Chinese startup,
  unchanged ETS AI MCP 4.15 SDK reads, history persistence across a fresh process
  and protected fixture reopening are observed. Naming and broader App/6.4
  compatibility remain open. The report explicitly records the unrelated `test`
  project autosave without an exact preimage, the initially ineffective store
  isolation, and an unbacked global App configuration rewrite. Follow its pinned
  evidence and current `STATE.json`; these partial results do not close the goal.
- `consolidate_export.py` — portable immutable-input freeze and native full-scope
  export/build orchestration, with bounded worker counts and sampled process-tree
  memory measurements. It never edits ETS source or binaries. Each run requires
  fresh output paths; use the committed isolated native runtime and exact physical
  contexts recorded in the freeze. Format 2 snapshots mutable control files and
  its own code; run with the retained `Orchestrator` path. `verify <freeze>` checks
  pinned bytes and application/runtime/compile-reference file sets without export.
  `test_consolidate_export.py` passes 28 isolation and drift guards.
- `consolidated-v467-replay-freeze-verification.json` — replay freeze07 retains
  byte-identical v467 map, accepted ledger, physical contexts, SDK contracts,
  exporter runtime and native evidence with 1,066 verified pins. The legacy
  freeze06 pointed to the live ledger and helper; their later edits invalidate
  its current verification. Its build-completion result and 17 pinned historical
  reports remain intact. This repair performs no additional ETS export/build.
- `connectionless-factory-correction-verification-v468.json` — corrects the
  map-only Falcon factory alias to `OpenConnectionlessAsync`. Its exact generated
  owner creates and configures the connection, handles descriptor fallback and
  failure cleanup, then returns it. Every other alias/scope/decision is retained;
  SDK/contract and 109-module cached checks pass. Current v468 has not been
  exported; the 109-project build and partial runtime evidence belong to v467.
- `connection-lifecycle-coverage-v469.json` — adds 223 coupled aliases across
  connection-oriented, connectionless, local transport/application and disposal
  chains: two methods, 85 fields, 49 parameters and 87 used locals. All 31 kickoff
  captures match their parameters; 14 fresh physical method scopes bind. Five
  generated machines retain their metadata and reconstructed v467 owners; five
  earlier storage uncertainties remain unchanged. SDK public definitions and
  parameters, CLR disposal contracts and every prior alias/scope are preserved.
  Native checks and both cached 109-module joins pass; candidates fall from
  20,152 to 20,092. Local slot 3 in `0x06000174` holds both a descriptor and a
  connector APDU length and remains unaliased pending role-specific splitting.
  Current v469 has not been exported or runtime-tested. Next: APDU/path
  negotiation, authorization state and memory transfer bounds through callers.
- `firmware-control-coverage-v471.json` — adds 345 coupled file-control aliases:
  21 message/extension types, seven methods, 138 fields, 23 parameters and 156
  used locals. All 24 fresh method scopes bind; 22 private/internal captures
  match their parameters and 20 public SDK captures remain unchanged. Fourteen
  generated machines retain exact owners and original metadata; fourteen earlier
  storage uncertainties remain unchanged. The disconnect reset's historical
  uncertainty is resolved through the authorization-level producer, getter and
  reset. Subservice 255 remains unnamed with missing domain evidence; retry
  local slot 4 in `0x060001A4` holds both exception dispatch and a prior counter
  and needs native role-specific splitting. Native checks and both cached
  109-module joins pass; candidates fall from 20,033 to 19,907.
  `firmware-helper-correction-verification-v472.json` records two complete-body
  corrections: `SendEndOfFileAsync` and `SendFileControlWithRetryAsync`. All other
  aliases, scopes and earlier decisions remain intact; its 25 evidence pins pass.
  Current v472 has not undergone consolidated export or runtime verification.
  Next: finish the streaming helper's parameters, used locals and capture roles.
  `apdu-security-coverage-v470.json` retains the preceding 171 checked APDU/security
  aliases and memory-ceiling evidence. `prepare_physical_review.py` validates
  position-bound uncertainty with exact parameter/type preimages; its 24 tests
  and the 31 ledger tests passed at v470. Unused kickoff slot 1 in `0x06000106`
  remains explicitly unresolved.
- `direct-call-closure-verification.json` — ILSpy `4fc8b3970` reconstructs a
  directly called, nonescaping generated helper as one named callable in its
  lexical owner. The actual Falcon streaming owner now contains `WriteChunkAsync`
  and no standalone `Type_30`. The targeted v472 Falcon source compiles with zero
  errors/2,113 warnings; its SDK audit checks 107 types, 1,082 methods and 354
  fields with zero issues. Export takes 18.7 seconds and an observed process-tree
  peak of 630,472,704 bytes (250 ms samples, a lower bound). Native net48/net10
  builds, 27 synthetic export/unchanged-client checks, 51 fail-closed guards,
  81,962 concurrent/collectible-cache checks and the prior closure-owner regression
  pass. Forty-one evidence pins retain these results, including immutable tool
  and test snapshots. The AST emits a
  `Func`/`Action` lambda; unsupported generic, recursive, escaping and
  identity-sensitive cases remain intact. No naming retirement or complete
  ETS/App runtime compatibility is claimed.
- `streaming-scope-coverage-v473.json` — adds 69 aliases across the complete
  block/chunk streaming chain: 33 fields, four private parameters and 32 used
  locals. Four captures match the original argument stores; twelve public SDK
  captures retain their names. Three generated types retain implementation
  metadata and the proven native reconstruction owns their emitted source.
  Five unused slots have no inferred names; `0x060001B4` slot 5 holds an awaited
  offset and three counter roles and remains unresolved pending native splitting.
  Every prior alias, scope and storage uncertainty is retained. Native map/SDK
  checks and both cached 109-module joins pass; candidates fall to 19,863.
  `streaming-helper-correction-verification-v474.json` corrects the helper to
  `WriteChunksAsync`: the complete loop processes all requested chunks and
  returns the final offset. Its 26 evidence pins retain every other alias,
  scope and annotation, including the new streaming scopes. Native SDK/contract
  checks and both cached joins pass. Current v474 has no consolidated export or
  runtime claim. Next: firmware message/accessor scopes and caller chains.
- `streaming-message-coverage-v475.json` — adds 127 aliases: the paired
  `CheckChunkBlockResponseMessage` type, four buffer/block accessors, 103
  parameters and 19 used locals. Eighty-two scopes bind against 105 original
  message bodies and two inlined predicate targets. Constructor/setter names
  follow serialized buffers, block/chunk/status fields and response processing;
  no unused local receives an invented role. The stream byte at data offset +2
  remains explicitly unresolved. All prior aliases/scopes are retained; native
  checks and both cached 109-module joins pass with 19,846 candidates remaining.
  `response-helper-correction-verification-v476.json` corrects four partial
  aliases to `ProcessFileControlResponse`, `ProcessFileStreamResponse`,
  `VerifyBusyReplyLength` and `VerifyBusyTimeoutReplyLength`. The normal reply,
  polling and four/six-byte checks follow complete original IL and callers;
  thirty evidence pins retain every other alias, scope and annotation. Native
  SDK/contract checks and cached joins pass. The v473/v475 specs contained 91
  uncertainty annotations under an unsupported key; the original ledger omitted
  them. `scope-evidence-repair-verification01.json` verifies their restoration
  across 65 methods with byte-identical map and unchanged aliases. It binds all
  111 historical v473-v476 evidence pins, using exact retained helper versions
  where current tooling has changed. Unknown decision keys now fail preparation.
- `chunk-status-family-verification-v477.json` — corrects both members of the
  synchronous virtual family to `VerifyChunkStatusBytes`. Complete native family
  checks, exact historical preimages and final map identities guard the atomic
  correction; existing scope names and uncertainty survive. The 69 focused
  guards pass; both cached 109-module joins retain 19,846 candidates. Continue
  substantial whole-application caller chains. Current v477 has no consolidated
  export or runtime claim; the last full solution build remains v467.
- `objectmodel-core-coverage-v478.json` — 96 coupled aliases across blob storage,
  object/reference collections, progress reporting and ID generation: 46 fields,
  16 parameters and 34 locals. Full original IL, physical inventories and 16
  existing exported types support the roles; public names and overloads survive.
  Forty unused slots, one reused Boolean and one write-only slot retain typed
  uncertainty. Both cached 109-module joins leave 19,800 naming candidates.
  `objectmodel-id-selector-verification-v479.json` corrects `CreateUniqueIds` to
  `GetExistingObjectsForIdType`: the helper selects existing collections used to
  seed the maximum ID number, while the creator constructs IDs. Every other alias and
  scope is retained. Native SDK/contract checks pass; no new export/build or
  runtime result is claimed. Continue transaction, persistence and caller chains.
- `persistence-coverage-v480.json` — 131 aliases connect transaction creation,
  queued actions/enlistments, write suppression, dirty roots and file journals:
  21 fields, 17 parameters and 93 locals. Original IL for 89 methods supports the
  roles; 89 unused/write-only slots retain explicit typed uncertainty.
  `persistence-role-corrections-verification-v481.json` removes two historical
  numeric suffixes with `EnsureFileTransaction`/`BeginFileTransaction`, and names
  three persistence predicates from their full conditions and caller branches.
  Prior aliases, scopes and uncertainty survive. Native SDK/contract checks and
  cached 109-module joins pass with 19,782 candidates remaining. Current v481 is
  not exported; full build, broader App/runtime and ETS 6.4 closure remain open.
- `physical-source-context-verification.json` — pinned preparation, source-context
  guards, mapped SDK AST observations and explicit missing dependency identities
- `generated-source-scope-verification.json` — native whole-scope observation audit
  and read-only structural candidate joins, with no naming retirement verdict
- `printed-reference-verification.json` — token-writer bindings and targeted mapped-source verification
- `iterator-region-order-verification.json` — 39 exact iterator-owner witnesses,
  synthetic cleanup traces, actual CvNext source compilation and unchanged-caller probes
- `restart-network-coverage-v467.json` — 115 aliases (six methods,
  42 fields, 20 parameters and 47 used locals) across five async restart,
  network-parameter and retry chains, forwarding, request preparation and codecs.
  Retry retains cloned attempts, temporary-error/timeout delays and the final
  original request. Restart retains suppression and finally restoration of both
  retry settings; confirmed restart returns process time without waiting for it.
  Existing codec/event aliases, SDK names/parameters and F7/F8 uncertainties stay
  intact. Five generated types and one private cache-reset method remain explicitly
  unresolved. All 47 used slots in 20 selected methods are mapped; 45 fresh method
  signatures/scopes and 42 fields match their physical inventories. SDK/contract
  checks and both 109-module cached joins pass. Lexical candidates fall from 20,195
  to 20,152: 37 named definitions and six explicit uncertainties. Next: freeze the
  accumulated v467 mappings for consolidated physical source and build verification,
  repair concrete compiler gaps in the tools, then resume whole-application naming.
  `property-discovery-coverage-v466.json`, `property-transfer-coverage-v465.json`
  and `property-descriptions-coverage-v464.json` retain preceding proof links.
  Printed merging, consolidated ETS/unchanged-App checks and ETS 6.4 remain pending.
- `discovery-information-codecs-coverage-v438.json` — connected DIB/SRP
  decoder/constructor/formatter naming; 51 exact aliases preserve prior names
  and original offset/code behavior. SDK/contract checks and 109 cached joins
  pass; printed lambda ownership and consolidated ETS checks remain pending.
- `discovery-frames-multicast-coverage-v437.json` — description-frame layouts,
  multicast lifecycle and independently proven captures/scopes; 91 exact aliases
  retain every prior name. Twelve definitions record missing evidence. SDK/contract
  checks and 109 cached joins pass; consolidated ETS build/runtime remains pending.
- `cloud-connector-getter-correction-verification-v436.json` — corrects the
  map-only connector-ID getter while checking absence of a prior ledger row.
  The target-serial getter and every other alias/scope/decision are retained;
  SDK/contract checks, 175 portable checks and 109 cached joins pass.
- `record_definition_alias_corrections.py` — reusable correction verifier for
  both reviewed aliases and historical map aliases with no prior ledger row.
- `session-frames-cloud-websocket-coverage-v435.json` — session-frame layouts,
  immutable cloud configuration and WebSocket connect/send/receive/disposal
  scopes; 94 exact additions retain every prior name. SDK/contract checks and
  109 cached joins pass; 20,807 candidates remain. Full ETS checks are pending.
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
  Complete virtual-family corrections require matching native changes and final
  map membership. New proofs snapshot mutable Python controls with exact hashes.
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
Unknown decision keys are rejected. Review-only scope evidence repair requires
exact previous evidence, typed positions, unchanged map bytes and checked aliases.
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
