# Final C# reconstruction observations

Build the **actual ILSpy plugin** first, then build this host with
`-p:RuntimeDirectory=<plugin output folder>`. The host requires byte-identical
dnlib, contracts and core references; plugin dependencies and input bytes are
hashed again before publishing a fresh report. It loads metadata, never executes
the inspected assembly, and resolves external metadata only from a manifest
whose physical paths, SHA256, MVID and complete assembly identities match.
There is no GAC or simple-name fallback. Missing dependencies remain explicit.

```
dotnet GeneratedSourceInspection.dll <runtime> <input> <new-report> inspect --references=<manifest>
dotnet GeneratedSourceInspection.dll <runtime> <input> <new-report> inspect --root=0x02000004 --references=<manifest>
dotnet GeneratedSourceInspection.dll <runtime> <input> <new-report> inspect --references=<manifest> --map=<source-map>
dotnet GeneratedSourceInspection.dll <runtime> <input> <new-report> inspect --references=<manifest> --map=<source-map> --sdk-source
dotnet GeneratedSourceInspection.dll <runtime> <native-report> <fresh-header> report-summary
dotnet GeneratedSourceInspection.dll <runtime> <input> <new-report> metadata --references=<manifest>
dotnet GeneratedSourceInspection.dll <runtime> <seed-manifest> <new-context> prepare-context --contexts=<loader-xml> --app-config=<main-config> --framework=<directory> --support=<directory>
dotnet GeneratedSourceInspection.dll <runtime> <complete-scope-summary> <new-audit> audit-scope
```

`--method=0x06000005` selects partial member scope. Ordinary decompiler switches
include `--no-async`, `--no-yield`, `--no-anon-methods`, `--show-all` and
`--declare-state-machines`. `--source=<new-file>` optionally emits one selected
root/member through the native C# decompiler. Outputs must be fresh and outside
the input directory. Reports bind the exact emitted source text hash even when
the text is discarded. A single worker with a 64 MiB stack processes one module
and one root at a time; elapsed time and peak process working set are recorded.

The reusable, portable `GeneratedSourceEvidence` helper in the ILSpy core
observes the final AST, after source filtering and printing transformations.
The C# provider exposes it through `PredefinedCustomDataIds.GeneratedSourceEvidence`
only when `DecompilationContext.CaptureGeneratedSourceEvidence` is enabled and
the output consumes custom data. Rewrite annotations are opt-in; normal exports
do not collect these extra observations. Capture includes exact successful
async/iterator and anonymous method witnesses, retained declarations, surviving
local member references, unresolved references and hoisted-field/source-variable
bindings. Compressed async lambdas retain their body witness. Captured parameter
substitutions retain their exact field binding without mutating shared ILVariables.

The complete `audit-scope` report also joins state-machine source coverage to
original metadata. Trusted framework state-machine attributes and exact builder
`Start<T>(ref T)` edges corroborate successful async/iterator witnesses. Canonical
source owners follow physical rewrite edges and declared property/event ownership;
cycles, missing edges and multiple owners remain explicit. Declared state members
and surviving local or cross-module printed uses have separate statuses. Original
state fields retain their source-variable bindings in the report. This coverage
does not establish runtime metadata restoration or semantic local names, and does
not retire naming candidates. The helper uses only dnlib and System.Text.Json;
the `StateCoverageRegression` project tests it on .NET 8 without WPF.
Successful async iterators report `AsyncIteratorMethod`, from the actual async/yield
reconstruction state, including empty async iterators. Ordinary async methods and
synchronous iterators retain their distinct kinds; disabled/failed rewrites have
no witness. This classification never depends on a compiler attribute's spelling.

