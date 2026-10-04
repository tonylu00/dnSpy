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
dotnet GeneratedSourceInspection.dll <runtime> <input> <new-report> metadata --references=<manifest>
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

Raw inspection uses `Mode=RawMetadataFinalCSharpAst` and `MapApplied=false`.
`--map` invokes the actual native source-map applier across all pinned export
inputs before decompilation; it uses `Mode=MappedFinalCSharpAst`, binds map/SDK
whitelist hashes and reports the selected module's aliases. Original definition
names/tokens and parameter/local alias scopes remain recorded. `--sdk-source`
sets the same `RestoreMetadataOnlyFields` C# context flag used by the actual SDK
project exporter, including native metadata restoration annotations and field
filtering. The flag is explicitly recorded; its default is false. This observes
one C# source view without writing SDK projects/resources or compiling them.
`metadata` reports physical identity/definitions without AST/source output.
No mode retires review candidates, proves semantic names, claims application-wide
merging or proves compilation/runtime compatibility. Absence in one root's AST is insufficient. A future scope-wide
consumer must bind mapped source, all physical compatibility contexts, retained
references, restoration contracts and owner chains before retiring symbols.

The reference manifest has `Format=1`, optional `InputDirectory`, `Assemblies`
(`Path`, complete `Identity`, `Mvid`, `Sha256`, optional `ExportInput`), optional
`Bindings` (`Source`, requested complete `Identity`, exact physical `Target`),
and optional `Configs` (`Source`, config `Path`, `Sha256`). Physically distinct
assemblies may have the same identity. Only the calling module itself, an exact
binding or one unique pinned full identity may resolve. Ambiguity stays explicit.
Bindings must correspond to a source AssemblyRef and the target's exact identity.
Export inputs must remain inside the pinned root. Mapped inspection requires the
same map input root and an exact pinned export-input object; dependencies are
read-only and do not become export inputs.

Configs apply only to their explicit source modules through the existing native
`ApplicationConfigResolver`. Reports retain requested/effective identities and
the config path, never treat a redirect as general version equivalence. Pins are
rehashed before publication. Build/run `ContextRegression` with the runtime's
dnlib and a fresh output directory for twin/self/ambiguity, explicit bindings,
redirect scope/culture/signing/range and stale hash/MVID/config/manifest guards.

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
must avoid shadowing. Both SDK C# views compile and reproduce the original 23
behavior cases, while captured parameter identity and input bytes stay intact.

Current Roslyn emits a no-cleanup iterator Dispose body as `state = -2; return;`.
The iterator recognizer now accepts only that complete exact pattern and keeps
other bodies on its existing analysis/fallback path. Set `ILSPY_ITERATOR_TRACE=1`
for analysis diagnostics; it is disabled by default.
