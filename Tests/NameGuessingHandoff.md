# External-agent handoff: infer readable ETS names

## Start with the cross-platform review inventory

Use the C#/.NET 8 NameCandidates tool, not ad hoc PowerShell regex filters.
From the de4dotEx checkout, these commands work with platform-local paths on
Windows, macOS or Linux:

```text
dotnet build tools/NameCandidates/NameCandidates.csproj -c Release
dotnet tools/NameCandidates/bin/Release/net8.0/NameCandidates.dll --review-obfuscated ./restored ./methods.json
dotnet tools/NameCandidates/bin/Release/net8.0/NameCandidates.dll --review-map ./reviewed.json ./restored ./source-names.xml
```

Copy the inventory to `reviewed.json` and fill in accepted rows' `NewName`.
All identity fields are already populated. Use `--review` for every method,
including those not classified as obfuscated. `--review-obfuscated` includes
unrecognized short names and suffixes such as `a`, `b`, `c_1`, `d_1`, while
preserving meaningful words and learned vocabulary. It is independent of
cross-version body matching. `MappingBlocker` exposes unsupported contract
cases; keep those proposals in the ledger rather than losing them from the list.
Conversion repairs ordinary alias collisions with deterministic suffixes and
checks authoritative metadata. For an existing seed map, use the executable
merge and preflight commands instead of editing XML:

```text
dotnet tools/NameCandidates/bin/Release/net8.0/NameCandidates.dll --update-map ./reviewed.json ./seed-names.xml ./updated-names.xml ./update-report.json
dotnet tools/NameCandidates/bin/Release/net8.0/NameCandidates.dll --check-map ./updated-names.xml ./check-report.json
```

The updater preserves untouched rows and parameter/type aliases, resolves name
collisions against the merged map, and reports per-entry errors before export.
It never overwrites the seed and publishes no map if any entry fails.
Fresh inventories are available on this machine under
`D:\knx_analysis\method-review-20260911` (`obfuscated63.json` and
`obfuscated64.json`; `methods63.json`/`methods64.json` contain all methods).

The existing `name-review-01/List-ObfuscatedMethods.ps1` uses a case-insensitive
regex that incorrectly includes `Load`, `Map`, `On`, `Save` and misses suffixed
short names. Replace its use with this tool. No regex evaluation or inventory
generation in this workflow requires PowerShell. The historical Windows paths
below identify the prepared ETS datasets, not a platform requirement for naming.

## Objective and current state

Infer descriptive type, method and parameter names from behavior, first in ETS
6.3, then transfer reviewed names to 6.4 and investigate unmatched methods.
The compilation/tooling workflow is finished; comprehensive semantic naming is
not. The current maps are seeds: 6.3 contains one type, five methods and one
parameter; 6.4 contains 496 methods across 25 modules and one parameter.
Inferred names are hypotheses, not recovered original author names.

Use dnSpy **source-only aliases** for this task. Source code becomes readable,
while the generated build tasks restore original runtime metadata names for
SDK/reflection compatibility. Binary `NameMap` and source `SourceNameMap` are
different formats. Do not apply binary renames to the ETS host for this task.
The tokenizer detects likely meaningful/obfuscated names; it does not infer
what a method does. NameCandidates transfers names using cross-version evidence;
the agent supplies behavioral reasoning and reviews the suggestions.

## Authoritative inputs

| Purpose | Path |
| --- | --- |
| Immutable 6.3 analysis binaries | `D:\knx_analysis\ETS6.3_api_preserved4` |
| Immutable 6.4 analysis binaries | `D:\knx_analysis\ETS6.4_api_preserved5` |
| External compatibility context used by 6.4 | `D:\knx_analysis\ETS6.3_compat_api2` |
| Readable/built 6.3 source baseline | `D:\git\ets63-api-source47` |
| Readable/built 6.4 source baseline | `D:\git\ets64-api-source19` |
| Seed 6.3 source map | `D:\knx_analysis\ets63-api-source-validation47\names.xml` |
| Seed 6.4 source map | `D:\knx_analysis\ets64-api-source-validation19\source-names.xml` |
| Validated exporter | `D:\knx_analysis\delegate-cache-runtime2\dnSpy.Console.exe` |
| Candidate scanner project | `D:\git\de4dotEx\tools\NameCandidates\NameCandidates.csproj` |