`Refresh-PhysicalScope.ps1` refreshes an explicit module list from a hash-checked
complete base audit while retaining other immutable reports and their producer pins.
Use `-RequireUnchangedSource` for observation-only fixes. Supply `-Modules` as a
PowerShell array, then run the native complete `audit-scope` on the new summary;
refreshing reports alone is not an audit verdict. The refresh never edits application
inputs, mappings, source or review decisions.
Both scope drivers read compact native headers rather than expanding all reference
records in PowerShell. Headers retain physical/map/context pins, root identities,
source hashes, witness/binding counts and native memory observations. The full native
reports remain authoritative and are checked again by `audit-scope`. Producer scripts
are copied into each output directory before their hashes are pinned.

`NonlocalReferences` retains emitted external/unresolved use records with the
local source owner, requested signature/assembly, originating physical metadata
path/MVID/token and resolved definition path/MVID/assembly/token/signature. It
uses the reference's metadata context, so the inspection host supplies the pinned
source resolver. Type forwarders retain both the requested facade and actual
definition assembly. A `MemberRef` is classified by its signature because dnlib
implements both method and field interfaces on it. Local reference tokens remain
separate. Unresolved strings now mean resolution failed, rather than every external
reference. The host audits resolved targets against exact pinned definitions and
records any unpinned definition explicitly. Counts describe distinct annotation
records per owner; they are not call counts. This data does not prove source removal.
Reference tokens/annotations can also identify declaration names or inlined body
implementations for debugging. A downstream retirement decision must distinguish
these from printed member accesses; the current joins deliberately stay conservative.

Raw inspection uses `Mode=RawMetadataFinalCSharpAst` and `MapApplied=false`.
`--map` invokes the actual native source-map applier across all pinned export
inputs before decompilation; it uses `Mode=MappedFinalCSharpAst`, binds map/SDK
whitelist hashes and reports the selected module's aliases. Original definition
names/tokens and parameter/local alias scopes remain recorded. `--sdk-source`
sets the same `RestoreMetadataOnlyFields` C# context flag used by the actual SDK
project exporter, including native metadata restoration annotations and field
filtering. The flag is explicitly recorded; its default is false. This observes
one C# source view without writing SDK projects/resources or compiling them.
`metadata` reports physical identity/definitions plus physical AssemblyRef,
TypeRef and MemberRef tokens/declaring identities without AST/source output.
No mode retires review candidates, proves semantic names, claims application-wide
merging or proves compilation/runtime compatibility. Absence in one root's AST is insufficient. A future scope-wide
consumer must bind mapped source, all physical compatibility contexts, retained
references, restoration contracts and owner chains before retiring symbols.

The reference manifest has `Format=1`, optional `InputDirectory`, `Assemblies`
(`Path`, complete `Identity`, `Mvid`, `Sha256`, optional `ExportInput`), optional
`Bindings` (`Source`, effective complete `Identity`, exact physical `Target`,
optional original `RequestedIdentity`), optional `Configs` (`Source`, config
`Path`, `Sha256`) and `Contexts` (`Source`, ordered physical `Directories`).
`RequireSourceContexts=true` rejects incomplete context coverage and disables
global resolution for callers without a pinned scope. Physically distinct
assemblies may have the same identity. Only the calling module itself, an exact
binding or one unique pinned full identity in the first applicable search directory
may resolve. Legacy manifests without scopes permit a unique global pinned identity.
Ambiguity stays explicit. Bindings must correspond to a source AssemblyRef after
its pinned config redirect, the target's exact identity and allowed directory.
Export inputs must remain inside the pinned root. Mapped inspection requires the
same map input root and an exact pinned export-input object; dependencies are
read-only and do not become export inputs.

Configs apply only to their explicit source modules through the existing native
`ApplicationConfigResolver`. Reports retain requested/effective identities and
the config path, never treat a redirect as general version equivalence. Pins are
rehashed before publication. Build/run `ContextRegression` with the runtime's
dnlib and a fresh output directory for twin/self/ambiguity, explicit bindings,
redirect scope/culture/signing/range and stale hash/MVID/config/manifest guards.

