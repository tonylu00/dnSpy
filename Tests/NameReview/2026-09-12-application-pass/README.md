# Application-wide naming pass — in progress

The objective is readable call chains throughout ETS and its coupled components.
The source trees have **not** been renamed or rebuilt by this pass. Decisions are
being accumulated before one consolidated application/verification phase. The
prior `CheckProjectData` fix is already in the 6.3 baseline.

The graph covers 111 managed source projects plus four retained binary dependencies
in 6.3, and 178 plus four in 6.4. Those are physical coverage counts, not readable
methods or completed work. Graphs and query databases live in
`D:/knx_analysis/application-name-pass01` (`graph63-v3`, `graph64-v3`,
`graph63-v3.sqlite`, `graph64-v3.sqlite`). Graph-local IDs always resolve through their
own manifest; same-name compatibility assemblies stay distinct.

Current reviewed chains include:

- ETS product/template checks → manufacturer cache language/version checks →
  cache rebuild creation, live reference selection and weak/strong retention.
- Template classification → CvNext namespace helpers and XML attribute names →
  reading the extracted project's `Name` attribute.
- Parent-process performance counters and the internet availability sampling
  loop, with the shared terminology carried into the inspected 6.4 main executable.
- The ETS 6.3 bootstrapper's environment setup, splash screen, command-line
  parsing, container/telemetry initialization, startup store checks, exception
  handling, pre-notification coordination and resource disposal. `bootstrapper.py`
  records the reviewed helpers, callers, captured context types, fields, parameters
  and local binding proposals together.
- Common's conversion-schema getter and CvNext's latest supported target version
  and namespace, following their exact references from template checks, conversion,
  import validation and the conversion command-line tool.
- The command handler's clipboard, panel navigation, project, device and window
  command/availability paths, including captured query state (`commands.py`).
- ProjectService's project authentication/opening, progress and integrity-check
  callbacks, store updates, project creation/password callbacks, DCA export
  selectors and project-schema metrics (`project_service.py`). Useful public
  method names remain unchanged; visible compiler placeholders are reviewed too.
- Startup registration, script-engine preference and input/output/source storage,
  single-instance mutex/pipe transport and its argument-line iterator, plugin
  registration and identity-check state (`startup.py`).
- App language/logging/startup/disposal, tab-window title/event forwarding and
  pre-notification window helpers (`application_ui.py`).
- Executable service fields, CLI warning/help paths, add-in signature completion,
  licensing configuration and shared LicenseManager state (`services.py`).
- CalculatedParameters' ActiveScript, NiL.JS and interpreted VBScript execution,
  validation and value-conversion contracts, plus reflective argument storage
  (`scripting.py`). Each accepted contract includes every physical family member;
  engine limitations are recorded in the individual behavioral reasons.
- Module argument lookup and template expansion, left/right parameter binding,
  dictionary execution, script callback adapters and device event dispatch
  (`script_bindings.py`). The SDK Device.ExecuteEventHandler caller establishes
  the roles of the device, management and progress arguments.
- Parameter dependency graph construction and ordering, cached calculation
  chains, inline/static execution and proposed-value validation
  (`calculation_chains.py`). Captured predicates, node types, fields, parameters
  and locals use the same terms as their callers. A detected cycle still logs
  and returns the ordered portion; no runtime repair is claimed.
- Project-store stream opening, consistency hashes, clone ID/mask handling,
  installer GUID/HMAC persistence, startup cleanup and restore-point rollback
  (`project_storage.py`). Leaf helpers are reviewed before their file/project
  callers, with fields and locals following the same terminology. Existing
  archive certificate/password helpers retain their useful names and gain
  reviewed field/local roles.
- Transactional directory creation, stream enlistment, commit journals, queued
  copies/deletions and interrupted-commit recovery (`file_transactions.py`).
- Product-store directory callbacks, weak cache tracking, cache file codes,
  manufacturer master hashes/HMACs and version information (`product_storage.py`).
  The master hash remains the existing sum of UTF-8 hash-text bytes; naming
  does not replace its algorithm.
- Conversion errors/notices and result combination, logger/resource wrappers,
  input-directory signatures, supported XML namespace reading and extraction
  (`conversion_results.py`). The schema reader returns the first version it
  finds; it does not prove that every input document uses the same version.
  Resource base names, keys, culture fallback and log severities stay intact.
- XML reader/writer interfaces and implementations, typed attribute readers,
  mutable XML node names, recursive element materialization and schema validation
  (`conversion_xml.py`). Required byte arrays use Base64; optional arrays use
  hexadecimal pairs. The `Enabled` comparison and XML Boolean parser remain
  distinct. Writer state means a write request was received, even for an ignored
  node kind; its alias does not promise bytes were written.
- Materialized XML attributes/elements, captured name predicates, ordered child
  insertion, subtree pruning, attribute lookup and ID parsing
  (`conversion_nodes.py`). `InsertChildAfterNamedSiblings` prepends by default;
  an ordering list selects the last permitted predecessor. `RemoveChildIfLeaf`
  preserves its existing true result for null/non-leaf inputs without removal.
- Conversion data collection and its complete shared contracts
  (`conversion_collectors.py`): baggage path/ID indexing, legacy help references,
  application-program ETS styles, project AddInData/UserFiles, and installation
  Puid allocation. `CollectCurrentNodeAndContinue` means continue scanning; false
  removes the collector from the active list. `ApplicationProgramEtsStyle` has
  `PreEts4`, `Ets4` and `Ets5` values, with `Ets4` preserving the lookup fallback.
  The collector state, query interfaces, private predicates and source-local
  proposals use the same terms. The Puid allocator remains an incremented integer.

For example, `RequiresCacheRebuild` describes both language-pair and cache-format
checks, including the distinction between optional and required missing caches.
Three otherwise identical predicates receive separate names from their actual
callers: communication-object, parameter and calculated-parameter cache checks.
The ledger records methods, types, fields, formal parameters and proposed local
bindings together. Existing meaningful method names are retained.

`decisions63.json` and `decisions64.json` are behavioral reviews, not proof that
the application is readable. Physical copies are listed within a shared decision
only after matching the reviewed source/signature. `stage.py` and `stage64.py`
are exact-snapshot recipes with input hash and source checks; they fail on other
versions rather than guessing by token. They only write a new review ledger.

`to_review.py` turns accepted methods/types/fields into the portable .NET
NameCandidates review format using fresh metadata inventories. It writes an
explicit pending list for locals and unsupported contracts. These cannot
silently disappear from completion accounting. Local occurrences need semantic
reference binding before edits. The converter binds graph-local contract-family
IDs to fresh map-root inventories only when the complete physical member set
has a consistent behavioral review. It verifies the inventory family digest,
rejects trimmed sets and retains conflicting or blocked families as pending.
Fresh type inventories also expose unsupported generic aliases before an update
is attempted. Constructor parameter proposals survive in pending work even when
the constructor name is retained. The .NET updater independently validates the
exact input identities and complete contracts, and reports requested/applied
names and collisions.

Field aliases now use declaring/inherited scopes in both updater and exporter,
so ordinary names such as `logger` can be reused in unrelated classes. The same
map includes the CheckProjectData fields already corrected in the source baseline.
The current staged maps are `names63-staged-v17.xml` and `names64-staged-v6.xml`
under the application pass directory; `progress.json` records their hashes.

The 6.3 map now includes XML contracts whose inherited `IDisposable` interface
needs reference metadata during map preflight. Use de4dotEx's
`--contract-references D:/knx_analysis/application-name-pass01/contract-references63.json`
before `--update-map` or `--check-map`. `contract-references63.json` records the
exact local reference assembly identity, MVID and SHA; reference dependencies
never become editable input assemblies. The resolver uses exact identities and
has no GAC/framework substitution. The tool accepts paths relative to the
manifest for portable reference bundles. `to_review.py` preserves the reference
manifest hash and rejects conflicting family-inventory manifests.

The supplemental `property-fields63.json` / `property-fields64.json` reviews
carry direct getter evidence and source locations for field roles across the
physical application tree. They supplement the manual decision ledgers rather
than pretending each deterministic property projection was a manual method
review. de4dotEx's `--suggest-property-fields` reads metadata without executing
it; `stage_property_fields.py` restricts its proposals to visible unreadable
fields in the exact graph/source snapshot. Normal compiler backing fields,
already readable source names, retained binary-only components, and existing
manual decisions are preserved. The source candidate rules are shared with
the graph's `worklist` command.

Examples include project-store `projectGuid`, project `pluginDeviceCount`,
archive `projectFilePath`, SDK argument/property state and XML schema values.
Compatibility paths and the 6.4 XML ObjectModel `_orig` copy have separate
identities and evidence. They are never collapsed into one assembly name.
`refine_property_fields64.py` records additional source review for
`currentAccessKey`, `operationProjectName`, and `updateOnlineCatalogCommand`,
including its task, running predicate, execution and progress callbacks.
The predicate's existing condition remains unchanged.

Reproduce source selection with the graph database and fresh .NET proposal file:

```text
python stage_property_fields.py GRAPH_DB PROPOSALS NEW_REVIEW MANUAL_LEDGER
```

Use the full `PropertyEvidence`, `SourceEvidence`, `SourceExclusions` and manual
`BehaviorRefinements` when resuming naming. These supplemental reviews are
already included in the current staged maps. The latest property map reports
are separate from the preceding manual-review reports, preserving both stages
of evidence. Neither review size nor absence from a proposal list proves that
the remaining application is readable.

The supplemental `field-accessors63.json` review records exact pure-field-write
evidence for two additional DynamicData methods. The portable .NET
`--suggest-field-accessors` command derives proposals from existing physical
field aliases; `stage_property_fields.py` now applies source/identity guards to
these method proposals too. Actual properties, contract methods, computed
bodies, existing method aliases and field aliases without lexical role evidence
are preserved or explicitly skipped. Its 6.4 scan found no additional eligible
methods, which says nothing about completion of that application.

`map-update63.json` is the latest manual update report (prior accessor aliases
remain in its base map);
`reviewed63.json` and `field-accessors63.json` retain the two reviews separately.
`reviewed63-combined.json` retains the preceding storage/accessor combined input
for provenance; the current manual report uses `reviewed63.json`.
The source worklist also includes compact lowercase/digit type names such as
`arx` and `b8j`, which escaped its earlier one/two-letter rule. Inclusion requests
behavioral review; it never authorizes a replacement name.

Storage evidence preserves distinctions that matter for readable behavior:
FileStreamStore's MaxValue mask setter activates `CopyActive`, so the project
clone flag is `isProjectCopy`; the real mask assignment still follows it.
`ComputeMaskedConsistencyHashBase64` records that its first Seek returns zero,
so the later Seek is not described as restoring the original position.
The deferred restore-point error expression uses a literal original field name;
the field alias retains owner-qualified runtime restoration instructions. Its
consolidated export/build validation remains pending with the rest of the tree.

`cross-version64.json` stages additional 6.4 method/parameter names from the
unique-body/call matches in `cross-version64-from63-v12.json` under the application
pass directory. `stage_correspondence.py` binds both physical input identities,
signatures, source hashes and the reference map; it preserves readable target
source and previously staged aliases. Parameter names transfer only with exact
sequence/type/metadata matches. `CorrespondenceEvidence` and `SourceEvidence`
record the actual pairs, including independent ETS6C/ETS6N paths. The known 6.4
counter-string discrepancy remains unresolved and is not hidden by other matches.

```text
python stage_correspondence.py REF_DB TARGET_DB CANDIDATES BASE_MAP NEW_REVIEW
```

`binding_reviews.py` also supports a precise declaration selector for shadowed
names: `{'NewName': 'transactionRootPath', 'Kind': 'Parameter', 'Start': 8965}`.
The selector must match exactly one declaration in an unchanged source file;
ambiguous/stale selectors fail. These are still declaration proposals awaiting
semantic reference application, not text replacements.

One real case is TransactionalFileStreamManager's transaction scope predicate:
the current source prints `string_0.StartsWith(string_0, ...)`, shadowing the
outer argument. The original lambda instructions load captured `fullName` then
the lambda argument before `String.StartsWith(InvariantCultureIgnoreCase)`.
The staged roles are outer `filePath` and inner `transactionRootPath`.
`transaction-scope63-il.json` preserves that evidence; consolidated export must
prove the correct captured-versus-lambda binding. No source fix is claimed yet.

de4dotEx's parameter updater now treats a requested original metadata name as
preservation/restoration and removes any old source override. It no longer
produces `title2` when `title` was already correct. The two 6.4 window-title
parameters keep their original `title` names; all current manual/correspondence
map reports have zero requested-versus-applied name adjustments. Genuine
collisions with other bindings still receive explicit allocation diagnostics.

Graph v3 fixes field MemberRef classification: dnlib MemberRef implements both
method and field interfaces, so the signature must decide the edge kind. Earlier
v2 graphs incorrectly labeled these uses as unresolved method calls. The exact
resolver now reports 13/87 unresolved uses in 6.3/6.4; these are graph diagnostics,
not readability completion. **Use v3 graphs and databases for future review.**
The CvNext field `any.a` resolves correctly; no scope-insensitive binding change
was needed. A wrong-vendor field fixture still fails reference preflight.

## Current limitations and next work

- This is still a partial review of the full indexed application. Deeper project
  loading/conversion internals, scripting facades and diagnostics, compatibility callback
  roles and many other components remain. Do not use the ledger count as an
  application readability metric. The portable source `worklist` query also finds
  emitted helpers that the metadata-only method review list missed.
- Field maps pass metadata/exporter allocation checks; consolidated source export,
  compilation and runtime restoration validation remain. Source-local application
  needs a semantic reference pass; syntax locations alone cannot authorize edits.
- Generic type aliases and constructor parameter-only mapping remain unsupported.
  Reviewed names are retained explicitly in pending work. Dynamic reflective
  field creation/removal contracts also remain pending while the fresh family
  inventory cannot resolve their external IReflect contract.
- Uncertain short string fields with special storage metadata and a compatibility
  callback with an unestablished consumer role are explicitly unresolved. Both
  the ledger and converted pending list retain these, even without a proposed
  name. Their absence from the accepted map is not completion.
- Common's unreferenced `f` getter and XML document/signing getter `e` still need
  their roles reviewed. Getter `d` has a reviewed conversion-specific name.
- **ETS 6.4's ETS6C input is not interchangeable with ETS6N.** Its process counter
  methods contain empty string literals where ETS6N has `Process`, `ID Process`,
  `Creating Process ID` and `#`. Names also differ despite equal MVID/token layout.
  `ets64-counter-string-discrepancy.json` records evidence from the input metadata.
  This discrepancy is unresolved; no string restoration or behavior equivalence
  is claimed. The process-counter review applies only to the main ETS6N input;
  other method correspondences are checked independently at each physical path.
- No ETS exports, builds, full audits or live launches were performed for this
  pass. Only portable tool regressions and identity/mapping/reference checks ran.

Continue the complete naming pass before exports/builds. Keep unclear roles as
explicit work items. Completion requires applied readable source, consistent
references/contracts and consolidated verification over the whole intended tree.

## ETS 6.4 vendor-name correspondence (DevKit, waves 78-79)

`D:\knx_analysis\ETS6.4_api_preserved5` is **not** obfuscated at the public API
level: `Knx.DevKit.dll` (graph `m0099`) keeps readable type names, event
accessors (`add_DongleAdded`), raisers (`OnDongleAdded`) and property accessors,
while only private members carry random names. That makes 6.4 a naming source for
6.3 rather than only a transfer target.

- Wave 78 recovered the whole `akj` (= `Knx.DevKit.SecureDongle.DongleManager`)
  event surface: `akh` (14 Dongle events), `alk` (18 manager events), `aku`
  (license added/removed) and the five `System.EventHandler` events. Field
  declaration order is stable across the two builds, counts match per field type,
  and the mapping is cross-checked by subscriber symmetry:
  `arx::a()` (6.3) and `Knx.Ets.Common.Licensing.DongleManager::InitializeAsync`
  (6.4) both subscribe to DongleAdded/Removed/Locked/Unlocked/InvalidSignature.
  Raisers are named `On<Event>`; 25 virtual raisers go through the
  `--review-families` contract path.
- Wave 79 transfers 24 type names (`akg`=`Dongle`, `akj`=`DongleManager`,
  `al2`=`TimeManager`, `al6`=`Bootloader`, `amh`=`UpdateManager`, the event
  handler/args pairs, ...). Correspondence evidence is member-shape overlap plus
  near-equal member counts (e.g. `amh` 249 vs `UpdateManager` 246). `aly` is named
  `TimeLicense` because the module already reserves `Time`
  (`SignatureType::Time`).

Working helpers: `scratch-align-events.py` (field-order alignment),
`scratch-match-types63to64.py` (member-shape type correspondence),
`scratch-fieldraisers.py` (event field -> add/remove/raiser), and
`devkit-event-align.json` / `devkit-event-split.json`. The next DevKit steps are
enum-member alignment by declaration order, property accessor transfer for the
matched types, and the remaining `akg`/`amh`/`al6`/`Class23` members.

## Mapping-only policy and tool support (2026-09-19)

Standing rules for this pass:

- **No script rewrites ETS source text.** Scripts may only produce mapping and
  review artifacts (JSON ledgers, `names63-staged-vNN.xml`). All renames are
  applied by *tools*. The legacy `2026-09-12-project-check/apply.py` does textual
  source replacement and must not be used again.
- **Evidence comes from dnSpy/ILSpy, not ad-hoc dumpers.** dnSpy.Console can dump
  any member (`--lang IL --md 0xTOKEN file.dll`) and now dumps a whole assembly:

  ```text
  dnSpy.Console.exe --lang IL --il-dump out.txt <assembly>
  ```

  The IL text includes enum literals with their constant values, event/field
  definitions and full method bodies, which is what the earlier native-records and
  DevKit passes needed.
- **Batch rename from the map (de4dotEx).** `NameCandidates --apply-map
  <map.xml> <output-tree> <report.json> [--preserve-public]` renames the mapped
  definitions and then rewrites every `TypeRef`/`MemberRef` in the whole tree that
  resolves to them, including cross-assembly calls. A map author therefore records
  the *implementation* only; reference tokens are never needed. Rows may carry a
  token or, for hand-written maps, just `ExpectedName`/`Signature`. Regression:
  `tests/ApplyMapRegression`.
- **ETS SDK public API is frozen.** Third-party ETS apps ship as compiled binaries
  and cannot be rebuilt against our modified SDK, so public/protected members of
  SDK assemblies must keep their names. Use `--apply-map ... --preserve-public`
  (reported in `SkippedPublicApi`) and dnSpy's `--public-sign`/`--source-name-map`
  export path, which keeps runtime identities.
- **SDK compatibility gate (63).** The shipped SDK package
  (`sdk_extract/Knx.Ets.Sdk.nuspec`) contains `Knx.Ets.Sdk.dll`,
  `Knx.Ets.Sdk.AddIns.AddInViews.dll`, `Knx.Ets.Common.Types.dll` and
  `Knx.Ets.Common.Resources.dll`. The gate is:

  ```text
  NameCandidates --public-api-audit names63-staged-vNN.xml audit.json \
      --sdk-module Knx.Ets.Sdk.dll --sdk-module Knx.Ets.Sdk.AddIns.AddInViews.dll \
      --sdk-module Knx.Ets.Common.Types.dll --sdk-module Knx.Ets.Common.Resources.dll
  NameCandidates --filter-map names63-staged-vNN.xml audit.json names63-sdkfrozen-vNN.xml
  ```

  `--public-api-audit` reports SDK-visible renames *and* types used by SDK public
  signatures that are renamed in another module, and emits a machine-readable
  `Freeze` list. `--filter-map` writes the export map with those rows left at their
  original names; `--apply-map` accepts the same list via `--freeze` for binaries.
  The current state (`public-api-audit63.json`, map `names63-staged-v85-sdkfrozen.xml`)
  froze `Knx.Ets.CalculatedParameters.z`, which `Knx.Ets.Sdk.ScriptFacades.DeviceFacade`
  and `DeviceManagementFacade` expose in public signatures; the filtered map passes
  with `sdk-visible=0` and `sdk-referenced-types=0`.
- **dnSpy source maps accept name-only rows.** `SourceNameMap` rows without a
  `Token` attribute are resolved by `ExpectedName` + `Signature` inside the module;
  ambiguous or missing matches fail the export instead of guessing.
