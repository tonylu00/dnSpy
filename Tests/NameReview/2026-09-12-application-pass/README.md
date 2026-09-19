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