`prepare-context` inventories metadata without executing it. The seed owns the
export-input flags; additional application/framework/support assemblies remain
read-only. Explicit `AssemblyContexts/Context` rows specify source and directory,
with optional config; an absent config explicitly overrides the main config for
that source. Main-root modules use the supplied main config. Other application
dependencies inherit a config only from consistent explicit host rows in their
physical directory; conflicting hosts stay recorded as unresolved context evidence.
The tool retains seed-proven physical bindings and selects new targets by complete
identity in ordered directories. Root/framework scans are recursive; explicit
support directories are not. Reparse points are skipped. Native PE files and
standalone netmodules retain hashes but cannot become assembly resolver targets.
No GAC or ambient fallback is used. Fresh outputs must lie outside the input tree;
pins, configs and preparation inputs are rechecked before publication. The output
manifest and adjacent `.preparation.json` record unresolved requests, config
provenance, elapsed time and peak working set. This is metadata context evidence,
not proof of loader equivalence, source merging or runtime compatibility.
`ContextRegression` also exercises preparation redirects/no-config overrides,
competing physical identities, read-only roles, retained netmodules, stale seeds,
DTD/duplicate contexts and failed publication.

Run `ReferenceRegression/Invoke-Regression.ps1` with `-RuntimeDirectory`,
`-Inspector` and a fresh `-OutputDirectory`. Its synthetic assemblies deliberately
share complete identity, MVID and definition tokens while retaining different
paths and bytes. Method/field/type uses must bind to their own physical twin;
missing and ambiguous contexts must remain unresolved. It also checks owner
provenance, deterministic observations/source and unchanged input hashes.

`PrintedReferences` records metadata bindings selected by the actual C# token
writer, including identifier, keyword and operator/indexer/delegate-call tokens.
Each record has physical reference/definition provenance, source owner, node kind,
printed text and form. `IsDefinition` separates declaration names from uses;
`IsImplementationAnnotation` marks the anonymous method link attached to the
`delegate` keyword. Such links are not printed implementation calls.
`PrintedReferenceTokens` contains only local definition tokens used outside those
two categories. `PrintedReferenceCoverage` distinguishes an observed writer from
an older or AST-only capture. No observer runs on the default printing path.
The inspector audits resolved printed records against exact physical metadata.
Comments, debug spans and implicit compiler bindings are outside these records;
their absence cannot establish removal or restoration safety. Preserve the
existing conservative AST reference observations alongside this additional view.

`Inspect-PhysicalScope.ps1` takes `-RuntimeDirectory`, `-Inspector`,
`-ReferenceManifest`, `-SourceMap` and a fresh `-OutputDirectory`. It inspects every
explicit export input in a required-context manifest using mapped SDK C# settings.
Native child processes run sequentially to bound decompiler lifetime to one
physical module. Reports preserve application-relative directories, and a hash-bound
summary records native observations, timing, peak child working set and explicit
uncertainties. Maps, runtime/host binaries and context pins are checked again at
each checkpoint. This is source observation only; it performs no ETS source/binary
patches, candidate retirement, project exports, builds or runtime tests.

`audit-scope` verifies the complete observation summary against original metadata.
It requires exactly the pinned export inputs, every original top-level root,
complete original definition inventories and printed-source hash coverage. It
rejects filtered scopes, differing normalized maps, stale native reports/tool pins,
foreign owner tokens, invalid rewrite implementations and hoisted-field bindings.
Nonlocal targets are checked again by physical path/MVID/identity/token/signature;
missing or unpinned targets and unknown owners stay explicit. The audit also
indexes first-party definitions retained by other modules' emitted references.
Printed records are independently counted and classified. Original reference
tokens are re-resolved in their own pinned source contexts; swapping identical
physical twins is rejected. In-memory CorLibTypes/imported references without an
original metadata row remain explicit as synthetic/unavailable origins. The
auditor compares each root's actual local-use set and every module's printed
counter with the report. It separately indexes cross-module printed uses, excluding
declarations and anonymous implementation links. Older AST-only reports still
pass the AST audit, with partial or absent writer coverage recorded explicitly.
This establishes observation coverage, not source retirement or runtime behavior.
`ReferenceRegression/Invoke-ScopeAuditRegression.ps1` exercises these native guards
with the previously emitted physical-twin fixture.
`ReferenceRegression/Invoke-GenericOriginRegression.ps1` builds a synthetic fixture
with generic type fields and reconstructed generic lambdas. Supply the runtime,
inspector, explicit framework directory and fresh output directory. The audit
must bind MemberRef and MethodSpec operands through their exact original body
contexts and reject an altered generic field role. No application inputs change.