- **Inner-reference evidence (`scratch-innerfp2.py`).** When a method has no name
  in the 6.4 counterpart, the matcher scores 6.3/6.4 pairs by what the body
  references: `System.*`/framework call signatures, string literals, mapped field
  and local types. Score with a clear winner (`>=0.6`, gap `>=0.2`) transfers the
  6.4 name; anything ambiguous is listed for manual review instead of guessed.
  For DevKit the 6.4 transfer is now largely exhausted for the remaining event
  accessors (many 6.4 accessors are themselves obfuscated), so the remaining
  `akj`/`akg`/`al6`/`Class23` members need behavioural naming from callers,
  strings and native-callback wiring, using `dnSpy.Console --lang IL`.
- **Verified reference propagation.** `Tests/SourceNameOnlyMapRegression` exports
  two projects from a map whose rows carry only `ExpectedName` + `Signature`: the
  renamed definition and the call site in the other project both change, and a row
  whose signature matches nothing fails the export. Together with the de4dotEx
  `--apply-map` regression this covers both the source-export and binary paths, so
  renamers only ever record the implementation.
- **Readable reference builds for the pending modules.** The ETS 6.4 tree carries
  newer builds of the same libraries next to the identical shared copies:
  `Knx.Ets.ObjectModel.2` (m0120, 22,503 readable methods), `Knx.Ets.HawkNET.2`
  (m0113, 5,546) and `Knx.Falcon.2` (m0153, 11,712). `Knx.Ets.ObjectModel.dll`,
  `Knx.Ets.HawkNET.dll` and `Knx.Falcon.dll` are byte-identical between the 6.3 and
  6.4 trees, so those `.2` copies are the naming source, not the identical ones.
  `scratch-crossmodule.py` pairs types by exact name first (3,360 pairs for
  ObjectModel) then matches members by signature shape plus inner-reference score,
  with readability decided by `NameCandidates --name-analysis` (the same lexical
  analysis the review pipeline uses) and a recurring-token check to reject
  obfuscated names.
- **Declaration-scoped name allocation (done).** The map updater, the map writer
  and dnSpy's `SourceNameMap.Apply` now reserve aliases through the shared
  `MemberNameScope`/`MemberNameClaims` pair: a member is reserved against its own
  and inherited declarations only, so unrelated types may both use `Create` while
  a same-type or inherited collision, an unmodified declaration, a generic
  parameter or a namespace component still receives a deterministic suffix. Wave
  87's 24 name-reservation losses are unblocked; the existing staged map still
  passes `--check-map` because it satisfied the stricter module-wide rule.
- **Structural 6.4 transfer (`scratch-transfer.py`, wave 88).** Type names are the
  weaker half of the evidence: only 46 of 962 HawkNET and 362 of 2087 Falcon 6.3
  types are readable, so names transfer through structure. Types pair by exact
  readable name first and then by a mutual-best containment match (`Shapes` 0.42,
  framework `Calls` 0.24, `Strings` 0.20, `Fields` 0.08, threshold 0.85, margin
  0.10); tuning on ObjectModel's 3331 known pairs measured 0.97 precision. Members
  then match by signature shape in which every non-framework type name collapses
  to one placeholder, so an obfuscated reference compares equal to the readable
  one, with the C# member class (ordinary/get/set/ctor/operator/explicit) part of
  the key so accessors and constructors cannot masquerade as ordinary methods. A
  shape with a single occupant transfers directly; several occupants require body
  evidence (framework calls, strings, locals, already-paired internal references)
  with `>=0.6` and a `>=0.2` margin. An audit using the 6.3 build's own readable
  names as anchors measured 2915/2917 ObjectModel, 319/319 Falcon and 43/43
  HawkNET agreements, so the pairs and the shape rule are sound.
- **Wave 88 (checkpointed).** 298 rows: 193 Falcon, 74 HawkNET, 31 ObjectModel,
  including the 24 ObjectModel rows wave 87 skipped for name reservation. The
  updater reported 6535 reviewed edits, 0 errors and published
  `names63-staged-v88.xml` (SHA256 972BFCD3...); `--check-map` passes, the SDK
  audit again freezes only `Knx.Ets.CalculatedParameters.z`, and the filtered
  export map reports `Success=True, sdk-visible=0, sdk-referenced-types=0`. 74
  proposals inside one type keep a deterministic suffix (`Create2`...`Create7`,
  `UpdateRootPathsOfCurrentTransaction2`): those are genuine same-scope collisions
  because the rebuild instruction is keyed by declaring type and alias.
- **Transfer ceiling (measured).** For ObjectModel, 224 candidates have no 6.4
  counterpart shape, 2200 have only placeholder counterparts and 555 have a
  readable one (312 unique). The 6.4 builds are therefore close to exhausted for
  this class of work: the remaining ~15,000 candidates across the graph need
  behavioural naming from the 6.3 binaries themselves (strings, call sites,
  property/event/native wiring, delegate targets) rather than another build.
- **Waves 89-90: member-vote seeds and state-machine evidence.** The type-level
  score alone missed pairs such as HawkNET `eo` -> `Knx.Ets.Hawk.DeviceManagement`
  or `lp` -> `DataProvider.ApplicationProgramOptions`; the member-vote matcher
  (`scratch-membervote.py`, majority of mutually matched members) now seeds the
  type map first, which raised Falcon 219 -> 626 and HawkNET 129 -> 469 proposals
  while the anchor audit improved to 444/444 and 92/92. Async and iterator
  wrappers only call `AsyncTaskMethodBuilder::Start`, so their state machine's
  body (calls, strings, locals) is now folded into the wrapper; that resolved
  ties such as `Bus::b` -> `ConnectAsync` and `Bus::a` -> `ChangeConnectorMode`
  with 0.48/0.64 margins. Wave 89 shipped 552 rows, wave 90 shipped 118 rows and
  covered every other pending module with a 6.4 peer (DevKit, ConverterEngine,
  DynamicData.6, Sdk, ActiveTree, ProjectCompare, Common.3, InformationExtract,
  CloudKit, DiagnosticLibrary, SemanticExport, PrintLibrary, PluginLoader,
  KnxCvNext). The CV/<version>/ compatibility copies are addressed through their
  tree-relative path, not the file name.
- **Wave 91: overload aliases.** The rebuild instruction was keyed by declaring
  type and alias only, so two overloads of one type could never share a name and
  the updater emitted `Create2..Create7`, `UpdateFirmware2..4` and hundreds of
  other artificial suffixes. Method instructions are now version 2 and carry the
  parameter list and generic arity, the shared `MemberNameClaims` allows a name
  when every other occupant is a method with a different signature, and
  `Tests/Invoke-OverloadAliasRegression.ps1` proves the round trip: two overloads
  export under one alias, the rebuilt assembly restores both original names and
  signatures, and the original caller still runs. Re-allocating the ledger
  dropped the artificial suffixes from 206 to 50.
- **Preflight performance (wave 91 checkpoint).** `--check-map` over the 6.3 tree
  took 40.5 s on one busy core because the contract-family graph, the member
  scope and the field scope were built over all 528 tree assemblies (101k types,
  DevExpress and 271 translated satellites included). The analysis now runs only
  over the modules a map references while every assembly still resolves, and the
  graph got name-indexed method lookup, memoized substitution, one shared
  comparer, lazy blocker sets and a single SHA256. Measured with
  `NAMECANDIDATES_TIMING=1` on `names63-staged-v91.xml`: 6.6 s (`--update-map`
  7.9 s), and both runs reproduce the checkpointed files byte for byte. The
  remaining single-core time: 0.4 s tree load (528 files / 363 MB), 1.2 s
  virtual-slot seeding (0.75 s of it dnlib's lazy per-type `Overrides`
  initialisation), 3.2 s contract walk (2.7 s interfaces, 1.5 s of that the
  explicit-implementation scan), 0.35 s family hashing, 0.5 s map validation,
  0.46 s field scope. Parallelising the graph needs the lazily materialised
  dnlib tables primed first; the two named per-type hotspots are the next
  candidates.
- **Wave 92: declaration-order alignment.** The 6.3 and 6.4 builds of one
  assembly are the same code compiled twice, so their member tables usually keep
  declaration order. `scratch-transfer.py` now aligns the two member-shape
  sequences (`difflib.SequenceMatcher`) and transfers the 6.4 name for paired
  slots where one readable name shares its shape with obfuscated placeholders.
  Order drifted in some assemblies, so the tool measures the alignment first -
  readable pairs on both sides must agree - and only trusts it when a module
  pair clears 97% over at least 100 pairs and the individual type clears the
  same bar after four pairs. Measured: Falcon 1153/1154 (enabled),
  ConverterEngine 315/316, Common.3 308/316, ObjectModel 0.958 (disabled),
  HawkNET 0.489 (disabled). All 91 Falcon slots the body-fingerprint matcher
  could also decide agree with the aligned name, so wave 92 shipped 98
  order-aligned Falcon rows (the two Common.3 rows were deferred): 7303 reviewed
  edits, 0 errors, check-map PASS, no new auto-suffixes (the 50 pre-existing
  wave-91 collisions stay), the SDK audit still freezes only
  `Knx.Ets.CalculatedParameters.z` and the filtered export map reports
  `sdk-visible=0, sdk-referenced-types=0`. Deferred:
  `Knx.Ets.Common.Wpf.BindableBase::a(System.String)` aligns to the 6.4
  `OnPropertyChanged(System.String)` overload, but a descendant
  (`Knx.Ets.ObjectModel.DomObject`) already declares that signature; the sibling
  `b(System.String)` keeps its v91 name `NotifyPropertyChanged` instead of the
  colliding 6.4 alias.
- **Wave 93: names leaked by compiler-generated remnants.** Dotfuscator renamed
  the methods but left the compiler's own names in place: a method that declares
  a lambda still points at `<>c::<Name>b__K` / `<>c__DisplayClassN_M::<Name>b__K`,
  and an async method is wrapped by `<Name>d__N`. `scratch-lambda-evidence.py`
  names every pending candidate whose body references exactly one such name
  (overloads of one source method share it and stay apart by signature; the
  compiler-generated members themselves and explicit implementations are
  filtered out). Measured before shipping: 6.3 methods that still carry a
  readable name reproduce it from the closure evidence 4272/4296 (99.44%) and
  from the state machine 1142/1158; the exceptions are `method_N` placeholders
  that the evidence names correctly and `IAsyncDisposable.DisposeAsync`
  implementations. Cross-checked against the readable 6.4 counterpart, 227/227
  comparable ObjectModel members agree. Wave 93 shipped 752 rows (751 ObjectModel,
  1 Falcon): 8055 reviewed edits, 0 errors, check-map PASS, no new auto-suffixes,
  the SDK audit still freezes only `Knx.Ets.CalculatedParameters.z` and the
  filtered export map reports `sdk-visible=0, sdk-referenced-types=0`. Twelve
  ObjectModel rows are deferred: Dotfuscator split one source method into
  identical-signature halves, so the declaration scope would suffix their shared
  name (`SpecializedValidate2`, `AfterSpecializedUndo2`, ...).
- **Wave 94: stripped event accessors.** Where the obfuscator removed the event
  row, its `add_`/`remove_` accessors look like ordinary methods and never match
  the 6.4 build's readable counterparts, because the transfer matches by C#
  member class. The body still shows the operation (`Delegate::Combine`/`Remove`)
  and the backing field, so `scratch-event-accessors.py` matches accessors by
  (operation, delegate type) and, when several events share one delegate type,
  by the backing field's position in the paired types. Wave 94 shipped 16 rows
  (10 Falcon.Bus event accessors, 6 Bus segment-coupler helpers matched by exact
  shape plus body evidence): 8071 reviewed edits, 0 errors, check-map PASS, no
  new auto-suffixes, SDK audit unchanged, filtered export map
  `sdk-visible=0, sdk-referenced-types=0`. The same rule finds 54 more accessors
  in ObjectModel, Sdk, Common, DynamicData, ActiveTree, CloudKit and
  SemanticExport, but those keep their `SpecialName` bit and stay blocked as
  `accessor-operator-or-runtime-special-name`.
