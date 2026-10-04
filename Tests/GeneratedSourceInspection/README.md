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

These reports deliberately use `Mode=RawMetadataFinalCSharpAst` and
`MapApplied=false`. They do **not** apply a source map, retire review candidates,
prove semantic names, claim application-wide merging or prove compilation/runtime
compatibility. Absence in one root's AST is insufficient. A future scope-wide
consumer must bind mapped source, all physical compatibility contexts, retained
references, restoration contracts and owner chains before retiring symbols.

Run `Invoke-Regression.ps1` with `-RuntimeDirectory`, `-Inspector`,
`-ReferenceManifest` and a fresh `-OutputDirectory`. It builds synthetic fixtures,
checks observation/source determinism and opt-in isolation, disabled transforms,
partial scope, generated-looking real names, compressed async lambdas, captured
fields, and retained type/member/signature/shared-fallback/public implementations.
Native synthetic metadata checks reject terminal Dispose lookalikes with another
state, another field or an extra side effect. Original and native-decompiled
sources both compile and execute the same iterator/async/closure behavior probes.
Output/reference/scope guards must reject without publishing a report.

Current Roslyn emits a no-cleanup iterator Dispose body as `state = -2; return;`.
The iterator recognizer now accepts only that complete exact pattern and keeps
other bodies on its existing analysis/fallback path. Set `ILSPY_ITERATOR_TRACE=1`
for analysis diagnostics; it is disabled by default.