Use the source trees for reading behavior, but obtain map identities from the
analysis binaries above. Rebuilt output tokens/MVIDs/hashes are not input map
identities. Consult `dnspy-export-map.xml` to associate each source project with
its exact physical input. Same-named assemblies under different directories can
be different implementations: never merge them by assembly name alone.

Create a new work directory, for example `D:\knx_analysis\name-review-01`.
Copy both seed maps into it. Preserve existing aliases unless a deliberate,
documented correction is needed. All reports/export destinations must be new.

## 1. Infer names in 6.3

Work in small coherent groups (one type or subsystem), beginning with methods
whose purpose is clear. Inspect C# and IL, callers and callees, literal strings,
exceptions, resources, parameter use, return values and observable side effects.
Read all significant branches before naming a method.

For each proposal, keep a review ledger with:

* Physical module path, SHA256, MVID, original metadata token and signature.
* Original name, proposed name, confidence and concrete behavioral evidence.
* Caller/callee evidence, competing interpretations and validation performed.
* Decision: accepted, needs investigation, or unsupported by the current map.

Prefer names describing the actual operation: `GetMajorVersion`,
`TryReadCertificate`, `ValidateProjectHeader`. Name parameters by their role,
not just their type. Infer a type's responsibility from several methods and its
usage, not one suggestive string. A wrapper may delegate the real operation;
trace it before assigning a name. Leave uncertain names unchanged and record
why. Preserve meaningful names such as `IsDeviceTesterLicensed`, including its
overloads; overload count and short length alone are not evidence of obfuscation.

Enter accepted guesses into the copied 6.3 `SourceNameMap`. Each Module requires
the exact relative `Path`, `Mvid` and `Sha256`; each Type/Method requires its
original token, `ExpectedName`, and original dnlib `FullName` as `Signature`.
Use dnlib metadata inspection or the existing inventory tooling to obtain these
values; never execute an input assembly to discover them. Write XML using an
XML API so signatures and names are escaped correctly.

The existing seed map is a concrete complete example. Parameter rows use
one-based `Sequence` excluding `this`, exact `ExpectedName`, and `NewName`.
Method `NewName` may be omitted for a parameter-only change.

Current source-map limits: non-generic types and ordinary nonvirtual methods;
generic methods and their parameters are supported. Constructors, accessors,
virtual/override and PInvoke/runtime methods are rejected. Keep proposals for
unsupported targets in the ledger rather than bypassing validation. Automatic
duplicate generic/parameter naming is already handled by the exporter and does
not require semantic guesses.

## 2. Transfer reviewed names from 6.3 to 6.4

Build the scanner and run it against the unchanged analysis inputs, using your
expanded, reviewed 6.3 map. These commands write reports only:

```powershell
dotnet build D:\git\de4dotEx\tools\NameCandidates\NameCandidates.csproj -c Release

dotnet D:\git\de4dotEx\tools\NameCandidates\bin\Release\net8.0\NameCandidates.dll --reference-source-map D:\knx_analysis\name-review-01\names63.xml D:\knx_analysis\ETS6.3_api_preserved4 D:\knx_analysis\ETS6.4_api_preserved5 D:\knx_analysis\name-review-01\candidates64.json
```

The scanner compares relative physical paths, scoped signatures, normalized IL,
locals, exception handlers and unique call correspondence. Inspect `MatchRound`,
`MatchedCallees`, `DeclaringTypeEvidence`, original/target identities and the
suggested name. Matching IL is useful evidence, not a proof of identical external
dependencies or behavior. Missing/ambiguous matches require manual investigation.
Two independently unique reviewed method bodies can establish a renamed type
correspondence; one suggestive method is insufficient.

Copy the candidate report to `selected64.json`, retaining the report's other
fields and only the accepted entries in `Candidates`. You may revise
`SuggestedName`; keep identity/evidence fields unchanged. Then convert:

```powershell
dotnet D:\git\de4dotEx\tools\NameCandidates\bin\Release\net8.0\NameCandidates.dll --source-map D:\knx_analysis\name-review-01\selected64.json D:\knx_analysis\ETS6.4_api_preserved5 D:\knx_analysis\name-review-01\generated64.xml
```

Merge the accepted generated method map with the seed using the executable
updater; it retains seed type/parameter rows, validates physical identities and
resolves collisions across the merged module:

```text
dotnet tools/NameCandidates/bin/Release/net8.0/NameCandidates.dll --merge-map ./generated64.xml ./names64.xml ./merged64.xml ./merge64-report.json
dotnet tools/NameCandidates/bin/Release/net8.0/NameCandidates.dll --check-map ./merged64.xml ./check64-report.json
```

Review the report's requested/applied aliases. Invalid entries produce a full
diagnostic report and no map; do not concatenate XML or bypass the failure.
Validate the merged map through export. Investigate unmatched 6.4 code using
the same ledger and behavioral process as 6.3.

## 3. Export, build and verify each batch — 6.3 first

Reuse the complete input lists, configurations and dependency contexts in:

* `D:\knx_analysis\ets63-api-source-validation47\Run.ps1`
* `D:\knx_analysis\ets64-api-source-validation19\Run.ps1`

Copy each runner and its referenced local input/context files to new validation
directories. Change its work/output/map paths to new destinations and the merged
map, retaining all input assemblies, dependency paths and app configuration.
Read the complete copied script before running it. Do not invoke an old runner
against its existing output. Preserve the explicit external 6.3 contexts in the
6.4 runner. Replacing these lists with only root DLLs loses compatibility helpers.

After export and a successful Release build, run the following for each version.
Substitute the appropriate new export/audit paths; each audit output must be new:

```powershell
$export = 'D:\git\ets63-name-review01'
$audit = 'D:\knx_analysis\name-review-01\audit63'
$dnlib = 'D:\knx_analysis\delegate-cache-runtime2\dnlib.dll'

& D:\git\dnSpy\Tests\Invoke-SdkSourceContractAudit.ps1 -DnlibPath $dnlib -ExportDirectory $export -OutputDirectory "$audit-sdk"
& D:\knx_analysis\Audit-SourceAliases.ps1 -DnlibPath $dnlib -ExportDirectory $export -Output "$audit-aliases.json"
& D:\git\dnSpy\Tests\Invoke-SourceStateMachineAttributeAudit.ps1 -DnlibPath $dnlib -ExportDirectory $export -OutputDirectory "$audit-state"
& D:\git\dnSpy\Tests\Invoke-SourceMethodBodyAudit.ps1 -BeforeExport D:\git\ets63-api-source47 -AfterExport $export -NameCandidatesProject D:\git\de4dotEx\tools\NameCandidates\NameCandidates.csproj -OutputDirectory "$audit-bodies"
```

For 6.4 use its new export and `D:\git\ets64-api-source19` as BeforeExport.
Require zero export/build errors, complete project coverage and zero contract,
alias and state-attribute issues. Investigate every method-body difference.
Source aliases can affect compiler-generated names; do not hide a mismatch by
loosening fingerprints or blindly enabling alignment. If a new name exposes an
exporter defect, fix it generically and verify 6.3 before proceeding to 6.4.

Keep changes in small reviewed batches. Compare input hashes before/after;
never modify the analysis baselines. Live ETS testing must be coordinated with
the user, use copied test projects and fresh profile backups, and restore the
profile/add-in afterward. Do not launch or patch the user's working ETS merely
to investigate a name. Existing source47/source19 live tests cover the seed maps,
not future changes. Do not enable ExtendedLogging: it suppresses saving.

## Deliverables

Return merged `names63.xml` and `names64.xml`, selected candidate reports, the
review ledger (including unresolved names), fresh build/audit results, and a
summary of accepted names and remaining uncertainty. Maps and ledgers are the
maintainable deliverables; direct edits to generated C# are not a substitute.

Read `D:\git\dnSpy\Tests\SourceNameMap.md`,
`D:\git\de4dotEx\tools\NameCandidates\README.md` and
`D:\git\dnSpy\Tests\SourceRecompilationHandoff.md` for format details and
current compilation/live-test evidence.
