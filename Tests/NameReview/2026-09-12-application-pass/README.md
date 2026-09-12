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
The current staged maps are `names63-staged-v14.xml` and `names64-staged-v6.xml`
under the application pass directory; `progress.json` records their hashes.

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