Run `Invoke-Regression.ps1` with `-RuntimeDirectory`, `-Inspector`,
`-ReferenceManifest` and a fresh `-OutputDirectory`. It builds synthetic fixtures,
checks observation/source determinism and opt-in isolation, disabled transforms,
partial scope, generated-looking real names, compressed async lambdas, captured
fields, and retained type/member/signature/shared-fallback/public implementations.
Native synthetic metadata checks reject terminal Dispose lookalikes with another
state, another field or an extra side effect. Original and native-decompiled
sources both compile and execute the same iterator/async/closure behavior probes.
Output/reference/scope guards must reject without publishing a report.
The suite also maps one exact captured-field definition through the actual native
applier. Its checked alias must seed the reconstructed local and every recursive
reference. A second alias collides with a nested lambda parameter; allocation
must avoid shadowing. Both SDK C# views compile and reproduce the original 24
behavior cases, while captured parameter identity and input bytes stay intact.
Printed-reference guards cover declaration/debug distinctions, reconstructed and
recursive lambdas, ordinary field accesses, named method groups, constructor
keywords, operators, indexers and delegate invocation punctuation.

Current Roslyn emits a no-cleanup iterator Dispose body as `state = -2; return;`.
The iterator recognizer now accepts only that complete exact pattern and keeps
other bodies on its existing analysis/fallback path. Set `ILSPY_ITERATOR_TRACE=1`
for analysis diagnostics; it is disabled by default.

`Inspect-StateSourceGaps.ps1 -OwnerTokens 0x0600055C,0x06000E86` limits a cold
recheck to exact owner MethodDef tokens in the identity-bound retained worklist.
The summary records both the full retained-row count and selected scope; missing
or malformed filters fail before output. A token can select multiple physical
modules, whose identities remain distinct. Filtered witnesses do not change
whole-scope coverage or retire candidates.

`Tests/Invoke-ReferenceAwaitRegression.ps1` exports and rebuilds typed and
object-backed reference awaiters with one and four workers, comparing 492
original behavior cases and 92 identity/receiver/resume guards. The native
matcher preserves assembly/type identity and accepts only compiler resume
bookkeeping; foreign receivers, casts, fields and side effects remain rejected.
`Tests/Invoke-ArchiveMetricsAwaitBehaviorProbe.ps1` compiles one caller against
original ETS contracts and runs its real public archive collector against each
physical module. Its 336 Rx cases record all loaded assembly identities, paths
and hashes, require rebuilt ViewModel/Common/ObjectModel companions in the
validated run, and retain raw traces. Disposal may race a continuation on another
thread, so the stable comparison checks its exact count without imposing that
interthread order. These focused checks do not establish complete ETS/App startup.

`Tests/Invoke-CatchAwaitRegression.ps1` rebuilds catch awaits with nested finally
cleanup under one and four export workers, comparing 1,728 original behavior
cases. Its 161 guards require proof that every try/catch path exits, preserve
reachable dispatch and nested entry regions, and retain removed dispatch spans.
`Tests/Invoke-BackupCatchAwaitBehaviorProbe.ps1` compares 1,008 cases through the
exact original backup owner and typed interfaces, with the real base operation
and error view-model constructor. It bypasses the handler constructor and injects
proxies for this focused comparison; it does not perform archive or live UI work.
Each original/rebuilt process records loaded assembly identities, paths and hashes.