- **Type renames are the next lever (tooling gap).** `scratch-type-pair-verify.py`
  verified 268 placeholder 6.3 types against readable 6.4 counterparts
  (unanimous member votes, member-shape containment >= 0.9 both ways, matching
  string literals): 177 Falcon (`Class1009` -> `Knx.Falcon.IoT.Stack.Oscore.Utility.OscoreByteConverter`,
  `nc` -> `Knx.Falcon.Device`, `oc` -> `Knx.Falcon.Network`), 89 HawkNET, 2
  DevKit, 1 DynamicData. They cannot be shipped yet: Dotfuscator flattened those
  types into the global namespace, so the alias must carry a namespace, but the
  updater rejects dotted type aliases (`Identifier()`), dnSpy's `SourceNameMap`
  rejects them (`ValidateName`), and the exporter's declaration/restore path only
  carries a leaf alias (`MetadataTypeNames.GetName` + `SourceFullName` prefix the
  type's metadata namespace). Supporting `Namespace.Name` type aliases in those
  three places (plus a declaration-namespace hook in the C# output) unlocks them.
- **Wave 95: verified type renames, namespace-aware declaration scope, closed
  contract graph.** The tooling gap above is closed in three places:
  `NameCandidates --update-map` accepts `Namespace.Name` for type rows and keeps
  the full alias unique per module (`de4dotEx 22a56ae9`), dnSpy's `SourceNameMap`
  exports/restores it (`dnSpy 428d9caa7`), and the exported project builds and
  runs with the type moved (`Tests/Invoke-NamespacedTypeAliasRegression.ps1`).
  Wave 95 shipped 200 of the 268 verified pairs (132 Falcon, 66 HawkNET, 2
  DevKit): `names63-staged-v95.xml` = `4499ABA3EEAE9BFF72C1E202CF563B6F7060CA20E86BFD6083682DC27ECC7EA5`,
  8,271 reviewed edits, 0 errors, `--check-map` PASS.
  Two scope rules had to be corrected for this wave. Dotfuscator flattens every
  metadata namespace to `""`, so the declaration-scope reservation used to treat
  every root type of a module as one C# scope and suffixed the second type that
  wanted a leaf (`Knx.Falcon.Impl.Utilities.TaskExtensions` became
  `...TaskExtensions2`). `MemberNameScope` now scopes a type by the namespace its
  **alias** puts it in, so only same-namespace collisions suffix; the registry
  keeps the full type alias and the scope check still compares leaves. That
  removed the one new auto-suffix: 51 -> 50 rows `Requested != Applied`, all 50
  pre-existing method-overload suffixes from wave 91, none new. The same-leaf case
  is covered by the extended namespaced-alias regression (two types, one leaf,
  two namespaces, exported, rebuilt and executed).
  Separately, `MethodContractFamilies` now analyses every module that can
  contribute a family member (types that implement, derive from or explicitly
  override an analysed type, read straight from the TypeDef/InterfaceImpl/
  MethodImpl tables and closed transitively). Before, a review that renamed a
  contract whose implementation lived in a module the base map did not carry yet
  produced a family without that implementation, which would have renamed the
  declaration alone and broken the implementation. `NameCandidates.Tests` (all
  fixtures) and the dnSpy registry/source-alias regressions pass with it.
  Performance: the tooling hot paths left dnlib `ResolveTypeRef`/
  `ModuleDef.Find` scans in the profile (`de4dotEx 733c9cdc`), so the identity
  map now answers references first, `ToTypeSig(resolveToCheckValueType: false)`
  replaces the value-type probe, modules without `MethodImpl` rows skip override
  materialisation, name classification is memoised and the union-find root pass
  and family grouping run in parallel. On the 6.3 tree: `--check-map` 6.9 s ->
  5.1 s (6.7 s with the implementation closure), `--update-map` 7.6 s -> 6.0 s,
  `--review-families` 21.7 s -> 13.9 s, `--review-obfuscated` 21.4 s -> 12.9 s,
  every output byte-identical to the previous run.
  A second pass (`de4dotEx 06b6213f`, mirrored as `dnSpy 8b6a94d43`) removed the
  remaining dnlib type-finder rescans: the contract context now resolves every
  reference from a per-module type-name index (dnlib only sees exported-type
  forwarders and misses), a type's method list and a member's parameter list are
  read once per pass instead of five and two times, and name classification is a
  concurrent map instead of a lock taken twice per member. `--check-map`,
  `--update-map`, `--review-families` and `--review-obfuscated` still reproduce
  `36A04057…`, `60463931…/CA39B033…`, `27B6C6F3…` and `8179AFA4…` byte for byte.
  Measured on the same 528-assembly tree (wall / process CPU):
  `--check-map` 5.3 s / 7.2 s, `--update-map` 6.1 s / 8.0 s,
  `--review-families` 10.8 s / 21.3 s, `--review-obfuscated` 12.6 s / 15.9 s.
  The SDK surface is unchanged: `--public-api-audit` freezes five rows
  (`sdk-visible=0`, `sdk-referenced-types=5` on the full map) and the filtered
  export map `D:\knx_analysis\names63-staged-v95-sdkfrozen.xml`
  (`89971A85330DCF94BE4CF2ECA6971B8E6AC7611B1881359E4A7A8DCEB7810BD9`) audits
  `sdk-visible=0, sdk-referenced-types=0`.
  Still open: 68 of the 268 candidate type pairs are not pair-verified yet (45
  Falcon, 23 HawkNET), and the ~12k behavioural candidates that the type renames
  now make readable by owner.
- **Wave 96: members of the verified type pairs.** The 200 renamed types give
  every member a known 6.4 counterpart, so `scratch-transfer.py` was seeded with
  the verified pairs (`wave96-seed.json`, 200/200 resolved) and every proposal
  inside those types was re-checked: 527 Falcon, 316 HawkNET and 6 DevKit
  proposals, of which 182 belong to the renamed types and are not mapped yet —
  all of them virtual slots, so they ship as contract families. 94 editable
  families (no blockers, no member mapped yet, one agreed name per family)
  renamed 400 member rows in 39 Falcon and 55 HawkNET families: 8,671 reviewed
  edits, 0 errors, `--check-map` PASS, `names63-staged-v96.xml` =
  `7A396AEC4288D7F4…`. One new auto-suffix appears:
  `Knx.Ets.HawkNET.dll|0x06001064` (`Class302::c`) was `Apply` and becomes
  `Apply2` because the family now claims `Apply` for `Class302::vmethod_0`, the
  interface slot it also implements — a Dotfuscator split twin, the same pattern
  wave 93 deferred. The other 50 suffixes are unchanged from wave 91. The SDK
  surface is unchanged: five frozen rows, export map
  `D:\knx_analysis\names63-staged-v96-sdkfrozen.xml` (`5E9B0C236F771215…`) audits
  `sdk-visible=0, sdk-referenced-types=0`.
  Deferred to a later wave: the other 87 proposals are further members of the
  same 94 families (the transfer matched several members of one family to the
  same slot name, which the atomic family row already covers) and one
  explicit-interface implementation stays blocked, plus the separate
  `FamilyProposals` (Falcon 23) that still need per-family evidence.
- **Wave 97: the transfer's remaining re-matches.** The seeded run also named
  members of types whose pairing it had previously missed: 18 editable families
  (60 member rows) in Falcon (11), HawkNET (6) and DevKit (1) —
  `names63-staged-v97.xml` = `1A009659BEE1DB67…`, 8,731 reviewed edits, 0 errors,
  `--check-map` PASS and **no new auto-suffixes** (still the 50 pre-existing
  ones plus the wave-96 split twin). Three proposals stay blocked as explicit
  interface implementations, and two families were already mapped. The SDK
  surface is unchanged: five frozen rows, export map
  `D:\knx_analysis\names63-staged-v97-sdkfrozen.xml` (`AEA35080…`) audits
  `sdk-visible=0, sdk-referenced-types=0`.
- **Wave 98: 237 further verified types, with the type gate corrected.**
  Re-running the pair verification showed that the strict gate rejected 253
  pairs for the wrong reason: it reused `MethodNameAnalysis` (a *method*-name
  heuristic) for the 6.4 **type** name, so legitimate domain nouns such as
  `Timing`, `Session`, `SRP` or `IoTPublisher` counted as unreadable and the pair
  failed before the shape check ran. The corrected gate asks only that the 6.4
  name is a real identifier (no `ClassN`/`InterfaceN`/short-letter placeholder)
  and keeps the independent evidence unchanged: membership by member votes
  (252 of the 253 unanimous, one 17/18), member-shape containment ≥ 0.9 in both
  directions (minimum 0.9) and the exact member-name transfer. 237 of them
  shipped (16 dropped as unusable nested/generic aliases): 120 Falcon, 50
  HawkNET, 43 DynamicData, 15 Common, 12 DiagnosticLibrary, 7 CloudKit, 5 DevKit,
  1 KnxCvNext. `names63-staged-v98.xml` = `6046393110E83884…`, 8,968 reviewed
  edits, 0 errors, `--check-map` PASS, **no new auto-suffixes** and the SDK
  surface unchanged (five frozen rows; export map
  `D:\knx_analysis\names63-staged-v98-sdkfrozen.xml`, `640BED9E…`, audits
  `sdk-visible=0, sdk-referenced-types=0`).
- **Wave 99: the transfer's members inside the wave-98 types.** The second
  seeded transfer run proposed 169 members of the wave-98 renamed types (94
  HawkNET, 75 Falcon), all with one agreed name per contract family. 92 of the
  96 families they touch were already mapped in waves 96-97 and one stays
  blocked as an explicit interface implementation, so the wave ships 3
  contract families (12 member rows) plus 3 ordinary Falcon methods
  (`FromFailure`, `FromInvalidJson`, `TryGetFailureReport`) that have no family
  row at all — `families63-w96.json` lists only virtual members, and the first
  version of the apply script silently dropped every candidate without one.
  `names63-staged-v99.xml` = `ED481D1F5F2C6823…` (8,983 reviewed edits, 0
  errors, `--check-map` PASS, still the 51 known auto-suffixes, no new ones).
  The SDK surface is unchanged: five frozen rows, export map
  `D:\knx_analysis\names63-staged-v99-sdkfrozen.xml` (`1F739A79…`) audits
  `sdk-visible=0, sdk-referenced-types=0`.
- **Wave 100: generic type aliases and the Falcon event raisers.** The map
  updater used to reject every generic type, so 16 verified wave-98 pairs
  (`TreeNode`1`, `FileCache`1`, `AsyncStateTransition`4`, …) could never ship.
  A generic type's metadata name carries its arity while its source alias does
  not: the binary applier writes the suffix back from the type's own generic
  parameters and `MetadataTypeNames.SourceMetadataName` already appends it for
  the rebuild instruction, so the renamer now pastes `Foo`1`, the tools check
  the arity and normalise it, and both the binary and the source path stay
  correct (`de4dotEx 2fd0dedf`, `dnSpy 09dda453a`, with the new
  `Invoke-GenericTypeAliasRegression.ps1` and the ApplyMapReference `Box<T>`
  case). 15 of the 16 ship — the DevKit pair's 6.4 name is itself obfuscated
  (`t2K3r6oJiIcJNf2FY2aX.kw9mOEoJ1scMbFbydwLH`1`), so it is skipped on purpose.
  The wave also names the three `Knx.Falcon.Bus` event raisers behind the
  already-mapped accessors: `0x060025CB`→`OnConnectionPropertyChanged`,
  `0x060025CD`→`OnGroupMessageReceived`, `0x060025D0`→`OnKnxMessageReceived`
  (each invokes the delegate field of its event and logs
  `Exception in <event>: {0}`).
  `names63-staged-v100.xml` = `FAD1D714DE6238C1…` (9,001 reviewed edits, 0
  errors, `--check-map` PASS, still the 51 known auto-suffixes). The SDK
  surface is unchanged: five frozen rows, export map
  `D:\knx_analysis\names63-staged-v100-sdkfrozen.xml` (`674D2C0E…`) audits
  `sdk-visible=0, sdk-referenced-types=0`.
  Batch rename check: `--apply-map` applied that export map to the 528-assembly
  tree in 58 s wall / 60 s CPU (1.04 cores) — 803 types, 7,669 methods, 1,259
  fields, 1,359 parameters plus 521 TypeRefs and 949 MemberRefs rewritten
  without naming a single reference token, 528 modules written, 0 errors; all
  528 output assemblies still load and the renamed generic types keep their
  arity (`Knx.Ets.Common.Caching.FileCache`1`, `Knx.Falcon.Impl.TreeNode`1`).
- **Wave 101: behavioural names from the members' own strings.** The 6.4
  transfer is exhausted (`scratch-transfer.py` was re-run for the last module
  pairs: ObjectModel's 6.4 build proposes only already-mapped members and real
  accessors, the ETS executables propose nothing; the 6.4 build of
  `ExtendedCopyImporter` carries the same `method_N` names as 6.3). 698 pending
  members do state what they do in their own literals, e.g.
  `"Failed to delete cache directory '"`, `"Cannot get Challenge from encrypted
  message"`, `"Cannot extract ZIP container {0} …"`. Wave 101 ships the 34
  whose statement maps one-to-one onto a name (`DeleteCacheDirectory`,
  `GetChallenge`, `ExtractZipFile`, `UpgradeTemplateFile`, `ProcessFrame`,
  `ReadKnxPackage`, …) in ObjectModel (19), Falcon (12) and Common (3);
  `names63-staged-v101.xml` = `C4F783D4066F0BB3…`, 9,035 reviewed edits, 0
  errors, `--check-map` PASS, the same 51 auto-suffixes. Two candidates are
  deferred because they are contract-family members whose other members have no
  evidence (the `IObjectRepresentationData::iz` slot with 12 implementations).
  The SDK surface is unchanged: five frozen rows, export map
  `D:\knx_analysis\names63-staged-v101-sdkfrozen.xml` (`E212402A…`) audits
  `sdk-visible=0, sdk-referenced-types=0`.
- **Batch-applier performance (same turn as wave 102).** The 40 s "low CPU, low
  IO" report was the `--apply-map` write phase: dnlib's normal writer
  re-materializes every module and every lazily materialized `MemberRef` asks
  `AssemblyResolver.Resolve` for its declaring type, which serializes all
  writer threads on one exclusive lock (the tree asks ~600k times for ~5k
  distinct (scope, type) pairs). The applier now memoizes that fallback per
  (source directory, scope identity, type name) and copies modules the map
  cannot change byte for byte instead of rewriting them (`CopiedModules`,
  `ModulesCopied`). Wave-101 batch apply: 29.4 s -> 10.6 s wall, 72.4 s ->
  24.6 s CPU, 68 modules rewritten and 460 copied, every rewritten module
  byte-identical to the previous output and every copied module byte-identical
  to its input (all 528 still load). de4dotEx `050f7a09`; see
  `tools/NameCandidates/README.md` for the profile and the regression fixture.
  The follow-up `21748706` skips resolving references whose own name matches no
  renamed definition (dnlib resolves a TypeRef by full name and a MemberRef by
  member name, so those references can never produce a row): the 553-assembly
  6.4 tree's cold `--apply-map` went 43.5 s -> 8.5 s and the 6.3 wave-101/wave-102
  maps now apply in 8.6 s, all outputs byte-identical (553/553 and 528/528
  files, SHA256).
- **Wave 102: the remaining string-evidenced members.** The same rule as wave
  101 applied to the members whose literal states the operation directly:
  `"Invalid signature detected: {0}"` -> `ValidateSignature` in both ETS6C/N
  executables, `"Invalid shift for replay window"` -> `SetReplayWindowShift`,
  `"The HKDF algorithm {0} is not supported!"` -> `CreateKeyDerivationFunction`,
  the four COSE attribute readers, `"Unknown association table format"`-style
  validators, `"IoT Failed to extract KNX serial number from mDNS Name {0}"` ->
  `ExtractSerialNumberFromMdnsName`, and so on. 17 rows ship in HawkNET (3),
  Falcon (12) and the two executables (2); one further candidate
  (`Knx.Ets.HawkNET.dll|0x0600009A`) is deferred because it is a virtual member
  whose contract family has no evidence for its other members, exactly like
  wave 101's two deferrals. `names63-staged-v102.xml` =
  `EA3DE48F704FE63614923FCC2E5F610B7D2E3D601074DAF0255183F7369EEC3C`, 9,052
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). The SDK surface is unchanged: five frozen rows, export map
  `names63-staged-v102-sdkfrozen.xml` (`C4D4A55D…`) audits `sdk-visible=0,
  sdk-referenced-types=0`. The batch check applied that export map to the
  528-assembly tree in 10.6 s wall (0 errors) and all 528 outputs load with the
  wave-102 names present.
- **Wave 103: property and event accessors restored from their own rows.** The
  obfuscator renamed accessor *methods* but left the property/event rows (and
  their names) intact, so `get_Foo`/`set_Foo`/`add_Changed` is derived evidence:
  C# binds an accessor to its row only through that conventional prefix plus the
  row's own name. The new `--suggest-accessors` command (de4dotEx `48d9f6c1`)
  derives those names, and the map updater now accepts an accessor row only when
  it equals the derived name (never a suffix). Of 1,635 candidates, 1,299 ship:
  956 new rows plus 343 rows that were recorded as explicit *unresolved*
  decisions ("property accessor; SourceNameMap v1 does not alias runtime special
  names") in earlier waves. Deliberate interop names (`get_uri` in WebView2's raw
  COM interfaces, WinRT `put_`) and accessors whose own row carries no readable
  name (23,880) stay explicit work items. One row is deferred:
  `Knx.Ets.DynamicData.dll|0x06000291` derives `get_Id`, which collides in its
  declaration scope, and an accessor name is never suffixed. Rows in the four SDK
  modules stay untouched. `names63-staged-v103.xml` =
  `4DA5229684D9A1C31C386ECF53F4ABD8D1BA047D9D7FAA96E53613FF91A244A7`, 10,637
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v103-sdkfrozen.xml`
  (`61D711DE04AAA422…`) audits `sdk-visible=0, sdk-referenced-types=0`. The batch
  check applied it to the 528-assembly tree in 8.7 s (0 errors); every output
  loads, the renamed accessors are present and `ey.Address` still keeps both of
  its accessors linked. dnSpy enforces the same derived-name rule in
  `SourceNameMap` (`Tests/Invoke-AccessorAliasRegression.ps1`), and the whole
  10-test battery passes.
- **Wave 104: the ExtendedCopy importer's behavioural names.** The 6.4 transfer
  and the mechanical channels are exhausted, so this wave names members from the
  physical evidence of their own bodies, read with dnSpy's IL output: the
  operation type a method creates (`LinkGroupAddressRefToFunctionOperation` ->
  `LinkGroupAddressRefsToFunctions`, `ChangeDeviceSecurityOperation` ->
  `ApplySecurityChanges`), the framework/ETS call it is built from
  (`CopyDeviceOperation.CallDevicePlugInsHandler` -> `CallDevicePluginsHandler`,
  `Strategy.CreateThreeLevelMiddleGroup...` -> `CreateThreeLevelGroupRange`), the
  XML attribute it reads or writes (`"IsActivityCalculated"` ->
  `SetActivityCalculated`, `"Required attribute '"` -> `GetRequiredUInt16Attribute`)
  and the mapped neighbours that call it (`AddArea`/`AddLine` -> the
  `AddAreaOperations`/`AddLineOperation` loops). 40 rows in
  `Knx.Ets.ObjectModel.dll`'s `Operations.ExtendedCopy.ExtendedCopyImporter`;
  each ledger row carries its evidence in `Reason`. The type is now complete
  except `0x060049CF`, the device address/domain-address reader, whose evidence
  does not fix a name yet.
  `names63-staged-v104.xml` =
  `6EF55F077D208CB962C935F72F5324CE897D7713DAF43E955AD2E0C08AD18841`, 10,677
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v104-sdkfrozen.xml`
  (`BA5C859EBC9FFEDB…`) audits `sdk-visible=0, sdk-referenced-types=0`. The batch
  check applied it to the 528-assembly tree in 8.7 s (0 errors); all outputs
  load, the new names are present and the renamed helper is still called by
  `Synchronize`.
- **Tooling performance: the "slow but idle" runs (de4dotEx `4853fa45`).** The
  wave tools spent tens of seconds at a fraction of one core with no disk
  traffic. Two causes: a console app gets the *workstation* collector, which
  serialised the metadata allocations of every parallel phase (the waiting does
  not appear as CPU), and several serial/quadratic passes (`--update-map`
  re-scanned every row of a module per edit and again per method row).
  `ServerGarbageCollection` is now on (the runtime config carries
  `System.GC.Server=true`; `DOTNET_gcServer=0` opts out for a lower peak working
  set), module reads/parses/hashes and the per-module inventories, the per-type
  contract walk, the implementation closure and the accessor scan run in
  parallel with results merged in input order, and a module's rows are indexed
  by (kind, token) and its alias set built once.
  Measured on the 528-assembly 6.3 tree, every output byte-identical
  (wall / process CPU): `--check-map` 5.6 s/7.4 s -> 3.1 s/8.0 s,
  `--update-map` 6.6 s/8.7 s -> 3.4 s/7.0 s, `--review-families` 10.8 s/19.8 s
  -> 4.6 s/33.6 s, `--suggest-accessors` 11.7 s/18.3 s -> 4.4 s/32.0 s,
  `--review` 23.8 s/42.3 s -> 7.7 s, `--review-obfuscated` 12.5 s/15.8 s ->
  3.5 s/18.8 s, `--apply-map` 9.0 s -> 4.8 s (528/528 applied files
  SHA256-identical). The 553-assembly 6.4 tree's `--review` went 25.4 s -> 8.4 s.
  The NameCandidates fixture suite and the ten dnSpy source-map regressions
  pass; `dnSpy.Decompiler/MSBuild/MethodContractFamilies.cs` is the mirrored
  copy.
- **Wave 105: the device-move helper names.** 21 rows in
  `Knx.Ets.ObjectModel.dll`'s `Operations.Devices.MoveDeviceAcrossProjectOperation`
  named from their own IL and the mapped neighbours: the segment/validators
  (`GetTargetSegment`, `GetMovableDevices`, `CreateMediumTypeValidator`,
  `CreateRfMainLineMultiDeviceValidator`, `HasSecurityImpacts`), the per-device
  copy steps (`MoveDevice`, `CopyDevices`, `MergeMovedDevices`,
  `CopyLoadedImage`, `CopyBinaryData`, `CloneDeviceGroupTree`,
  `UpdateComObjects`, `UpdateModuleInstances`, `MoveAdditionalAddress`,
  `CanCopySerialNumber`, `IsIndividualAddressChanged`, `ToByteAddress`,
  `GetComObjectRefCache`) and the failure collector
  (`ForEachCollectingFailures`). The last one is worth a note: the compiler's
  lambda name `<WithLoggingAndContinue>b__0` shows the method's original name was
  `WithLoggingAndContinue`, but `OperationBase` already declares
  `WithLoggingAndContinue<T>(ILog, IEnumerable<T>, Action<T>, Func<T, string>)`
  and the two differ only in their return type, so the declaration-scope rule
  cannot reuse it and the behaviour-derived name is used instead. The first
  `--update-map` run suffix-ified that row (`WithLoggingAndContinue2`) and the
  wave was re-run from the ledger per the wave rule: no new auto-suffixes.
  `names63-staged-v105.xml` =
  `15E8D9F804E7B0A75C20F2C0CCF8E5199E656EE72DB1579C81B76614EB9DBE50`, 10,698
  reviewed edits, 0 errors, `--check-map` PASS, the same 51 auto-suffixes. SDK
  surface unchanged: export map `names63-staged-v105-sdkfrozen.xml`
  (`B1BB9B8E44AD6372…`) audits `sdk-visible=0, sdk-referenced-types=0`. The batch
  check applied it to the 528-assembly tree in 5.0 s (0 errors, 528/528 load);
  `CopyDevices` still calls `MoveDevice` and `MergeMovedDevices`, and
  `CallDevicePlugInsHandler` still calls `ForEachCollectingFailures`.
- **Wave 106: the group-address import pipeline.** 24 rows in
  `Knx.Ets.ObjectModel.dll`'s
  `Operations.GroupAddressImportExport.ImportGroupAddressesOperation`, named from
  each member's own IL plus the readable neighbours already in the map: the
  reader and style detection (`CreateImportReader` reads `.CSV`/`.XML` into the
  CSV/XML reader and throws `FormatException` otherwise; `DetectGroupAddressStyle`
  and `DetectGroupAddressStyleFromRanges` answer the `GroupAddressStyle` from the
  `Address` attribute and from `Range.IsMainGroupCompliant/IsMiddleGroupCompliant`),
  the CSV fix-up (`MergeMultilineCsvRecords` joins continuation lines with
  `"\r\n"`, normalizes and rewrites the file), the import steps
  (`ImportGroupAddress`, `ImportGroupRange`, `CreateGroupAddressForImportValue`,
  `CreateGroupRangeForImportValue`, `EnsureGeneratedMainGroupRange`,
  `TryMapImportedAddressToRange`, `GetTargetRangeIdForGroupAddress`,
  `GetTargetRangeIdForGroupRange`, `FindCreatedGroupRangeId`,
  `CollectExistingGroupAddresses`, `CreateGroupRangeMapping`), the existing-address
  handling (`IsExistingGroupAddress`, `ResolveExistingGroupAddressFlags`,
  `SetSecurityModeForExistingGroupAddress`), the helpers
  (`SetFirstDatapointType`, `IsUsableImportedAddress`, `ValidateImportedGroupRange`,
  `FormatGroupAddressMessage`, `RunWithUndoDisabled`, `ResolveInconsistency`) and
  the inconsistency prompt. `0x06004574` is an empty method with no callers in
  the graph and stays an open item. `names63-staged-v106.xml` =
  `6CCF8E28697BF5F6CD529ABA28ACE6E8F1589769B65881551645215647077983`, 10,722
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v106-sdkfrozen.xml`
  (`88B5636B1983EBA5…`) audits `sdk-visible=0, sdk-referenced-types=0`. The batch
  check applied it to the 528-assembly tree in 7.3 s (0 errors, 528/528 load);
  `SpecializedValidate` still calls `CreateImportReader`/`DetectGroupAddressStyle`,
  `SpecializedExecute` still calls `ImportGroupAddress`/`ImportGroupRange`, and
  the address/range creation helpers keep their callers.
- **Wave 107: the group-address change (rename) operation.** 23 rows in
  `Knx.Ets.ObjectModel.dll`'s `Operations.GroupAddress.ChangeGroupAddressOperation`.
  The constructor stores `IGroupAddress.Address` in field `b` and its `value`
  parameter in field `c`, which is what makes the three changer groups readable:
  the `Changer` applies the new address (`TrackAddressChange`,
  `SetNewAddressWithUndoDisabled`, `SetNewAddressAndNotifyReferences`),
  `UndoChanger` restores the old one (`TrackAddressUndo`,
  `SetOldAddressWithUndoDisabled`, `SetOldAddressAndNotifyReferences`) and
  `RedoChanger` re-applies the new one (`TrackAddressRedo`,
  `SetNewAddressForRedoWithUndoDisabled`,
  `SetNewAddressAndNotifyReferencesForRedo`). `method_8/9/10` are the bodies
  behind `get_Changer`/`get_UndoChanger`/`get_RedoChanger` (`ChangeItemAddress`,
  `UndoItemAddress`, `RedoItemAddress`), `method_11` is the constructor's
  `TrackSourceObject`, `SpecializedUndo`/`SpecializedRedo` go through
  `UndoSwappedItem`/`RedoSwappedItem`, and `GetSubGroupAddressText` is the
  description helper that answers with `ThreeLevelSubGroupAddress`,
  `TwoLevelSubGroupAddress` or the plain address for
  `GetSingleItemLocalizedWithValueDescription`. `names63-staged-v107.xml` =
  `7DDC482FD55438F1FCA93518BD3745CE618B08E1D102CF5BA6F78CEF9EFEB7AC`, 10,745
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v107-sdkfrozen.xml`
  (`06B276910A47494B…`) audits `sdk-visible=0, sdk-referenced-types=0`. The batch
  check applied it to the 528-assembly tree in 5.1 s (0 errors, 528/528 load);
  `Knx.Ets.Sdk.dll` still constructs `ChangeGroupAddressOperation`, and the
  change/undo/redo trackers keep their callers.
- **Wave 108: the installation merger's element and attribute handlers.** 21 rows
  in `Knx.Ets.ObjectModel.dll`'s `Import.InstallationMerger`. The pairs inside
  `get_ElementSettings` and `get_AttributeCallbacks` are the evidence, together
  with the writer field each `With...Writer` assigns (`WithTradesWriter` ->
  `iwriter_2`, `WithSplitInfosWriter` -> `iwriter_7`, `WithBuildingsWriter` ->
  `iwriter_0`, `WithGroupAddressesWriter` -> `i`,
  `WithUnassignedDevicesWriter` -> `m`, `WithAreaWriter` -> `iwriter_4`,
  `WithBusAccessWriter` -> `iwriter_6`, `WithInstallationWriter` -> `iwriter_3`):
  `CloneTradesElement`, `CloneSplitInfosElement`, `CloneBuildingsElement`,
  `CloneGroupAddressesElement`, `CloneUnassignedDevicesElement`,
  `CloneAreaElement`, `CloneBusAccessElement`, `WriteInstallationElement`,
  `PatchIdAttribute`, `PatchRefIdAttribute`, `PatchGroupAddressRefIdAttribute`,
  `PatchDefaultLineAttribute`, `ScrambleBcuKeyAttribute` (BCUKey through
  `BcuKeyScrambler`), `TransformPasswordValue` (the secret attributes through
  `IPasswordHandler.WriteValue`/`ReadValue` by `Direction`), `FormatEdiGuid`
  (the `Edi` attribute as `Guid.ToString("B").ToUpperInvariant()`),
  `NormalizeDisabledAttribute`, `CollectDeviceInformation`
  (`DeviceCount`/`AddSerialNumber`/`PopulateDevice`), `CountLineElement`,
  `MergeBinaryDataElement`, `CountFunctionElement` and `CountRoomElement`.
  `names63-staged-v108.xml` =
  `2781CB1EDBE5AA41D3D430B43327115CD2620480DA5592C6951183640A661AAC`, 10,766
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v108-sdkfrozen.xml`
  (`B1B804C12688E0EB…`) audits `sdk-visible=0, sdk-referenced-types=0`. The batch
  check applied it to the 528-assembly tree in 4.7 s (0 errors, 528/528 load);
  every handler still resolves from `get_ElementSettings`,
  `get_AttributeCallbacks`, `get_DeviceSettings` and `get_LocationsSettings`.
- **Wave 109: the project device's collection, certificate and usage plumbing.**
  23 rows in `Knx.Ets.ObjectModel.dll`'s `Project.Device`: `InitializeCollections`
  (builds `BinaryDatas`, `AdditionalAddressesCollection`, the consistency
  validator, `BusInterfaceCollection`, the non-default channel/com-object
  managers and `LazyChannelInstanceCollection`),
  `OnUsageChannelsChanged` / `IsAddedUsageForApplicationProgram` /
  `IsRemovedUsageForApplicationProgram` (the usage-collection wiring through
  `UsageInstallationEventManager` and `Usage.MatchesAppPrg`),
  `UpdateDeviceCertificateAssignment` (the `DeviceCertificateCollection`
  registration moves with the serial number), `ResetIndividualAddress` /
  `OnIndividualAddressReferenceChanged` (the address plus bus-interface display
  names), `SynchronizeDeviceState` / `SynchronizeNonDefaultParameters` (the
  reader side of `InternalSynchronize`),
  `AttachPasswordChangeObserver` / `DisposePasswordChangeObserver` /
  `OnIsProvidingSecureTunnelingChanged` (the `"Password"`/`"PasswordHash"`
  observer over `BusInterfaceCollection`), `WriteGroupTree`,
  `AcquireInitialParamCalcLock` / `ReleaseInitialParamCalcLock` (the volatile
  counter behind `GetInitialParamCalcActiveLock`), `OnAfterBind`,
  `OnActiveComObjectInstancesChanged` / `OnActiveComObjectsLoaded` /
  `OnActiveChannelInstancesChanged`, `LoadApplicationProgramDynamic`,
  `EnsureCalculator`, `NotifyTextParameterRefChanged` and `OnDispose`.
  `names63-staged-v109.xml` =
  `3E14805AE84907253AC546CA12DAD5B3444F6137069D0EF52FA7DA7E4DDA6B61`, 10,789
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v109-sdkfrozen.xml`
  (`96FEB7B6A48E4D8B…`) audits `sdk-visible=0, sdk-referenced-types=0`. The batch
  check applied it to the 528-assembly tree in 4.5 s (0 errors, 528/528 load);
  the device constructor, `InternalSynchronize`, `Dispose`,
  `set_Address`/`SetAddressWithoutUndo` and the explicit
  `IInternalDevice` members all keep their callees.
- **Wave 110: the communication-object instance.** 20 rows in
  `Knx.Ets.ObjectModel.dll`'s `Project.ComObjectInstance`:
  `RegisterTextParameterRef` / `UpdateTextFromParameterRef` /
  `InvalidateTextCache` (the `TextParameterRefManager` registration and the
  `ModuleArgManager.CheckArgumentText` call for the `"TextParam"` argument),
  `InitializeFromComObjectRefInfo` (the `ComObjectRefInfo` initializer),
  `UpdateTextsFromModuleArguments` / `OnTextChanged` / `OnFunctionTextChanged`
  (the `"Text"`/`"FunctionText"` arguments),
  `UpdateChannelInstanceFromUsage` / `FindChannelInstance` plus the four
  predicates the search passes to its collections (`MatchesDeviceChannel`,
  `MatchesMainModuleChannel`, `MatchesSubModuleChannel`,
  `MatchesParentModuleChannel` — all compare `AppPrgChannelId` with the
  instance's `ChannelId`), `NotifyComObjectActivityChanged`,
  `UpdateDatapointTypeRefs`, `ResolveDatapointType` /
  `ResolveDatapointTypeForDefaults` (master-data lookups),
  `IsToDoItemOfThisInstance`, `OnPriorityChanged`, `OnNameChanged` and
  `OnDispose`'s neighbours. `names63-staged-v110.xml` =
  `FDA638C9F5B254E0A5AC948E679BC7D84544EC234ECFD0991916C9516393B987`, 10,809
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v110-sdkfrozen.xml`
  (`B7406D05D01CEA08…`) audits `sdk-visible=0, sdk-referenced-types=0`. The batch
  check applied it to the 528-assembly tree in 4.6 s (0 errors, 528/528 load);
  the constructors, `set_IsActive`, `set_Priority`, `get_Name`,
  `get_ParentChannel` and `set_DatapointTypes` all keep their callees.
- **Wave 111: the project merger's element and attribute handlers.** 14 rows in
  `Knx.Ets.ObjectModel.dll`'s `Import.ProjectMerger`.
  `get_ProjectTagElementSettings` pairs `Naming.Project`,
  `Naming.ProjectInformation` and `Naming.ProjectTags` with
  `CloneProjectElement`, `WriteProjectInformation` (which adds
  `Birdy-PasswordCompareHash` and `Birdy-PasswordHash-IV`) and
  `CloneProjectTagsElement`; `get_HistoryEntriesElementSettings`,
  `get_ToDoItemsElementSettings`, `get_ProjectTracesElementSettings`,
  `get_DeviceCertificatesCountElementSettings` and
  `get_DeviceCertificatesElementSettings` name
  `CloneHistoryEntriesElement`, `CloneToDoItemsElement`,
  `CloneProjectTracesElement`, `CountDeviceCertificateElement` (through
  `IProjectCounter.AddSerialNumber`) and `CloneDeviceCertificatesElement`;
  `get_AttributeCallbacks` pairs `"Password"`, `"Id"`, `"RefId"`, `"Name"`,
  `"FDSK"` and `"Guid"` with `TransformPasswordValue` (the
  `PasswordDescrambler`/`PasswordScrambler` and `IPasswordHandler` by
  `Direction`), `PatchIdAttribute`, `PatchRefIdAttribute`,
  `RenameNameAttribute` (the `WithRenamer` function), `TransformFdskValue` and
  `PatchGuidAttribute`. `names63-staged-v111.xml` =
  `188CEC95E99A5E5DBA42F09022F6571366DA82E06164FDB0FD2880351A62A06F`, 10,823
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v111-sdkfrozen.xml`
  (`569FA1BD2D56538A…`) audits `sdk-visible=0, sdk-referenced-types=0`. The batch
  check applied it to the 528-assembly tree in 4.5 s (0 errors, 528/528 load);
  every handler still resolves from its settings getter or
  `get_AttributeCallbacks` (the two mergers share `TransformPasswordValue`,
  `PatchIdAttribute` and `PatchRefIdAttribute` names because they are declared in
  different types).
- **Wave 112: the group-address unlink operation.** 13 rows in
  `Knx.Ets.ObjectModel.dll`'s
  `Operations.GroupAddress.UnlinkGroupAddressOperation`: the two execute paths
  (`UnlinkConnectors` for an explicit connector list and
  `UnlinkAllGroupAddressConnectors`, which logs
  `"...unlinking all connectors from group address {0} {1} "`), the
  per-com-object-instance unlink
  (`UnlinkConnectorsFromComObjectInstance`, `TrackConnectorsOfComObjectInstance`),
  `CollectAffectedDevices` for `CreateValidators`, and the connector/device
  predicates of `get_Connectors` (`IsTargetConnector`,
  `GetAffectedConnectorsOfComObjectInstance` /
  `IsConnectorOfComObjectInstanceAffected`,
  `GetAffectedConnectorsOfGroupAddress` / `IsConnectorOfGroupAddressAffected`)
  and of the validator pass (`IsComObjectInstanceOnAffectedDevice`,
  `GetConnectorsOfGroupAddressOnAffectedDevices`, `IsConnectorOnAffectedDevice`).
  `names63-staged-v112.xml` =
  `81FD3CA295D64926EC3248F7C12D826BDA1FC2B0BF6EA7918B5385BEC19205E4`, 10,836
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v112-sdkfrozen.xml`
  (`C9A9CE7B73A13E90…`) audits `sdk-visible=0, sdk-referenced-types=0`. The batch
  check applied it to the 528-assembly tree in 4.4 s (0 errors, 528/528 load);
  `SpecializedExecute`, `CreateValidators`, `get_Connectors` and
  `UnlinkComObjectInstance` all keep their callees.
- **Wave 113: the device copy operation.** 19 rows in
  `Knx.Ets.ObjectModel.dll`'s `Operations.Devices.CopyDeviceOperation`: the two
  entry points (`GetCopyableDevices` for the dialog list and `CopyDevices` for
  the workspace clone), the content copier (`CopyDeviceContents` and its
  `CloneGroupTree`, `CopyFirmwareImage`, `CopyBinaryData`,
  `CopyNonDefaultComObjects`, `CopyModuleInstances`, `CopySecuritySettings`
  steps), the address/segment handling (`CreateCopiedIpConfig`,
  `MarkCopiedDevicesModified`, `ChangeAdditionalAddress`, `ToByteAddress`,
  `GetTargetSegment`), the plug-in notification (`NotifyDevicePlugIns`,
  `ForEachCollectingFailures`) and the sharing caches/validators
  (`GetComObjectRefCache`, `CreateMediumTypeValidator`,
  `CreateRfMainLineMultiDeviceValidator`). `names63-staged-v113.xml` =
  `3629B068C3F77BF70E602B81AB972864CBA898995978BA59127E6DEE29BE3E13`, 10,855
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v113-sdkfrozen.xml`
  (`9D8A84DB21C227CB5E39375533249F926D2CB8D607D020757A19CF9EB1870B42`) audits
  `sdk-visible=0, sdk-referenced-types=0`. The batch check applied it to the
  528-assembly tree in 4.8 s (0 errors, 528/528 load); every renamed copier
  still binds from `CopyDevices`/`CopyDeviceContents` and
  `GetComObjectRefCache` keeps its 20 callers across `MoveDeviceAcrossProjectOperation`,
  `ObjectContext`, `Caches` and `AppPrgInfoDynamicFacade`.
- **Cross-version scanner performance (de4dotEx `50c7c61c`).** The remaining
  "40 s at a fraction of one core" command was the scanner behind
  `--reference-source-map` (and the plain `<reference-tree> <target-tree>`
  candidate scan, which shares its walk): the module pairs ran on one thread and
  each of its up to eight rounds rebuilt both fingerprint indexes from scratch,
  plus a per-group re-scan of every type seed. The pairs are pure, so they now
  run on `ProcessorCount` threads and merge in target order (a module's failure
  is rethrown after the merge, exactly like the sequential loop stopped); a
  fingerprint is cached per method and only the callers of a method that just
  gained an anchor are recomputed; the declaring-type rule for type anchors is
  indexed once per pair and an embedded `MemberRef`'s declaring-type walk is
  memoized per pair. Fingerprint values are unchanged — the document is hashed
  from the serializer's UTF-8 bytes through a per-thread buffer instead of the
  UTF-16 string plus its UTF-8 copy. Reports are SHA256-identical: 6.4
  reference -> 6.3 target 50.5 s/81.0 s CPU -> 11.1 s/79.0 s, 6.3 reference ->
  6.4 target 58.7 s/95.6 s -> 11.8 s/97.4 s, plain 6.4 -> 6.3 48.2 s/77.3 s ->
  10.2 s/73.5 s. `NAMECANDIDATES_TIMING=1` prints the scanner's
  map/list/read/seed/round/hash split; the NameCandidates fixture suite and the
  ten source-map regressions pass.
  Re-measured on this machine (16 logical processors) with a fresh Release
  build of `50c7c61c` and the wave-124 map, against the pre-fix build kept in
  `D:\knx_analysis\perfcheck3\before-root`: `--check-map` 5.8 s / 7.3 s CPU ->
  3.2 s / 8.4 s, `--update-map` 3.9 s / 7.2 s, `--review-obfuscated`
  12.4 s / 15.9 s CPU (1.3 busy cores) -> 2.9 s, and the plain 6.4 -> 6.3
  whole-tree scan 58.4 s / 59.0 s CPU (1.01 busy cores) -> 10.0 s / 74.6 s
  (7.5 busy cores). Every report the two builds wrote is byte-identical.
- **`--review-map` and the contract-reference manifest (de4dotEx `e8b0d15a`).**
  `--review-map` turns a reviewed ledger into a source map, and for an
  inventory that carries type, field, parameter, local or contract-family rows
  it delegates to the transactional updater — which refuses a ledger whose
  `ContractReferenceSha256` is set unless it receives the same manifest. The
  CLI only accepted `--contract-references` for `--review-families`,
  `--suggest-accessors`, `--update-map`, `--merge-map` and `--check-map`, so
  every manifest-bound review failed the check with no way to satisfy it.
  `--review-map` now takes the manifest as well (help text and tool README
  updated). The wave-124 ledger converts in 3.4 s with 11,092 edits and 0
  errors; `--update-map`/`--check-map` still publish byte-identical maps and
  reports, and the fixture suite's 20 scenarios pass.
- **Wave 114: creating devices from a template.** 16 rows in
  `Knx.Ets.ObjectModel.dll`'s
  `Operations.Devices.CreateDeviceFromTemplateOperation`: the template filter
  (`GetTemplatesValidForSegment`, which feeds the `SpecializedValidate`
  closure) and the product import (`ImportDeviceProducts`,
  `CreateProgressManager`), the segment and security checks
  (`CanAddDeviceToSegment`, `CreateIpSecureBackboneValidator`,
  `HasMyProductsLicense`, `IsModularApplication`), the parameter plumbing
  (`AttachNonDefaultParameterValues`, `CreateNonDefaultParameterCache`,
  `CreateParameterIdForDevice`, `FindComObjectInstance`,
  `RebindModuleInstanceIdToDevice`), the com-object flags
  (`ApplyComObjectInfoElement`, `ParseDatapointTypeIds`) and the IP handling
  (`CreateIpConfig`, `ParseIpConfigAssignments`). `names63-staged-v114.xml` =
  `E62F0D37FCC328827E3BD4F543C29FB576F2224AF51BA7B2AABD1FC2023F3D49`, 10,871
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v114-sdkfrozen.xml`
  (`CA83C9E9FD3E852C…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 4.7 s (0 errors, 528/528
  load); every renamed helper still binds from its caller (`CreateValidators`,
  `SpecializedExecute`, `SetParameterAndComObjectInfosForModularApplications`,
  `TransferParametersAndFlags`, `DetermineSecurityImpacts`, the constructor and
  the `SpecializedValidate` closure).
- **Wave 115: adding a device and linking a device to a segment.** 26 rows in
  `Knx.Ets.ObjectModel.dll`: `Operations.Devices.AddDeviceOperation` (13 rows)
  gets the progress manager and the transactional remote-product import
  (`CreateProgressManager`, `ImportRemoteProductsWithFailureHandling`,
  `RefreshCatalogOnImportFailure`), the segment-filtered product selection
  (`GetCatalogItemsValidForSegment`, `FindCouplerCatalogItem`), the device
  materialization (`CreateDeviceFromCatalogItem`, `ApplyHardware2ProgramImage`,
  `ResetBusInterfacePasswords`, `ApplyAdditionalAddresses`,
  `SetDeviceBuildingPartAndTrade`, `ToByteAddress`,
  `SynchronizeDeviceChannels`) and the modified marking
  (`MarkCreatedDevicesModified`), and
  `Operations.Devices.LinkDeviceToSegmentOperation` (13 rows) gets the medium
  and RF bookkeeping (`ResetMediumConfigLoadedForDomainAddress`,
  `ResetMediumConfigLoadedForDomainDevices`, `RunFastAckSlotHandlers`), the
  address changes (`ApplyIndividualAddressChange`,
  `ApplyAdditionalAddressChanges`, `SaveAdditionalAddresses`,
  `SetAdditionalAddress`) and the undo/redo handlers
  (`RestoreUnassignedDevices`, `DetachUnassignedDevices`,
  `DetachUnassignedDevicesOnRedo`, `RemoveDeviceFromOldSegment`,
  `AddDeviceToTargetSegment`, `GetTargetSegment`). `names63-staged-v115.xml` =
  `060D74B9876BAC6C34000648CF8C2233DF221A0541C914221CDA32C9F3BE0B49`, 10,897
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v115-sdkfrozen.xml`
  (`54F16D46FC2A6AA2…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 4.8 s (0 errors, 528/528
  load); every renamed helper still binds from its caller (the two
  constructors, both `SpecializedValidate` closures, `SpecializedExecute`,
  `SpecializedUndo`, `SpecializedRedo`, `DetermineSecurityImpacts`,
  `CreateDeviceFromCatalogItem` and `BeforeOpenMarker`).
- **Wave 116: deleting objects and copying a project.** 24 rows in
  `Knx.Ets.ObjectModel.dll`: `Operations.DeleteOperation` (12 rows) gets the
  certificate handling (`SaveDeviceCertificates`, `DetachDeviceCertificates`),
  the location and plug-in bookkeeping (`DirtyDeviceLocations`,
  `NotifyPluginDeletingDevice`), the connector/bus-interface unlinks
  (`RemoveConnectorsFromGroupAddress`, `RemoveConnectorsFromBusInterface`,
  `RemoveBusInterfacesFromGroupAddress` and the redo variant
  `RemoveConnectorsFromGroupAddressOnRedo`) and the collection handlers
  (`RemoveObjectsFromAllDevices`, `RemoveObjectsFromAllDevicesOnRedo`,
  `RestoreObjectsInAllDevices`, `IsObjectMissingFromAllDevices`), and
  `Operations.Projects.CopyProjectOperation` (12 rows) gets the validator
  iterator (`GetValidators`, the `<GetValidators>d__12` state machine whose
  only caller is `Validate`), the copy driver
  (`SaveProjectAndCopy`, `CopyProjectWithTiming`, `RunCopyProjectSteps`,
  `PatchStoresInTransaction`), the store patching helpers
  (`RewriteStoreStream`, `GetNewProjectName`,
  `GetNewProjectNameForStorePatcher`, `GetAreaStore`, `GetUserFileStore`,
  `GetDeviceBinaryDataStore`, `GetAddinDataStore`).
  `names63-staged-v116.xml` =
  `3C9A9410FF29A46D1E62C51A985B1688215389C99AF49A1D28D9AEF520C98A56`, 10,921
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v116-sdkfrozen.xml`
  (`3EAD875ADA46DBB6…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 4.3 s (0 errors, 528/528
  load); every renamed helper still binds from its caller
  (`SpecializedExecute`, `SpecializedUndo`, `SpecializedRedo`, `Execute`,
  `Validate`, `PatchStores` and the two `PatchStores` patch lambdas).
- **Wave 117: the template manager and the device template.** 27 rows in
  `Knx.Ets.ObjectModel.dll`: `Templates.TemplateManager` (14 rows) gets the
  handler and folder plumbing (`OnTemplateAdded`, `OnTemplateDeleted`,
  `OnTemplateCategoryAdded`, `OnTemplateCategoryDeleted`,
  `EnsureTemplateDirectory`), the missing-file cleanup
  (`RemoveTemplatesWithMissingFile`, `RemoveMissingTemplatesOfCategory`), the
  cache import (`CopyTemplatesFromCache`) and the category/template loading
  (`LoadCategories`, `LoadCategoryNodes`, `LoadTemplatesFromDirectory`,
  `LoadTemplate`, `CreateTemplateFromFile`, `WriteCategoryNodes`), and
  `Templates.DeviceTemplate` (13 rows) gets the template data collection
  (`CollectNonDefaultParameterInfo`, `IsGrantedForUseByCustomer`,
  `CreateCatalogItemHash`, `MatchesProductIdentity`, `ExportDeviceData`,
  `CreateTemplateDataReader`, `CreateModuleInstanceList`,
  `CreateDeviceBinaryDataList`, `CreateDeviceNode`) and the info-element
  helpers (`FormatDptIdRefs`, `GetElementType`, `JoinInfoValues`,
  `SplitInfoValues`). `CreateCatalogItemHash` has an empty body and no caller
  anywhere in the 528-assembly tree (checked with a dnlib walk); it is the
  catalog-item counterpart of the already-mapped `CreateDeviceHash`.
  `names63-staged-v117.xml` =
  `73AC9D9C618C5436A8523DC4EA5AD15CD05D4460D42312D84C80AF014A54C48B`, 10,948
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v117-sdkfrozen.xml`
  (`75471ABD9C8DF307…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 4.8 s (0 errors, 528/528
  load); every renamed helper still binds from its caller (the constructor,
  `AddTemplate`, `DeleteTemplate`, `Import`, `Load`, `SaveCategories`,
  `InternalCollectTemplateData`, `CreateTemplateDataReader`,
  `CreateDeviceObjectList`, `GetInfoElements` and `LoadInformation`).
- **Wave 118: the project root object.** 29 rows in
  `Knx.Ets.ObjectModel.dll`'s `Project.Project`: the collection and access
  plumbing (`InitializeCollections`, `OnAfterBind`, `UpdateTagCollection`,
  `ThrowIfNotOpen`, `CheckAccessOrThrow`, `ReportProgress`,
  `ReportActivityProgress`, `DirtyPendingObjects`, `CreateManufacturer`), the
  access-key handling (`UpdateAccessKeyFromResult`, `ApplyAccessKeySettings`,
  `UpdatePasswordCompareHash`), the schema checks (`IsSchemaOutdated`,
  `IsSchemaNewerThanImplemented`, `GetImplementedSchemaVersion`), the close
  counters (`GetDeviceCount`, `GetRoomCount`, `GetFunctionCount`,
  `GetLineCount`, `GetAssignedCertificateCount`,
  `GetUnassignedCertificateCount`, `IsCountableBuildingPart`,
  `IsCertificateAssigned`, `IsCertificateUnassigned`), the persistence chain
  (`PersistProject`, `WriteProjectToStore`, `WriteProjectStores`,
  `RefreshProjectImageFile`) and `GetProjectId`.
  `names63-staged-v118.xml` =
  `7356976DD7F6B7E61FF450A9B506924BB4E476B6D825FF666E7A3349AE40581A`, 10,977
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v118-sdkfrozen.xml`
  (`7E5906BDF9E2DF93…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 4.6 s (0 errors, 528/528
  load); every renamed helper still binds from its caller (the constructors,
  `Init`, `Save`, `WriteTo`, `DoInitialization`, `UpdateAccessKey`,
  `PerformActivityCalculationIfNeeded`, `MarkSchemaUpdateRequired`, the
  `CloseInternal` counters, `set_Tags` and the `OpenInternal` closure).
- **Wave 119: the installation object and restoring a copy as a clone.** 24
  rows in `Knx.Ets.ObjectModel.dll`: `Project.Installation` (12 rows) gets the
  identity and collection setup (`GenerateInstallationId`,
  `InitializeCollections`) and its per-store persistence pairs
  (`PersistGroupRanges`/`WriteGroupRanges`,
  `PersistUnassignedDevices`/`WriteUnassignedDevices`,
  `PersistBuildings`/`WriteBuildings`, `PersistTrades`/`WriteTrades`,
  `PersistSplitInfos`/`WriteSplitInfos`), and
  `Operations.ProjectSync.RestoreCopyAsCloneOperation` (12 rows) gets the
  progress and transaction plumbing (`CreateProgressManager`,
  `PatchStoresInTransaction`), the project registration
  (`AddRestoredProject`), the clone body
  (`CloneProjectStoreContents`, `ExtractProjectArchiveToTempFolder`) and the
  store-patching helpers (`RewriteStoreStream`, `GetNewProjectName`,
  `GetNewProjectNameForStorePatcher`, `GetAreaStore`, `GetUserFileStore`,
  `GetDeviceBinaryDataStore`, `GetAddinDataStore`). The store helpers carry
  the same names as their `CopyProjectOperation` peers from wave 116 because
  they are declared in different types. `names63-staged-v119.xml` =
  `3E006CD5F5FE330916293DE2E822AC64B85CA894A198CEEE72AD22E963E0F2DD`, 11,001
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v119-sdkfrozen.xml`
  (`2C9CBF793C10234A…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 4.7 s (0 errors, 528/528
  load); every renamed helper still binds from its caller (`Installation::WriteTo`,
  `Installation::GenerateId`, the constructor, `SpecializedExecute`,
  `CloneProjectStore`, `CloneProjectStoreContents`, both `PatchStores` methods
  and the four `PatchStores` patch lambdas).
- **Wave 120: exporting a keyring and patching topology addresses.** 22 rows in
  `Knx.Ets.ObjectModel.dll`: `Operations.KeyringExport.ExportKeyringOperation`
  (11 rows) gets the collected inputs (`CollectUserIds`,
  `CollectSecureDeviceInformation`, `CollectInterfaces`,
  `CollectRelatedGroupAddresses`, `GetIndividualAddress`,
  `IsSecureInterface`, `ToSecureString`), the document work
  (`CreateKeyringDocument`, `AddGroupAddressElements`, `SignAndSaveKeyring`) and
  the export body `ExportKeyring` (which logs
  `"Failed exporting keyring for bus interfaces: {0}"`), and
  `Operations.ExtendedCopy.Patcher.TopologyAddressesPatcher` (11 rows) gets the
  element dispatch and walk (`CalculateAddressesForElement`,
  `CalculateAddressesForChildElements` already mapped,
  `CreateAdditionalAddressStrategy`, `ResetAddressZeroFlag`,
  `IndexAddressElements`), the device passing (`PatchDeviceElements`,
  `PatchDeviceAddresses`, `IsAddressAlreadyUsed`) and the address element
  writers (`PatchAddressElement`, `PatchChildElements`, `CreateAddressElement`,
  `AddAddressElementAttributes`). `names63-staged-v120.xml` =
  `83DB7DCBDAD57329047490602EADABA0DAC2DD83299CAD80634263960EAEB663`, 11,023
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v120-sdkfrozen.xml`
  (`5E9756556FE01F6C…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 4.6 s (0 errors, 528/528
  load); every renamed helper still binds from its caller
  (`SpecializedExecute`, `AddInterface`, `AddDeviceElements`, the constructor,
  `Patch`, `CalculateAddressesForElement`,
  `CalculateAddressesForChildElements`, `CalculateAddressesForLineElements`
  and the `BusInterfaceInfo` accessor).
- **Wave 121: the store update base and the channel instance.** 21 rows in
  `Knx.Ets.ObjectModel.dll`: `Operations.StoreUpdate.UpdateStoreOperationBase`
  (11 rows) gets the conversion driver (`ConvertStoreContainer`,
  `ReportConversionStep`, `ShowNewStep`, `GetConversionStepCaption`,
  `CreateProgressManager`), the file handling (`CopyStoreFiles`,
  `ResetTempFolders`, `BackupStoreToTransactionRoot`) and the store
  post-processing (`CreateStoreInfoDuringSchemaUpdate`,
  `RebuildManufacturerCaches`, `ApplyMasterHashes`), and
  `Project.ChannelInstance` (10 rows) gets the constructor callbacks
  (`CheckNameArgument`, `RegisterTextParameterRef`, `MatchesChannel`), the
  rename and notification path (`SetRenameText`, `NotifyNameChanged`,
  `GetChannelText`), the reference collections
  (`CreateGroupAddressRefCollection`, `CreateFunctionRefCollection`) and the
  usage handling (`OnUsageChannelPropertyChanged`,
  `UpdateDeviceUsageVersion`). `names63-staged-v121.xml` =
  `ED9F1632B2C8457617E8B9630BD052E682DBD0AA7FE2C5CCD1F1F5263CB4E761`, 11,044
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v121-sdkfrozen.xml`
  (`79EB652BE2FE3865…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 4.5 s (0 errors, 528/528
  load); every renamed helper still binds from its caller
  (`SpecializedExecute`, `BeforeExecute`, `AfterExecute`, the constructor,
  `UpdateRename`, `DeactivateRename`, `ClearRenames`, `UpdateGroupAddresses`,
  `UpdateFunctions`, `get_Name`/`get_DisplayName`/`ToString`,
  `TextParameterOnTextChanged` and the `UsageChannel` setters).
- **Wave 122: the coupler validator.** 15 rows in
  `Knx.Ets.ObjectModel.dll`'s
  `Operations.Validators.CouplerValidator`: the resolution helpers
  (`GetHardware2ProgramInfo`, `FindHardwareInfo`,
  `FindApplicationProgramInfo`, `HasHardwareInfo`), the placement checks
  (`DetermineCouplingDirection`, `ValidateCoupling`, `ValidateIpCoupler`,
  `IsCouplerHardware`, `IsOtherWorldCoupler`) and the medium-type selectors
  (`IsSupportedMediumType`, `IsNeededUpperLine`,
  `IsNeededUpperLineForNonSegmentCoupler`, `IsNeededUpperLineOnSubLine`,
  `IsNeededUpperLineForSubLineCoupler`, `IsNeededUpperLineOnMainLine`). The five
  "needed upper line" selectors share one body (`mediumType.Id ==
  Coupler.NeededUpperLine`) and are distinguished by their call site: the
  coupling-direction helper, the non-segment coupler branch, the sub line check
  (twice) and the main line check. `names63-staged-v122.xml` =
  `77EF0B7F26421EDF03D597C22F8D51CCBB2A0A460177DFFBA37EF0011C258CAB`, 11,059
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v122-sdkfrozen.xml`
  (`7BB9956A3340EBD6…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 4.8 s (0 errors, 528/528
  load); every renamed helper still binds from its caller (`Validate`,
  `get_HardwareInfo`, `get_ApplicationProgramInfo`, `DetermineCouplingDirection`,
  `CheckSubLine`, `CheckMainline` and the constructor).
- **Wave 123: the group address conflict rule.** 13 rows in
  `Knx.Ets.ObjectModel.dll`'s
  `Operations.SplitAndMerge.MergeRules.GroupAddressConflictRule`: the
  conflicting-range creators the constructor installs
  (`GetOrCreateConflictingGroupRange`, `CreateMiddleGroupForConflict`,
  `CreateMainGroupForConflict`), the classification
  (`ClassifyGroupAddressesByTargetRange`, `AddGroupAddressToRange`,
  `HandleGroupAddressPropertyMismatches`), the copy path
  (`ResolveRangeConflicts`, `ResolveTargetGroupRange`,
  `CopyMissingGroupAddressesIntoRange`, `CreateGroupAddressesForRange`,
  `HandleCopiedGroupAddress`, `HandleCopiedGroupAddressForRange`) and the
  failure report `ReportUncopiedGroupAddresses` (which logs
  `"GroupAddressCannotBeCopiedNoMoreFreeAddresses"`).
  `names63-staged-v123.xml` =
  `BCDCC9EF0DD4F1EFDFB9B1BBE7171913C183CB69021633B71099691D7FB47EFB`, 11,072
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v123-sdkfrozen.xml`
  (`7C23FDE34F5692BE…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 4.4 s (0 errors, 528/528
  load); every renamed helper still binds from its caller (the constructor,
  `Apply`, `ResolveRangeConflicts`,
  `CopyMissingGroupAddressesIntoRange` and
  `ClassifyGroupAddressesByTargetRange`).
- **Wave 124: unlinking the addresses a delete removes.** 20 rows in
  `Knx.Ets.ObjectModel.dll`, ten in
  `Operations.GroupRanges.DeleteGroupRangeOperation` and ten in
  `Operations.GroupAddress.DeleteGroupAddressOperation` (different namespaces,
  so the shared names are legal): the unlink drivers the execute/undo/redo
  wrappers install (`InvokeGroupAddressUnlink`, `InvokeBusInterfaceUnlink`,
  `ExecuteUnlinkWithUndoDisabled`, `ExecuteBusInterfaceUnlinkWithUndoDisabled`,
  `UndoUnlinkWithUndoDisabled`, `UndoBusInterfaceUnlinkWithUndoDisabled`,
  `RedoUnlinkWithUndoDisabled`, `RedoBusInterfaceUnlinkWithUndoDisabled`) and
  the recent-address bookkeeping — `RemoveFromRecentGroupAddresses` and
  `GetRecordedGroupAddresses` on the group-range delete,
  `RemoveSourceAddressesFromRecent` and `AddSourceAddressesToRecent` on the
  group-address delete. `names63-staged-v124.xml` =
  `E8F47FC08023C15193994ACC014B8B925D5443BA673D3D8843159852973C9809`, 11,092
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v124-sdkfrozen.xml`
  (`39C0E578372E8A48…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 4.8 s (0 errors, 528/528
  load); the unlink drivers and the bookkeeping helpers still bind from
  `BeforeSpecializedExecute`/`AfterSpecializedUndo`/`AfterSpecializedRedo` and
  from both types' `Execute`/`Undo`/`Redo` wrappers.
- **Wave 125: the device calculator and the room address strategy.** 20 rows in
  `Knx.Ets.ObjectModel.dll`. `Project.DeviceCalculator` (10 rows) gets the
  calculator lifecycle (`AttachCalculators`, `DetachCalculators`), the three
  callbacks it subscribes (`OnActivityCalculationFinished`,
  `OnTextParameterRefChanged`, `MatchesComObjectInactivityFilter`), the two
  halves of the `GetParameterInstanceFacadeByRefId` predicate
  (`MatchesModuleInstanceId`, `MatchesSubModuleScope`), the lazy entry point
  `EnsureParameterInstances` and the module registry pair
  (`RegisterModuleInstance`, `UnregisterModuleInstance`).
  `Operations.Strategies.CreateNewInThisRoomAddressStrategy` (10 rows) gets the
  range assignment behind `TargetRange` (`AssignTargetRange`), the four
  creators (`CreateThreeLevelMiddleGroup`, `CreateThreeLevelMainGroup`,
  `CreateFreeGroupRange`, `CreateTwoLevelMainGroup`) and the five free-address
  predicates — four of them share one body and are distinguished by their call
  site, like the wave-122 coupler selectors: `IsUnusedRangeWithFreeAddresses`
  (the final fallback of `Initialize`), `IsUnusedLeafRangeWithFreeAddresses`
  (its leaf-only fallback), `IsUnusedChildRangeWithFreeAddresses`
  (`FallBackForThreeLevelGroupStructure`) and the two
  `SearchNextAvailableRange` fallbacks
  (`IsUnusedRangeWithFreeAddressesForTwoLevelStyle`,
  `IsUnusedRangeWithFreeAddressesForFreeStyle`). `names63-staged-v125.xml` =
  `5D3EB2A4E1DC93039BB59050F89AA4D521E8B8DDA275C62BFC682FA0505AE983`, 11,112
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v125-sdkfrozen.xml`
  (`C752CB6417ECA54E…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 4.7 s (0 errors, 528/528
  load); every renamed helper still binds — `AttachCalculators` from the
  constructor, `DetachCalculators` from `Finalize`, the predicate halves from
  `<GetParameterInstanceFacadeByRefId>b__0`, `EnsureParameterInstances` from
  `GetActiveChannels` and the three tree getters,
  `RegisterModuleInstance`/`UnregisterModuleInstance` from
  `InstantiateModule`/`UninstantiateModule`, and the strategy's creators and
  predicates from `Initialize`, `FallBackForThreeLevelGroupStructure` and
  `SearchNextAvailableRange`.
- **Wave 126: the RF ack-slot copy validator and the paste-special resolver.**
  20 rows in `Knx.Ets.ObjectModel.dll`.
  `Operations.RfMulti.FreeFastAckSlotCopyValidator` (10 rows) gets the two
  validation helpers (`FilterToValidatedDevices`, `ValidateAckSlotCapacity` —
  the 63-slot limit), the other-project slot collection
  (`CollectExistingAckSlotsForOtherProject`), the sharing rule
  (`CanShareFastAckSlots`) and five device/bus-interface predicates — two
  identical pairs told apart by their call site (`IsAddressedValidatedDevice`
  and `IsAddressedValidatedDeviceForNewAddresses`,
  `IsBusInterfaceOnAddressedValidatedDevice` and
  `IsBusInterfaceOnAddressedValidatedDeviceForNewAddresses`) plus
  `IsValidatedDevice` and `IsForeignDevice`.
  `Operations.PasteSpecial.GroupAddressConflictsAcrossInstallationResolver`
  (10 rows) gets the copy pipeline of `Apply`
  (`SelectRangeCreator`, `FindTargetAndConflictingRange`,
  `CopyIntoRangeAtSourceAddress`, `EnsureCapacityAndCopyIntoRange`,
  `ExecuteCopyIntoRange`), the three style-specific range creators
  (`CreateTwoLevelRangeForCopy`, `CreateThreeLevelMiddleGroupForCopy`,
  `ResolveWithFreeGroupRangeForCopy`) and the two range/address comparisons
  (`HasSameAddressRangeAsSource`, `HasSameAddressAsSource`).
  `names63-staged-v126.xml` =
  `F82CB56013465D28AEC33A534F589AFF38AB1E15A5D5FDD6568E349E11B48D62`, 11,132
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v126-sdkfrozen.xml`
  (`387777DF6B118590…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 4.7 s (0 errors, 528/528
  load); every renamed helper still binds — the filter, capacity check and
  collection from `ValidateSameProject`/`ValidateOtherProject`, the sharing
  rule from `CollectExistingAckSlotsForOtherProject`, the predicates from
  `FilterToValidatedDevices`, `GetConnectedDevices` and
  `ConnectedDevicesForNewGroupAddresses`, and the resolver's pipeline from
  `Apply`, `SelectRangeCreator` and `FindTargetAndConflictingRange`.
- **Wave 127: adding a device by product/hardware/program and the add-in data
  merger.** 20 rows in `Knx.Ets.ObjectModel.dll`.
  `Operations.Devices.AddDeviceWithProductAndHardwareToProgramOperation`
  (10 rows) gets the constructor's helpers (`CreateProgressManager`,
  `SetOperationDescription`), the validate steps (`RunProductImporter`,
  `CollectValidators`), the security-impact guard
  (`NeedsCouplerSecurityImpacts`), the execute helpers (`MarkDevicesModified`,
  `ApplyHardware2ProgramImage`, `AssignAdditionalAddresses`,
  `ToNullableByteAddress`, `CalculateInitialActivity`).
  `Import.AdditionalProjectDataMerger` (10 rows) gets the three element
  handlers (`WriteAddinDataIntoStore`, `GetAddinDataFromStore`,
  `CloneUserFilesToWriter`), the two id-mapping actions (`MapAddinDataId`,
  `MapUserFileId`) and the five attribute callbacks (`PatchIdAttribute`,
  `PatchRefIdAttribute`, `RewriteNameAttribute`, `WriteProjectPasswordValue`,
  `WriteFdskValue`) — the two patch names match the sibling
  `InstallationMerger`/`ProjectMerger` callbacks. `names63-staged-v127.xml` =
  `A20BEDCA2E0F39D9F34A96A9C8EC8EC5CC8FD558B54647D3C380ABE86B469422`, 11,152
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v127-sdkfrozen.xml`
  (`6BCF41AF7895669B…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 4.9 s (0 errors, 528/528
  load); every renamed helper still binds — the constructor steps,
  `<SpecializedValidate>b__0`, `DetermineSecurityImpacts`, `SpecializedExecute`
  (including `AddDeviceOperation::CreateDeviceFromCatalogItem` for
  `ApplyHardware2ProgramImage`), `CreateDeviceInstance`, and the merger's
  `get_ElementSettings`/`get_AddinDataSettings`/`get_UserFileSettings`/
  `get_AttributeCallbacks`.
- **Wave 128: the additional-info XML patcher and the parameter instance.**
  19 rows in `Knx.Ets.ObjectModel.dll`.
  `Operations.ExtendedCopy.Patcher.AddAdditionalInfoToXmlPatcher` (10 rows)
  gets the three behavior handlers `Patch` dispatches to
  (`ApplyConnectorAndFunctionBehavior`, `ApplyConnectorBehavior`,
  `ApplySingleArgumentBehavior`), the behavior writers
  (`SetBehaviorAttribute`, `SetBehaviorOnGroupRange`, `ApplyGroupAddressBehavior`
  with its `@Central`/`KeepCentral` rule), the guard
  (`SourceBuildingPartHasDevices`), the project comparison
  (`IsSameProjectAsTarget`) and the post-processing
  (`NormalizeKeepBehaviorsInDocument`, `PropagateKeepToParentGroupRanges`).
  `Project.ParameterInstance` (9 rows) gets the value pipeline
  (`ConvertTypedValue` with its converter-exception log and
  `TryConvertTypedValue`, `SetValueFromActivityCalculator`,
  `EvaluateParameterCalculation`), the calculation scope
  (`GetAffectedModuleDefinitionIds`,
  `ExecuteCalculationsForRelevantModules`),
  `ApplyInitialValueWhenActivated`, `RaiseValueChanged` and the
  `IsValidationErrorMessage` predicate. `names63-staged-v128.xml` =
  `AF2918F3D1B4ACC25C1102A777B5FC262B91B34752737FAB339004353F4EB2A8`, 11,171
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v128-sdkfrozen.xml`
  (`7A7AECF82D80CAE4…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 4.7 s (0 errors, 528/528
  load); every renamed helper still binds — the three patcher handlers and the
  post-processing from `Patch`, the writers from those handlers and
  `Patch`, and the parameter pipeline from `set_Value`, `set_IsActive`,
  `PerformParameterCalculation`, `ParameterInstanceFacade::set_Value` and the
  default-value getters.
- **Wave 129: the object-model IoC module and the project exporter.** 18 rows in
  `Knx.Ets.ObjectModel.dll`. `IocModule` (9 rows) gets the registrations `Load`
  and the store registrations drive (`RegisterTemplateManager`,
  `RegisterXmlSerializers`, `ResolveMasterDataFile`, `ResolveMasterIconsFile`,
  `ResolveProductExtensionDataFile`, `GetOrCreateMyProductsPath`) and the
  versioning/signing checks (`InitializeVersioning`,
  `CheckEntryAssemblySigning`, `CheckTypeAssemblySigning`).
  `Import.Exporter` (9 rows) gets the export helpers (`StoreExtraDataFiles`,
  `WriteMasterDataToProductStore`, `WriteKnxProjectHeader`,
  `WriteElementToWriter`), the attribute collectors
  (`CollectApplicationProgramAttribute`, `CollectTypePictureRefIds`) and three
  iterator helpers whose compiler-generated state machines carry their original
  names (`GetDeviceInstanceCallbacks`, `GetProjectSources`,
  `GetInstallationSources`). `names63-staged-v129.xml` =
  `0EBF2559DDA71A0BD0E3D2524FA0438D072E2A4521A4611E1F00CE0B1BA9B0D1`, 11,189
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v129-sdkfrozen.xml`
  (`F009A711F49CAF2A…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 4.9 s (0 errors, 528/528
  load); every renamed helper still binds — `Load`,
  `CollectVersionInformation`'s state machine, the master-data/product-extension
  store registrations, `ExportZipped`/`Export`, `ExportProjectStore`,
  `ExportApplicationPrograms` and
  `CreateTargetXmlWithFilterAndWrite`.
- **Wave 130: the group-range address generator and the extended copy
  operation.** 18 rows in `Knx.Ets.ObjectModel.dll`.
  `Operations.ExtendedCopy.AddressGeneratorForGroupRangeStructure` (9 rows)
  gets the address assignment helpers the already-named `Apply*` methods drive
  (`GetOrCreateAddressStrategy`, `AssignMiddleGroupRangeAddress`,
  `AssignMainGroupRangeAddress`, `AssignFreeGroupRangeAddresses`,
  `SetRangeAttributes`, `GetNumberOfCopy`), the two structure parsers
  (`ParseGroupRangeValues`, `ParseAddressValues`) and the recursive
  `ResetBehaviorToCreate`.
  `Operations.ExtendedCopy.ExtendedCopyOperation` (9 rows) gets the validate
  and prepare steps (`ValidateForConflicts`, `PrepareXmlDocument`), the
  patcher pipeline (`RunPatcherPipeline`, `SetBehaviorAttribute`,
  `SaveXmlDocument`, `SetXmlDocumentFromXDocument`), the cleanup helpers
  (`RemoveEmptyGroupRanges`, `MarkBehaviorsAsLoose`) and
  `SourceBuildingPartHasDevices` (the same guard the XML patcher uses).
  `names63-staged-v130.xml` =
  `D8D1DCDE93B611848D77F34F6D4CF8F38F6E8FA38404E4698060EFB3D1B146DC`, 11,207
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v130-sdkfrozen.xml`
  (`8EA3008C03399E41…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 4.4 s (0 errors, 528/528
  load); every renamed helper still binds — the ten `Apply*` drivers and
  `CreateGroupAddressesInKeepedRanges` for the address generator, and
  `SpecializedValidate`, `GetPreviewXml`, `AddBehaviorToGroupRange`,
  `CleanupGroupAddressStructureXml`, `PerformCleanUpEmpty{Trades,BuildingParts}`
  and `ApplyGroupRangeStrategy` for the operation.
- **Wave 131: the transaction helper and the IP routing backbone security
  operation.** 16 rows in `Knx.Ets.ObjectModel.dll`. `OnTransaction` (8 rows)
  gets the scope factory (`CreateBirdyTransactionScope`, `CreateTransaction`,
  `CreateTransactionScope`, `TryTakeExclusiveTransaction`), the
  `TransactionManager` reflection helper (`SetTransactionManagerField`), the
  queue drain (`FlushQueuedOperations`), `CloseTransaction` and — kept at its
  readable original name — `Do`, which 44 call sites across the module use.
  `Operations.ChangeIpRoutingBackboneSecurityOperation` (8 rows) gets
  `CollectValidators`, the backbone-key handling (`UpdateBackboneKey`,
  `ShouldHaveBackboneKey`, `HasBackboneKey`), the confirmation pair
  (`ConfirmChange`, `ConfirmChangeForUnprotectedProject`) and the device work
  (`ParkFilteredIpDevices`, `IsAffectedBySecurityChange`).
  `names63-staged-v131.xml` =
  `6C963416EEAE4C6240D62460CD0C05B2EE835D8796C61EC75A884C25415E3A36`, 11,223
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v131-sdkfrozen.xml`
  (`3A5C96DF57AD6A84…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 4.6 s (0 errors, 528/528
  load); every renamed helper still binds — `CreateDefault`,
  `CreateTransactionAndAddItem`, `Do`, `TryCreateExclusive`,
  `QueueScope::Dispose`, `BirdyTransactionScope::Dispose`, and
  `SpecializedValidate`/`SpecializedExecute` for the security operation.
- **Wave 132: the shrink-project operation and the additional group addresses
  operation.** 16 rows in `Knx.Ets.ObjectModel.dll`.
  `Operations.Projects.ShrinkProjectOperation` (8 rows) gets the validator
  iterator (`GetValidators`), the progress pipeline
  (`CreateProgressManager`, called by `BeforeExecute`), the four deletion
  helpers (`DeleteCatalogItems`, `DeleteUnreferencedHardware`,
  `DeleteApplicationPrograms`, `DeleteManufacturerData`, called by
  `SpecializedExecute`), the manufacturer-folder cleanup
  (`DeleteManufacturerFolder`) and the referenced-baggage collector
  (`CollectReferencedBaggages`, called by `BeforeExecute`).
  `Operations.Line.AddAdditionalGroupAddressesOperation` (8 rows) gets the
  execute/undo actions the three constructors install
  (`AddAddressesToSegment`, `RemoveAddressesFromSegment`,
  `AddAddressRangeToSegment`, `RemoveAddressRangeFromSegment`), the three
  validators (`ValidateSegment`, `ValidateAddressRange`,
  `ValidateAddressRangeWithOptionalEnd`) and
  `InvalidateCouplerCommunicationPart` (called by `SpecializedExecute`,
  `SpecializedRedo` and `SpecializedUndo`).
  `names63-staged-v132.xml` =
  `4460F15817A85A234DD29A7924514B73FC670D8AAFF4C576E707949EE4C20081`, 11,239
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v132-sdkfrozen.xml`
  (`7D901A023ACF6D14…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 6.3 s (0 errors, 528/528
  load); every renamed helper still binds — `SpecializedValidate`,
  `BeforeExecute` and `SpecializedExecute` for the shrink operation, the three
  constructors plus `SpecializedExecute`/`SpecializedRedo`/`SpecializedUndo`
  for the group-address operation.
- **Wave 133: the device-to-segment XML copier and the device-identity
  transfer operation.** 16 rows in `Knx.Ets.ObjectModel.dll`.
  `Operations.ExtendedCopy.CopyDeviceToSegmentExtendedOperation` (8 rows) gets
  the XML plumbing: `GetOrCreateTargetSegmentElement` (creates the Segment
  under the parent Line or Area with Id/Name/Number/MediumTypeRefId/Comment/
  Description), `CreateAttribute`, `CollectUnassignedDeviceElements` (selects
  the `UnassignedDevices/DeviceInstance` nodes and adds the missing `Address`),
  the reparenting pair `MoveNodesToTarget` + `DetachNodes`,
  `SetTargetBehavior`, `ValidateCopiedDevices` (compat mode, secure-table
  limits and the free fast-ack slot validator) and `GetTargetSegment`.
  `Operations.Devices.TransferDeviceIdentityOperation` (8 rows) gets the
  description (`InitializeDescription`), the undo capture/restore pair
  (`CaptureUndoData`, `RestoreUndoData`) and the execute steps
  (`CopySecurityIdentity`, `CopyApplicationProgramIdentity` only when both
  devices share a `Hardware2ProgramId`, `ClearLoadedState`,
  `ResetSourceImagesToCatalog`, `ResetSecurityCredentials`).
  `names63-staged-v133.xml` =
  `F701F3059D861E2DAFBF84CE7CA0CAB0F5FFD06763AFF22064461C78453E1A91`, 11,255
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v133-sdkfrozen.xml`
  (`C8E7EB0FFB57EDDA…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 6.8 s (0 errors, 528/528
  load); every renamed member still binds — `AddTargetElement` calls the five
  XML helpers, `InternalValidation` calls `ValidateCopiedDevices`,
  `CollectSourceDevicesDictionary` calls `GetTargetSegment`, the constructor
  calls `InitializeDescription`, `BeforeExecute` calls `CaptureUndoData`,
  `SpecializedUndo` calls `RestoreUndoData`, and `SpecializedExecute` calls
  the five identity steps.
- **Wave 134: the container-items aggregate and the hardware-merger family.**
  19 rows in `Knx.Ets.ObjectModel.dll`.
  `Project.ContainerItemsAggregateCollection`2` (8 rows) gets the aggregate
  bookkeeping (`GetAggregateIndex`, `GetCollectionCount`, `AddCollectionCount`),
  the subscription plumbing (`Subscribe`, `GetItems`), the two change handlers
  (`OnSubContainerCollectionChanged`, `OnItemsCollectionChanged`) and
  `RaiseCollectionChanged`. `Import.HardwareMerger` (1 row) gets
  `GetHardwareElement`; its `FilterDecorator` (2 rows) gets `MarkAncestorKeys`
  and `IsFiltered`; its `InternalHardwareMerger` (8 rows) gets the container
  factories (`CreateProductsElement`, `CreateHardware2ProgramsElement`), the
  merge callbacks (`MergeHardware`, `MergeProduct`, `MergeHardware2Program`),
  the hash guard (`EnsureSameHash`), `GetHardwareElement` and `GetChildElement`.
  `names63-staged-v134.xml` =
  `3048CFD8389E307A66B126E6940C74B8D7937D4C563B08147F15744DFDAC2CAE`, 11,274
  reviewed edits, 0 errors, `--check-map` PASS, no new auto-suffixes (the same
  51). SDK surface unchanged: export map `names63-staged-v134-sdkfrozen.xml`
  (`4BF1FD32E3A5A6E1…`) audits `sdk-visible=0, sdk-referenced-types=0`. The
  batch check applied it to the 528-assembly tree in 7.3 s (0 errors, 528/528
  load); every renamed member still binds, with `Subscribe`, `AddCollectionCount`
  and `GetItems` now visible at their intra-module call sites too.
- **Batch applier: same-module generic MemberRef operands (de4dotEx
  `b249c6e7`).** dnlib can materialize one MemberRef row twice:
  `GetMemberRefs()` returns the default-context instance while a generic method
  body's `call`/`ldftn` operand carries a context-specific instance, and the
  writer serializes the operand. An implementation-only map therefore renamed
  a generic type's definition while same-module call sites kept the old
  MemberRef name. The applier now walks every method body and updates those
  operand instances. Re-applying waves 132/133 with the fixed applier changed
  17 modules and 963 references, and both verify scripts pass; the extended
  `ApplyMapRegression` builds a `Generic<int>.Original` call whose operand
  instance differs from the table instance and asserts the applied output binds
  `Calculate`.
- **Wave 135: the compiler's own names for generated members (de4dotEx
  `3f10bfbc`).** Dotfuscator renamed the compiler-generated *methods* but left
  the evidence Roslyn emitted in place: a cached lambda still stores into its
  canonical `<>9__N_M` field, a display-class lambda is still taken with
  `ldftn` from its declaring method, and an iterator's finally helper still
  clears the state field and disposes its stored resource.
  `perfprobe/wave135-evidence2.py` reads those edges out of the name graph and
  restores `<Source>b__N_M`, `<Source>b__K` and `<>m__FinallyK`; the declaring
  method's reviewed (or already readable) name supplies `<Source>`. The finally
  numbering is verified against the readable 6.4 copies:
  `Import.Exporter/<GetInstallationSources>d__33` has `<>m__Finally1..7` in the
  same metadata order as the 7 pending 6.3 rows, and
  `TemplateCategory/<get_AggregatedCategories>d__9` has `<>m__Finally1`. The
  map updater, reference-map reader and batch applier now accept those
  compiler patterns for method and field rows (types, parameters and locals
  stay source identifiers), so dnSpy re-renders the shapes instead of showing
  a delegate creation: decompiling HawkNET from the wave-134 tree yields 12
  `=>` occurrences and from the wave-135 tree 89, with no leftover `b__`
  names. `names63-staged-v135.xml` = `B9CB8B07877A4DD5…`, 11,624 reviewed
  edits (350 rows: 222 new rows plus 128 rows earlier waves had left
  unnamed), 0 errors, `--check-map` PASS, no new auto-suffixes (the same 51).
  SDK surface unchanged: export map `names63-staged-v135-sdkfrozen.xml`
  (`02184A4986AF99E5…`) audits `sdk-visible=0, sdk-referenced-types=0`; the raw
  map keeps the same five freeze rows and `--filter-map` removes four. The
  batch apply rewrote 10,150 method names in 528/528 modules with 0 errors, and
  `perfcheck2/verify-wave135b.cs` reloads every output, finds all 350 new
  definitions and reports `stale_references=0` — every `ldftn` and MemberRef
  site was rewritten with the map. 596 lambdas whose declaring method still
  carries an obfuscated name stay for a later wave, as do the member names of
  the remaining user methods in Falcon and HawkNET.
- **The 6.4 tree re-staged from the wave-135 map.** The cross-version scanner
  (`--reference-source-map names63-staged-v135-sdkfrozen.xml`) re-ran over the
  two trees: 557 targets, 492 physical module pairs, 1,096 review candidates
  and 895 skips in 11.5 s wall with the work spread over 7.4 cores. Converting
  the candidates to the target's source map, merging them onto
  `names64-staged-v6.xml` and preflighting produces `names64-staged-v7.xml` =
  `605F70D72849603EDA6051D7848AFF8C5DB24D89C62AFA5F4AE9417E9DC68E01` (2,925
  rows: 613 names the 6.4 tree did not have, plus 69 rows whose earlier
  collision suffix — `ExtractParentId2`, `Deserialize2`, `GetImage3` — became
  the clean name), 1,096 edits, 0 errors, `--check-map` PASS. The 6.4 SDK gate
  is clean on both maps (`renamed=2,925, visible=323, sdk-visible=0,
  sdk-referenced-types=0`; `--filter-map` removes nothing), and `--apply-map`
  rewrote 1,583 methods, 53 types, 1,289 fields and 266 parameters in all 553
  modules with 0 errors in 7.2 s. `perfcheck2/verify64-v7.cs` reloads every
  output (553/553) and finds all map names, and the applied ConverterEngine
  decompiles with the transferred names (`FindManufacturerLanguage`,
  `CompareCultures`, `LogMessageToFile`, `DecodeAndIntern`). Artifacts:
  `cross-version64-v135.json`, `map-update64.json`,
  `rename64-staged-v7-check.json`, `public-api-audit64.json`; `progress.json`
  now records the v7 map and its export audit.
- **Wave 136: the constructor- and explicit-implementation-declared lambdas.**
  Wave 135 stopped at the 409 lambdas whose declaring method carried an
  obfuscated name. Two groups are still fully determined by Roslyn's own
  scheme: a lambda declared in a constructor is `<.ctor>b__N_M` /
  `<.cctor>b__N_M`, and a lambda declared in an explicit interface
  implementation uses the last segment of the qualified name
  (`<MoveNext>b__N_M`). The readable 6.4/compat graphs confirm both shapes
  (1,637 `<.ctor>b__…` and 316 `<.cctor>b__…` methods there). Extending the
  wave-135 evidence rule produced 123 more proposals; 119 were new rows (four
  were already named by earlier waves with plain identifiers). The wave is
  mostly the 52 cached lambdas of HawkNET's `en::.cctor` and the constructor
  lambdas of Falcon's `Class1462`, `Class311`, `Class402` and the
  `IAsyncStateMachine.MoveNext` implementers. `names63-staged-v136.xml` =
  `6DE8387635FE68AA52536D60EE0DF63C9F1CE4013E55ED418CDEE6C92D964A0A`, 11,743
  reviewed edits, 0 errors, `--check-map` PASS, the same 51 auto-suffixes; the
  export map `EAA3B96096017614…` audits `sdk-visible=0, sdk-referenced-types=0`
  (raw map keeps the same five freeze rows / four removed). The batch apply
  renamed 10,269 methods in 528/528 modules with 0 errors and
  `verify-wave136` reports `stale_references=0`. Decompiling HawkNET gives 89
  `=>` on the wave-135 tree and 137 on the wave-136 tree with no leftover
  `b__` names. 214 lambdas stay deferred — their declaring methods are still
  obfuscated user methods (`Class1462::a`, `Class311::a`, …).
- **Wave 137: the IoT JSON template analysis cluster (Falcon).** `Class1462`
  is `Knx.Falcon.…Json.Analysis.IoTJsonAnalyzer` and `Class1461` its result
  type; the released 6.4 build keeps the readable names, so the rows transfer
  one to one. The result type gets its six backing fields
  (`usedTemplate`, `originalJsonPayload`, `analysisWasSuccessful`,
  `failureInfoData`, `exception`, `analysisResult`), their six accessors
  (`get_UsedTemplate`, `get_OriginalJsonPayload`, `get_AnalysisWasSuccessful`,
  `get_FailureInfoData`, `get_ExceptionDuringParsing`, `get_AnalysisResult`)
  and the two factories (`FromFailure`, `FromInvalidJson`); the analyzer gets
  `jsonTemplates`, `get_JsonTemplates`, `Analyze`, `TryAnalyze` — and with
  `TryAnalyze` named, the 15 cached lambdas it declares become
  `<TryAnalyze>b__5_0..14` (the canonical `<>9__5_M` fields supply the index).
  `0x06002399` (the indexer accessor that would be `get_Item`) stays blocked by
  the accessor/operator guard because no property row was left behind.
  `names63-staged-v137.xml` = `2939E5707FC8962140859C9D75ABFA7B7A184C0B09FBD5E9AF78AC347894F5A4`,
  11,774 reviewed edits (31 rows), 0 errors, `--check-map` PASS; the export map
  `AB0F06A612921C99…` audits `sdk-visible=0, sdk-referenced-types=0` (raw map
  keeps the same five freeze rows / four removed). The batch apply rewrote
  10,293 methods and 1,266 fields in 528/528 modules with 0 errors in 6.6 s,
  and `verify-map.cs` reports `canonical_rows=484 definitions_missing=0
  stale_references=0`.
- **Wave 138: HawkNET's capability load-control insertion.**
  `Class311::a(HawkDataProvider)` — whose only caller is the reviewed `Apply`
  of `BasicLoadProcedureTask` — inserts the load controls the coupler
  capabilities require: every branch is gated by
  `Enumerable.Any(couplerCapabilities, predicate)` and ends in the procedure's
  insert-control call, patching `Occurrence` and `AppliesTo` on the way. It is
  named `InsertCapabilityLoadControls`, and the eight cached lambdas it
  declares become `<InsertCapabilityLoadControls>b__5_0..4, 8..10` from their
  canonical `<>9__5_M` fields. `names63-staged-v138.xml` =
  `6177E8F6D6086445965E6D1570C6F61E83A669ED9095C7B1BAF2D6B2EB8FBBAA`, 11,783
  reviewed edits (9 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `E3038831329BA01930C93DBA9D50DCC1A23B9A254C95E94FB0EF10EDD71E6AB6`
  audits `sdk-visible=0, sdk-referenced-types=0`. The batch apply rewrote
  10,302 methods in 528/528 modules with 0 errors in 6.3 s, and `verify-map.cs`
  reports `canonical_rows=492 definitions_missing=0 stale_references=0`.
  Reusable tooling added: `perfcheck3/wave-pipeline.ps1 -Wave <n> -ApplyRoot
  <dir>` (update, check, audit, filter, apply, hashes) and
  `application-name-pass01/checkpoint-wave.py <n>`.
- **Wave 139: lambdas declared in explicit interface implementations.**
  Roslyn names a lambda after its declaring method, and when that method is an
  explicit interface implementation the `<Source>` part is the *qualified*
  name — the readable graph carries 31 such rows, e.g.
  `<Knx.Ets.ObjectModel.Project.IInternalDevice.SetAddressWithoutUndo>b__0`.
  Two deferred declarers are exactly that shape and stay blocked themselves
  (the accessor/operator guard owns them), but their cached closure lambdas are
  ordinary methods: HawkNET `Class494/b::b` implements
  `System.Collections.IEnumerator.MoveNext`, so its four lambdas become
  `<System.Collections.IEnumerator.MoveNext>b__22_0, 3, 4, 5`, and Falcon
  `Class1364/Struct965::e` implements
  `System.Runtime.CompilerServices.IAsyncStateMachine.MoveNext`, so its four
  become `<System.Runtime.CompilerServices.IAsyncStateMachine.MoveNext>b__5_2,
  3, 5, 6`. `names63-staged-v139.xml` =
  `41212AC047D1AA297C311234DDABC36BFC99B5B9751EE16F041955CF2FCE7C70`, 11,791
  reviewed edits (8 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `4ACAD4E9457AE039CFB85A50946A571268B1BF578B8B29001AB2F67FA15CC31B`
  audits `sdk-visible=0, sdk-referenced-types=0`. The batch apply rewrote
  10,310 methods in 528/528 modules with 0 errors in 6.6 s, and `verify-map.cs`
  reports `canonical_rows=500 definitions_missing=0 stale_references=0`.
- **Wave 140: HawkNET's ex-factory image fill.** `Class402::a(Image, byte[],
  ref byte[], uint, uint)` — `Class402` is `Knx.Ets.Hawk.Impl.LoadControlContext`
  — is called from the async image optimisation: it builds an
  `Enumerable.Repeat(0xFF)` fill buffer, walks the image segments, copies
  ex-factory bytes over the areas that are still erased and logs "`{0} filled
  {1} bytes in holes`", "`{0} filled {1} bytes in partial properties`",
  "`{0} filled {1} partial bytes`" and "No ex-factory data for {0}". Its four
  cached lambdas are the byte predicates (`value != 0xFF`, `value > 0` twice,
  `value == 0`), and the released counterpart type carries
  `OptimizeImageForExFactoryDataAsync`. Named
  `FillMissingImageBytesFromExFactory`, so the lambdas become
  `<FillMissingImageBytesFromExFactory>b__54_2..5`.
  `names63-staged-v140.xml` =
  `525A8E20CB0604B939851EC1584CAB19C8C5064D46D3BCE784E3428F75784F41`, 11,796
  reviewed edits (5 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `EB42E64921B75002…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,315 methods in 528/528 modules with 0 errors in
  6.9 s and `verify-map.cs` reports `canonical_rows=504 definitions_missing=0
  stale_references=0`.
- **Wave 141: HawkNET `ReadDeviceTask.GetProcedure`.** `fv::a(fe)` returns
  `Knx.Ets.Hawk.Impl.LoadProcedure` (the mapped `go`), and the released
  `ReadDeviceTask` counterpart declares `GetProcedure` in the same position
  between `PerformTaskAsync` and `PerformIoTTaskAsync`; the graph records no
  callers because it is reached through a delegate. Named `GetProcedure`, so
  its four cached lambdas become `<GetProcedure>b__5_0..3`.
  `names63-staged-v141.xml` =
  `148415E3CFF45397DF46A545CCD6F81D4B03D7E03BB7CCA7EF9CD5CD3CE00B78`, 11,801
  reviewed edits (5 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `AA316008126FA1C4…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,320 methods in 528/528 modules with 0 errors in
  6.2 s and `verify-map.cs` reports `canonical_rows=508 definitions_missing=0
  stale_references=0`.
- **Wave 142: every remaining lambda of a blocked explicit implementation.**
  Twenty of the deferred declarers are explicit interface implementations and
  stay blocked themselves, but each one's MethodImpl target gives the
  qualified name Roslyn used for its lambdas. `probe-overrides.cs` shows all
  twenty implement either `System.Runtime.CompilerServices.IAsyncStateMachine.MoveNext`
  (18) or `System.Collections.IEnumerator.MoveNext` (2 — HawkNET
  `Class345/Class351::c`, Falcon `m8/a::d`), so their 28 cached lambdas take
  those qualified names. `names63-staged-v142.xml` =
  `667AFD222B691B6B74A79E00811839E8B1BC7BBEF212540118E1F03F13F59E6E`, 11,829
  reviewed edits (28 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `42F8DB0A1813E44A…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,348 methods in 528/528 modules with 0 errors in
  6.2 s and `verify-map.cs` reports `canonical_rows=536 definitions_missing=0
  stale_references=0`.
- **Wave 143: HawkNET `Class501::a(ly[])`.** The body is
  `ly[].Where(predicate).SelectMany(x => lv[]).Select(x => GroupAddress).Distinct()`,
  i.e. it collects the distinct group addresses reachable from the supplied
  items; named `GetDistinctGroupAddresses`, which also names its three cached
  lambdas `<GetDistinctGroupAddresses>b__0_0..2`.
  `names63-staged-v143.xml` =
  `F58967D639A8DFBFB64A7BD50339F3C2CA667F88876A287F987D783D9596546E`, 11,833
  reviewed edits (4 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `F7FF45803B804D24…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,352 methods in 528/528 modules with 0 errors in
  7.3 s and `verify-map.cs` reports `canonical_rows=539 definitions_missing=0
  stale_references=0`.
- **Wave 144: HawkNET `Class511::a(IEnumerable<lx>)`.** The body is
  `items.Where(x => x != null && x.SecureLinks != null)`
  `.SelectMany(x => x.SecureLinks)` (element type
  `Knx.Ets.Hawk.DataProvider.SecureLink`) `.Distinct(link comparer)`
  `.Select((link, index) => Class511.Factory((uint)index, link))`, so it
  returns the distinct secure links of the supplied items each paired with its
  index; the three cached lambdas are the predicate, the array selector and the
  indexed projection. Named `GetDistinctSecureLinks` →
  `<GetDistinctSecureLinks>b__3_0..2`. `names63-staged-v144.xml` =
  `277C91FB9856B3E0C43F7CB273C003B6E24C8F6E0B509A8C274B054E2BB407A6`, 11,837
  reviewed edits (4 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `4A596BAC90373D9F…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,356 methods in 528/528 modules with 0 errors in
  6.2 s and `verify-map.cs` reports `canonical_rows=542 definitions_missing=0
  stale_references=0`.
- **Wave 145: HawkNET `CompareDeviceTask` address-space resolution.**
  `eh::a(eo device, gi image, ResourceName resource, ResourceName
  fallbackResource, go procedure)` resolves the `Class430` resource for the
  first name and returns its address space (`fx` =
  `Knx.Ets.Hawk.AddressSpace`); when that fails it repeats with the fallback
  name and finally looks the segment controls up in the procedure
  (`go::b()` → `OfType<Class365>().FirstOrDefault(predicate)`) and converts the
  segment through `Class299`. Named `ResolveResourceAddressSpace`; the three
  cached `FirstOrDefault` predicates become
  `<ResolveResourceAddressSpace>b__26_0..2`. `names63-staged-v145.xml` =
  `530D53A48F2DA21FEA73ACD7006A75BF992EDB402D0A27C6C6FC6592A1E4381C`, 11,841
  reviewed edits (4 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `5CC508D3492EB2AC…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,360 methods in 528/528 modules with 0 errors in
  6.8 s and `verify-map.cs` reports `canonical_rows=545 definitions_missing=0
  stale_references=0`.
- **Wave 146: HawkNET `Class313::b(CreateImageContext)`.**
  The body returns unless the `InternalLoadDeviceOptions` flags carry bit 2
  without bit 1, finds a load control with the cached predicate, reads the
  image at the fixed address `(9, 0, 52, 0)` and — when there is no data —
  logs "Remove {0} because no data present" and removes the control (the second
  cached lambda is the removal filter). Called only by the reviewed `Apply`.
  Named `RemoveControlsWithoutData`; lambdas
  `<RemoveControlsWithoutData>b__8_0..1`. `names63-staged-v146.xml` =
  `A441D5BED0624D5F44E7BDED2A02FACE8A5D782A38893BBC9068FCCD12D0B9BE`, 11,844
  reviewed edits (3 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `033FB037343BB94E…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,363 methods in 528/528 modules with 0 errors in
  6.4 s and `verify-map.cs` reports `canonical_rows=547 definitions_missing=0
  stale_references=0`.
- **Wave 147: HawkNET tunnelling-user controls.**
  `Class304::a(CreateImageContext, lr, lo)` in
  `AddIpSecurityConfigDataTask` builds the `LdCtrlWriteProp` list for the
  `PID_TUNNELLING_USERS` table: it distincts and orders the tunnelling-user
  `(byte, byte)` entries with the two cached selectors, guards the table size
  ("PID_TUNNELLING_USERS table overflow: required {0} entries, available {1}
  entries") and writes ObjType 11 / PropId 97 controls per entry. Named
  `CreateTunnellingUserControls`; lambdas `<CreateTunnellingUserControls>b__7_0..1`.
  `names63-staged-v147.xml` =
  `D083E8178ED4802ED9A69CE8CB6348965B1938453B87EBBB6FFC9F487E72D01D`, 11,847
  reviewed edits (3 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `8F683CAA64294E70…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,366 methods in 528/528 modules with 0 errors in
  6.6 s and `verify-map.cs` reports `canonical_rows=549 definitions_missing=0
  stale_references=0`.
- **Wave 148: HawkNET `DeviceProfileInformation.MaySupportLongFrames`.**
  `Class345::method_15()` returns true when `Any(additionalProfiles, p =>
  p.MaySupportLongFrames == true)`, true for mask version `0xFFFF`, false when
  the mask version's high nibble is not `0x1000`, otherwise the legacy flag
  getter and finally any configuration resource named 60 — and the released
  `DeviceProfileInformation.get_MaySupportLongFrames` has the identical
  structure, which pins the name. The two cached lambdas are the profile and
  resource predicates: `<get_MaySupportLongFrames>b__40_0..1`.
  `names63-staged-v148.xml` =
  `B428A0845100940F84DD92A2C3867D5F35A5610F42A3EA8AADAFC34EFDB4BD12`, 11,850
  reviewed edits (3 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `49C3A3F30AC9F82D…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,369 methods in 528/528 modules with 0 errors in
  6.0 s and `verify-map.cs` reports `canonical_rows=551 definitions_missing=0
  stale_references=0`.
- **Wave 149: the HawkNET `DeviceProfileInformation` capability cluster.**
  Eleven capability getters of `Knx.Ets.Hawk.Impl.DeviceProfileInformation`
  are pinned by their own bodies and cached predicates and by the identical
  bodies of their released counterparts: `get_SupportsInterfaceObjects`
  (`Any(profiles, p => p.SupportsInterfaceObjects)`), `get_SupportsConfirmedRestart`
  (same list), `get_SupportsMemoryExtendedServices`, `get_SupportsPropertyExtendedServices`,
  `get_MaySupportLongMemoryServices` (long-frame support plus the memory mask
  bits), `get_FirstAppObjectIdx` (feature name 1, Byte),
  `get_HasGroupCommunication` (resource name 11), `get_HasFilterTable`
  (resource name 15), `get_HasSecondaryRouterObject` (version `10528`),
  `get_HasMemoryMappedLoadControls` (configuration feature 11) and
  `get_RestartTime` (feature 6, default 200). Six of their cached predicates
  also become canonical (`<get_SupportsInterfaceObjects>b__32_0`,
  `<get_SupportsConfirmedRestart>b__34_0`, `<get_SupportsMemoryExtendedServices>b__36_0`,
  `<get_SupportsPropertyExtendedServices>b__38_0`,
  `<get_MaySupportLongMemoryServices>b__42_0`, `<get_FirstAppObjectIdx>b__44_0`).
  `names63-staged-v149.xml` =
  `1E026B6E222B166A9B8B5F2BDFCC7AB77872FE90E1F2961F829C82EF296083CB`, 11,867
  reviewed edits (17 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `FF010C13A31BD33D…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,386 methods in 528/528 modules with 0 errors in
  6.5 s and `verify-map.cs` reports `canonical_rows=557 definitions_missing=0
  stale_references=0`.
- **The last serial tree walks (de4dotEx `f4486852`).** Every other
  NameCandidates command already parsed its modules on all cores; the two
  property/field suggestions and the public API audit still walked the whole
  tree on one thread, so they ran at roughly one core from start to finish.
  Both now split their per-module work over `Environment.ProcessorCount`
  threads and merge the rows in file order, the audit fills its resolver cache
  in that same order, and both print `NAMECANDIDATES_TIMING=1` phases.
  6.3 tree (wall / CPU / busy cores): `--suggest-property-fields`
  2.5 s / 2.9 s (1.2) -> 1.2 s / 3.2 s (2.6), `--suggest-field-accessors`
  3.1 s / 4.3 s (1.4) -> 1.6 s / 6.6 s (4.1), `--public-api-audit`
  1.2 s / 0.9 s (0.8) -> 0.9 s / 1.0 s (1.1); the audit lists and loads its
  528 modules in 73 ms. The 553-assembly 6.4 tree behaves the same way, all 18
  report files (9 kinds on both trees) are byte-identical to the previous
  build, and `PublicApiAuditFixture` plus the existing property/field fixtures
  pass in the full fixture suite.
- **The applied-tree gate is a built command (de4dotEx, `--verify-applied`).**
  The post-apply verifier ran as `dotnet run perfcheck2/verify-map.cs`, which
  paid a file-based-app build/package probe per wave (23.1 s cold, 4.8 s warm,
  0.3 s CPU and no reported IO in the CLI parent) and then parsed all 528
  modules on one thread (4.6 s wall / 5.1 s CPU, ~1 core), so a whole wave cost
  ~40 s for ~16 s of work. `NameCandidates --verify-applied <applied-root>
  <map.xml> [expected-canonical-rows]` keeps the same report
  (`loaded=`, `canonical_rows=`, `definitions_missing=`, `stale_references=`,
  `VERIFY PASS/FAIL`) but lists and parses the tree on
  `Environment.ProcessorCount` threads, matches canonical rows by name plus
  applied declaring type and checks stale `MemberRefs` through a leaf index.
  Nested type aliases compose from the outermost alias down, so a renamed
  display class inside a renamed type is matched (the script looked nested
  aliases up under the already-renamed prefix). Wave-149 tree: 23.1 s / 4.8 s
  -> 1.7 s wall at 2.8 busy cores; all wave 137-149 applied trees re-verify
  identically (`definitions_missing=0 stale_references=0`) in 1.3-3.5 s, and
  the whole wave batch (update, check, audits, filter, apply, gate) costs
  18.0 s instead of ~40 s.
  `wave-pipeline.ps1 -ApplyRoot <dir>` now runs the gate after its apply step,
  and `tests/NameCandidates/AppliedVerificationFixture.cs` pins the pass shape,
  the nested-alias composition, a missing definition, a stale reference, an
  unloadable input and the expected-row-count failure.

- **Wave 150: the Falcon `Device` wrapper and its progress-reporting write
  (de4dotEx `--verify-applied` gate).** 6.3 `nc` (`0x0200001B`, base
  `System.Object`, `IDisposable` + `IAsyncDisposable`, 156 methods) is the
  released `Knx.Falcon.Device`: 59 of its members were already mapped to Device
  members (`OpenConnectionAsync`, `NegotiateMaxApduLengthAsync`,
  `Read/WritePropertyValueAsync`, `Read/WriteRouterMemoryAsync`,
  `WriteKeyAsync`, ...), it holds the same
  `Knx.Falcon.Impl.KnxStack.IApplicationLayer` field, and no SDK signature
  mentions `nc`, so the type row is safe for third-party callers. Inside it,
  `0x060000CD` builds the same three cached lambdas and passes the same
  constants 4/11, `get_MemoryVerifyMode()` gate and worker call as the released
  `Knx.Falcon.Device::WriteRouterMemoryAsync(System.UInt32,
  System.ReadOnlyMemory<byte>, System.Boolean, System.IProgress<int>,
  System.Threading.CancellationToken)`, so it takes that overload's name and
  its three cached lambdas become `<WriteRouterMemoryAsync>b__118_0..2`.
  `names63-staged-v150.xml` =
  `C58C5C18B36E3A74778B8D80FF78ECDA19DDA5682A588A5260DC53F6F0CEEE01`, 11,872
  reviewed edits (5 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `35D1F948E3D94A97…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,390 methods in 528/528 modules with 0 errors in
  7.0 s, and the new built gate reports `canonical_rows=560
  definitions_missing=0 stale_references=0` in 3.5 s (the file-based
  `dotnet run` verifier it replaced cost ~21 s for the same report).
- **Wave 151: `DataFacade.FinalizeImage` and the restart load controls.** The
  released `Knx.Ets.Hawk.Impl.DataFacade::FinalizeImage(CreateImageContext)`
  and 6.3 `Class319::a(Class300)` (`0x06000662`) are the same algorithm:
  combine the image's adjacent segments, return unless `RequireRestart`, find
  the last `LoadControlBase` through the same three cached predicates, keep an
  existing `LoadControls.Restart`/`LoadControls.MasterReset`, otherwise read
  `DeviceProfileInformation.get_SupportsConfirmedRestart` (the wave-149
  `Class345::method_12`) and append `Restart` or a `MasterReset` carrying
  `LdCtrlMasterReset.EraseCode = 1`. The method takes `FinalizeImage` and its
  three cached predicates become `<FinalizeImage>b__62_0..2`; the two wrappers
  it keeps are `Knx.Ets.Hawk.Impl.LoadControls.MasterReset` (6.3 `Class391`,
  `Class363<LdCtrlMasterReset>`) and `...LoadControls.Restart` (6.3 `Class395`,
  `Class363<LdCtrlRestart>`), both already carrying a mapped `ExecuteAsync`.
  `names63-staged-v151.xml` =
  `EC02368E1FD122E099CC8826552B6DAD0ECDE5577C6DE081806641E75B8D42E3`, 11,878
  reviewed edits (6 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `D915E4110A69A9DE…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,394 methods and 806 types in 528/528 modules with
  0 errors in 6.5 s, and `--verify-applied` reports `canonical_rows=563
  definitions_missing=0 stale_references=0` in 3.5 s.
- **IlDump now lists types and members** (`IlDump <assembly> --types [filter]`
  and `--members <type-full-name>`). The applier compacts RIDs, so tokens from
  the input tree do not identify the same member in an applied tree; the type
  and member inventories verify an applied map by name and locate the owner of
  a method before dumping its body.
- **Wave 152: the RF multi-tables device-info item.** 6.3 `Class339`
  (`0x0200031D`, base `Class331` = the released `DeviceInfoItem`) carries the
  released `Knx.Ets.Hawk.Impl.DeviceInfoItems.DeviceInfoItemRfMultiTables`
  member list in the same order (`in`/`IncludeItemAsync`,
  `vmethod_0`/`ProcessAsync`, `c`/`method_0`, `b`/`method_1`, `a`/`method_2`,
  `a(BitArray)`/`smethod_2`, `vmethod_1`/`EstimateTimeAsync`, `ToString`), so
  it takes that type name. `Class339::c` (`0x06001017`) is the received 6.4
  `method_0(DeviceInfoOptions, DeviceManagement,
  Dictionary<ResourceName,byte[]>, IDictionary<object,object>, DataFacade,
  XElement, CancellationToken, IProgress<HawkProgressIndication>)` (Void, still
  obfuscated there): it reads the `CommunicationTables` from the cache and
  appends one `<Resource Item="<address>" Value="Rx:… Tx:… Ready Ack#…
  SLE(…) Fast(…)">` element per entry, with the same strings in both builds and
  the `<ProcessMediaCouplerAsync>d__5` state machine as its caller. Named
  `AppendRfMultiTableResources`; its three cached predicates become
  `<AppendRfMultiTableResources>b__4_0,2,3`.
  `names63-staged-v152.xml` =
  `FDD1AACB085C5043BAF363B8B61E2E1E5A4FAC6C23BACD23AF4D93CCDBB51B2E`, 11,883
  reviewed edits (5 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `2310F02931C25356…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,398 methods and 807 types in 528/528 modules with
  0 errors in 6.6 s, and `--verify-applied` reports `canonical_rows=566
  definitions_missing=0 stale_references=0` in 3.5 s.
- **Wave 153: the Falcon master-data provider.** 6.3 `Class703`
  (`0x0200013E`, implements `Interface29`, 26 methods) is the released
  `Knx.Falcon.MasterData.MasterDataProviderFromXml`: four members already
  carried that type's names (`GetKnxMasterData`, `Validate`,
  `UpdateDefaultFromHigherVersion`, `<GetKnxMasterData>b__20_0`), its
  constructors take the released String/FileInfo/Stream/XDocument/empty/
  `IEnumerable<string>` set, and it fills the document version, medium-type
  array and manufacturer dictionary. `Class703::c(XDocument)` (`0x06000659`)
  is the released `method_0(XDocument)` (still obfuscated there) — the private
  loader called by the FileInfo, XDocument and `IEnumerable<string>`
  constructors in both builds — named `LoadFromXDocument`, with its three
  cached selectors becoming `<LoadFromXDocument>b__18_0,2,3`. No SDK row
  mentions `Class703`.
  `names63-staged-v153.xml` =
  `2743157D18B87F81B145D0132C53981C6688079CE936176164DA76C9E20AF3B7`, 11,888
  reviewed edits (5 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `004AC2CC56E9149F…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,402 methods and 808 types in 528/528 modules with
  0 errors in 6.2 s, and `--verify-applied` reports `canonical_rows=569
  definitions_missing=0 stale_references=0` in 3.9 s.
- **Wave 154: the router-memory read overload.** Inside the wave-150
  `Knx.Falcon.Device`, `0x060000C0`
  (`Task<byte[]> (uint, uint, IProgress<int>, CancellationToken)`) is
  body-identical to the released
  `Device::ReadRouterMemoryAsync(uint, uint, IProgress<int>,
  CancellationToken)`: the same two cached lambdas (`<>9__105_0/1` over
  `method_4`/`method_5`), constants 4/11 and the same worker call with the same
  argument order. Its sibling `0x060000BF` (the same method without the
  IProgress parameter) was already mapped to `ReadRouterMemoryAsync`, and the
  released type carries both overloads. Named `ReadRouterMemoryAsync`; its two
  cached selectors become `<ReadRouterMemoryAsync>b__105_0,1`.
  `names63-staged-v154.xml` =
  `6DA1DC9EA37D7AEA1BAE08E869C83014CB0EFCE9039806378342DB60CDA8A45B`, 11,890
  reviewed edits (3 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `807D546D2A34F1F7…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,405 methods in 528/528 modules with 0 errors in
  6.5 s, and `--verify-applied` reports `canonical_rows=571
  definitions_missing=0 stale_references=0` in 3.5 s.
- **Wave 155: the IPv6 candidate lookup behind the Falcon address helper.** The
  `Knx.Falcon.IoT.Stack.Network.Ipv6AddressHelper` type row and its two
  `Select...` overloads were shipped earlier; the deferred lambdas belonged to
  the still-obfuscated candidate lookup. `Class1036::a(Interface41)`
  (`0x060011B2`) is body-identical to the released
  `GetIpv6SourceAddressCandidatesForDestinationEndpoint(
  IIoTSourceIpAddressProvider)` — the same two-stage IPv6 `Where` filters, the
  same `Any` gate, the same cached filters and the same "It is not possible to
  select an source IPv6 address …" exception — and `0x060011B0` is the released
  no-argument overload (new `IoTSourceIpAddressProvider` + delegate). Both take
  that name and the two cached filters become `<…>b__6_0,1`. The applied tree
  now shows all four overloads by name; `Interface41`, the nested display class
  and the three comparison delegates stay open.
  `names63-staged-v155.xml` =
  `AF6CB8075DA00DDA3C1B39E55B1891F224E0077BC67CD39E0E42D1D39B532E81`, 11,895
  reviewed edits (4 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `BD075BAE71AAA65F…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,409 methods in 528/528 modules with 0 errors in
  6.0 s, and `--verify-applied` reports `canonical_rows=573
  definitions_missing=0 stale_references=0` in 3.5 s.
- **Wave 156: the IoT source-address provider interface.** 6.3 `Interface41`
  (`0x020002FE`) is the released
  `Knx.Falcon.IoT.Stack.Network.IIoTSourceIpAddressProvider`: it is the
  parameter type of the wave-155 `Ipv6AddressHelper` methods whose released
  counterparts declare that interface, and its two members match the released
  interface 1:1 (`imethod_0()`/`get_EnableAutomaticSourceAddressSelection()`,
  `imethod_1()`/`GetSourceIpAddresses()`). The applied tree now prints the
  provider overloads as
  `…ForDestinationEndpoint(Knx.Falcon.IoT.Stack.Network.IIoTSourceIpAddressProvider)`.
  The interface *methods* are virtual, so they stay blocked for the
  contract-family flow (`--check-map` rejects an interface method alias with
  "Unsupported method alias", verified on a scratch map).
  `names63-staged-v156.xml` =
  `E96FDAFE0688A9212569FFFF5B8882DF11743B1297E50AA065F0C33A18188D29`, 11,896
  reviewed edits (1 row), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `BD110165741C8280…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 809 types in 528/528 modules with 0 errors in 6.2 s,
  and `--verify-applied` reports `canonical_rows=573 definitions_missing=0
  stale_references=0` in 3.5 s.
- **Wave 157: the Falcon top-score address filter.** The deferred lambdas of
  `Class1036/a::b(IPAddress[], Func<IPAddress,IPAddress,int>)` (`0x060011BF`)
  belong to the helper that the wave-155
  `SelectIpv6SourceAddressForDestinationEndpoint` overload calls once per
  comparer: it scores every candidate (score, address), takes the descending
  first score and returns every address tied with it
  (`Class1036/b::d(ValueTuple)` is literally `Item1 == captured best`). Named
  `SelectHighestScoringAddresses`; the closure methods became `ScoreAddress`
  and `HasHighestScore`, and the two cached projections
  `<SelectHighestScoringAddresses>b__5_6,8`.
  `names63-staged-v157.xml` =
  `94ED61BEF13FDD17B34841ED5208B48A490537007640A0586EB53CE49D532BD2`, 11,901
  reviewed edits (5 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `F3EF637D0326E6A1…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,414 methods in 528/528 modules with 0 errors in
  6.1 s, and `--verify-applied` reports `canonical_rows=575
  definitions_missing=0 stale_references=0` in 3.5 s.
- **Wave 158: the HawkNET `NetworkFacade` and its connection-state getters.**
  6.3 `Class412` (`0x02000182`) is the released
  `Knx.Ets.Hawk.Impl.NetworkFacade`: the member lists line up one-to-one in
  declaration order (52 vs 56 methods), the 19 members shipped by earlier waves
  already carry its names, and every remaining connection-state getter is
  pinned by its own body — `s()`/`get_IsDirectDeviceConnection`
  (`ConnectorType == IpDeviceManagement`), `method_2()`/
  `get_IsLocalUsbConnection` (`!= Usb && Mode == Local`), `q()`/
  `get_IsTunnelingConnection` (`IpTunneling`), `method_4()`/`get_IsRouting`
  (`IpRouting`), `method_5()`/`get_IsCloudConnection` (provider flag),
  `method_6()`/`get_SupportsLocalProgMode`
  (`interfaceFeatures.SupportsLocalProgrammingMode`), `m()`/
  `get_InterfaceSerialNumber` (`interfaceFeatures.SerialNumber`),
  `method_10()`/`get_MaxSupportedGatewayApduLength`
  (`interfaceFeatures.MaxApduLength`) and `d()`/
  `get_OutboundSegmentCouplerAddress` (`provider.dt()`).
  The **type row is SDK-frozen**: `Knx.Ets.Sdk.Network.NetworkManagement`
  exposes `Class412` in a public signature, so the export filter removes the
  type alias (the applied tree keeps `Class412` but carries all nine getter
  names). The raw map now holds **6 freeze rows / 5 removed**; the checkpoint
  asserts the raw SDK-visible count stays 0 and that the raw freeze set keeps at
  least the five previously known rows, and reports the raw shape each wave.
  `names63-staged-v158.xml` =
  `759AED15DF247246780FBBADB35AA0D3C3D557C44C077B72BDEC2A6E6989A285`, 11,911
  reviewed edits (10 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `65211104E835CA36…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,423 methods in 528/528 modules with 0 errors in
  6.7 s, and `--verify-applied` reports `canonical_rows=575
  definitions_missing=0 stale_references=0` in 3.5 s.
- **Wave 159: the compatibility plugin host/installer and the Hawk network
  interface.** Three type rows whose readable 6.4 counterparts the new
  signature-shape scan finds uniquely: 6.3 `Class144` (`Knx.Ets.Compatibility.dll`,
  `0x0200000D`) → `Knx.Ets.Compatibility.PluginHost` (29 shape matches, incl.
  the whole `Sdk*`/`TryGetCachedPluginInformation` cluster),
  `Class158` (`0x02000020`) → `Knx.Ets.Compatibility.PluginInstaller` (12,
  incl. `AnyPluginRequiresElevation`/`InstallEts3Plugins`) and HawkNET `fb`
  (`0x02000080`) → `Knx.Ets.Hawk.IAsyncNetworkAccessProvider` (22; its members
  mirror the already-named `FalconNetworkAccessProvider`). The matched
  `PluginInstaller` plugin methods and every `IPluginHost` implementation member
  are virtual: `--update-map` rejects them with
  `virtual-or-override: use --review-families`, so the wave ships the three type
  rows and leaves those members to the contract-family flow.
  `names63-staged-v159.xml` =
  `FD020834E9084B7EE9B325C0F36CEE0A6E462090D2D7CBD8DEDE705A2CC50B93`, 11,914
  reviewed edits (3 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `E1D999D2B57E2CF2…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 812 types in 528/528 modules with 0 errors in 6.2 s,
  and `--verify-applied` reports `canonical_rows=575 definitions_missing=0
  stale_references=0` in 3.5 s.
- **Wave 160: the contract-family flow, exercised end to end.** The wave-159
  type row named HawkNET `fb` as `Knx.Ets.Hawk.IAsyncNetworkAccessProvider`, but
  its members stayed blocked (`--update-map`: *virtual-or-override: use
  --review-families*). This wave uses the supported flow: a full-tree
  `--review-families` inventory (4.6 s, 332 MB, 141,360 families / 279,799
  members) supplies one seed row per family with its family id, and
  `--update-map` expands every seed to all members of that slot across the tree
  (the interface declaration and each implementation) under one name. Twelve
  families ship here, named from the released interface by unique shape match:
  `dt()`/`get_OutboundSegmentCouplerAddress`, `dz()`/`get_IsCloudConnection`,
  `d1`/`ReadLocalProgModeAsync`,
  `d2`/`SetRfMultiSlowDeviceToFastReceptionModeAsync`,
  `d5`/`ConnectDeviceLocalAsync`, `ef`/`GetAuthorizationLevel`,
  `e4`/`WriteToolKeyAsync`, `e5` and `fi`/`SecureSyncAsync`,
  `e7`/`GetNetworkAsync`, `e8`/`SetNetworkRfMode`,
  `e9`/`PingIndividualAddressAsync`. `ec()` keeps its
  explicit-method-implementation blocker and stays open. The update reported 36
  `ContractMethod` rows (10,423 → 10,459 renamed methods) with 0 errors.
  `names63-staged-v160.xml` =
  `026B3353F384CEE0AAC880C8BD13D8F2F2A5E7224087BD3E38BA471FA4DAF89E`, 11,950
  reviewed edits (12 seeds), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `830FE687E4B4BE0F…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,459 methods and 812 types in 528/528 modules with
  0 errors in 6.2 s, and `--verify-applied` reports `canonical_rows=575
  definitions_missing=0 stale_references=0` in 3.4 s. Applied tree:
  `Knx.Ets.Hawk.IAsyncNetworkAccessProvider::get_OutboundSegmentCouplerAddress`,
  `get_IsCloudConnection`, `ConnectDeviceLocalAsync`, `GetAuthorizationLevel`,
  `PingIndividualAddressAsync`, …
- **Wave 161: the compatibility plugin interfaces and their implementations.**
  Fifteen contract-family seeds (from the full-tree inventory) expand to the
  `Knx.Ets.ObjectModel.Compatibility.IPluginHost` and `…IPluginInstaller`
  declarations plus every implementation in the tree, named from the released
  interfaces by unique shape match: `ShowParameterDialogAsync`,
  `ShowPropertyPages`, `InvokeContextMenuItem`, `DeletingAssociation`,
  `ChangedSendingAssociation`, `ChangedGroupAddress`, `CanAddAssociation`,
  `TransferParameters`, `CheckDevice`, `ExportDevice`, `ImportedDevice`,
  `BeforeHawkPluginAccess`, `CreateEts3Plugin`, `AnyPluginRequiresElevation` and
  `InstallEts3Plugins`. The update reported 58 new `ContractMethod` rows
  (10,459 → 10,517 renamed methods) with 0 errors across twelve modules, and the
  applied `Knx.Ets.ObjectModel.dll` now shows
  `IPluginHost::ShowParameterDialogAsync/ShowPropertyPages/InvokeContextMenuItem/
  DeletingAssociation/…` by name.
  `names63-staged-v161.xml` =
  `8A1CC4F9F8870828C91F2CDF6482C8D5AF45107158487CAABC5ECBF00E34BA39`, 12,008
  reviewed edits (15 seeds), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `49A5303A80DBF028…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 10,517 methods and 812 types in 528/528 modules with
  0 errors in 6.9 s, and `--verify-applied` reports `canonical_rows=575
  definitions_missing=0 stale_references=0` in 3.3 s.
- **Wave 162: the correspondence queue, first bulk wave.** The shape queue
  against the wave-161 map yields 154 actionable members across the Falcon
  KNX-message classes (`MemoryExtended*Message`, `NetworkParameterMessageBase`,
  `ConfirmedRestartMessage`, `DeviceDescriptorResponseMessage`,
  `FileControl/FileOperationState/CheckChunkBlock*`, `CRI`, `KnxIpFrame`), the
  compatibility/object-model facades and a few HawkNET types. 18 of them are
  virtual/interface slots and ship as contract-family seeds (expanded by
  `--update-map`), the other 74 as plain rows; six no-op pairs
  (`IsDownwardCompatibleTo`, `get_ManagementModel`, `get_Version`,
  `get_MgmtDescriptor01`, `get_MaskEntries`, `GetHawkConfigurationData` — all in
  `Knx.Ets.Sdk.dll`, name → same name) are filtered out so the raw audit keeps
  `sdk-visible=0`. The families expand to 179 new renamed methods
  (10,517 → 10,696). New helper `perfprobe/family-seeds-batch2.py` splits a
  queue into family seeds and plain rows in one streaming pass over the 332 MB
  inventory.
  `names63-staged-v162.xml` =
  `D372B9BD4C75DACC53F6CE091CB68FE79E3D6AAE185F7F5994378E7CD882C5EF`, 12,187
  reviewed edits, 0 errors, `--check-map` PASS, same 51 suffixes; the export map
  `8B05F4A6253A8C80…` audits `sdk-visible=0, sdk-referenced-types=0`. The batch
  apply rewrote 10,696 methods and 812 types in 528/528 modules with 0 errors in
  6.6 s, and `--verify-applied` reports `canonical_rows=575
  definitions_missing=0 stale_references=0` in 3.6 s.
- **Wave 163: verified type rows from the queue.** Six type rows whose
  non-compat 6.4 counterpart is the unique shape match and was checked by hand:
  `Class915` (all nine member shapes) → `Knx.Falcon.KnxMessages.ApplicationLayer.NetworkParameterMessageBase`,
  `Class831` (8/9) → `…DeviceDescriptorResponseMessage`, `Class828` (7/9) →
  `…ConfirmedRestartMessage`, `Class844` (7/9) → `…CheckChunkBlockRequestMessage`,
  `Class754` (10/21, clear best) → `Knx.Falcon.KnxnetIp.Frames.KnxIpFrame` and
  `asm` (5/5) → `Knx.Ets.Common.Http.IHttpClient`. The new
  `perfprobe/verify-type-list.py` ranks the top non-compat 6.4 candidates for a
  list of 6.3 types (it excludes the `ETS6.3_compat_api2` copies).
  Deliberately left open because shape evidence cannot separate them:
  `Class791`/`Class794` vs `CRD`/`CRI` (identical members and bodies; only the
  declaration order suggests 791=CRD), `Class908`/`Class909`/`Class910` vs the
  read/write message classes (response classes share the same member shapes),
  `Class857`/`Class854` (two file-frame candidates tie), `Class907` (only
  compat matches) and `Class1196` (its counterpart is itself obfuscated).
  `names63-staged-v163.xml` =
  `ED0DA0EA6689A658BA9CDCE7391C09D5204570DB9AF9D1359D6C13DC850129DE`, 12,193
  reviewed edits (6 rows), 0 errors, `--check-map` PASS, same 51 suffixes; the
  export map `1CCAB5A387EEFD3C…` audits `sdk-visible=0, sdk-referenced-types=0`.
  The batch apply rewrote 818 types in 528/528 modules with 0 errors in 6.3 s,
  and `--verify-applied` reports `canonical_rows=575 definitions_missing=0
  stale_references=0` in 3.7 s. Applied tree: `NetworkParameterMessageBase`,
  `ConfirmedRestartMessage`, `DeviceDescriptorResponseMessage` and
  `Knx.Ets.Common.Http.IHttpClient` are all visible by name.
- **Wave 164: the queue's remaining readable-name members.** Applying the
  alignment gate (`build-wave164.py`: best non-compat type by unique shape
  match, then an ordered-member LCS ratio ≥ 0.6) to the queue left six types with
  37 queued members; 9 families carry blockers and 17 pairs were already
  readable no-ops (`get_Dynamic`, `get_Version`, `CreatePluginHost`,
  `IsDownwardCompatibleTo`, …), so 11 plain rows shipped
  (10,696 → 10,707 renamed methods).
  `names63-staged-v164.xml` =
  `3FEC75009E3076A4A78EB37D14A35CF3C63123B25EB43FBE4C38838962F055FF`, 12,205
  reviewed edits, 0 errors, `--check-map` PASS, same 51 suffixes; the export map
  `71AFA5E9C15E77B0…` audits `sdk-visible=0, sdk-referenced-types=0`. Apply
  rewrote 10,707 methods in 528/528 modules with 0 errors in 6.3 s;
  `--verify-applied` `definitions_missing=0 stale_references=0`.
- **Queue insight.** `correspondence-queue.py` lists members that have no map
  row, but a member may already carry a readable name in the binary (the
  compatibility/object-model assemblies were only partially obfuscated). Those
  pairs are no-ops (`NewName == OriginalName`) and must be filtered — they would
  otherwise count as raw `sdk-visible` rows and make the export filter drop
  extra rows. A future queue revision should skip members whose current name
  already passes the readability test (`MethodReview.Reason == null`).
