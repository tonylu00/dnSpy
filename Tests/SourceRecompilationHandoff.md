# Source recompilation handoff — 2026-09-11

The requested sample/ETS source recompilation workflow is implemented across
de4dotEx, NETReactorSlayer and dnSpy. The expanded ETS 6.3 validation completed
before 6.4; both now have direct official-SDK and protected-persistence checks.

## Outputs

| Output | ETS 6.3 | ETS 6.4 |
| --- | --- | --- |
| Compilable source | `D:\git\ets63-api-source47` | `D:\git\ets64-api-source19` |
| Complete staged application tree | `D:\knx_analysis\ETS6.3_source47` | `D:\knx_analysis\ETS6.4_source19` |
| Reviewed source map | `D:\knx_analysis\ets63-api-source-validation47\names.xml` | `D:\knx_analysis\ets64-api-source-validation19\source-names.xml` |
| Export/build invocation and logs | `D:\knx_analysis\ets63-api-source-validation47` | `D:\knx_analysis\ets64-api-source-validation19` |
| Direct live evidence | `D:\knx_analysis\ets63-source47-live1` | `D:\knx_analysis\ets64-source19-live1` |

The source roots contain `solution.sln`, project context/export manifests and
the accepted source-map snapshot. Build with `dotnet build solution.sln -c Release
-p:UseArtifactsOutput=false`. Export runners require a new output directory.
The validated dnSpy console is `D:\knx_analysis\delegate-cache-runtime2\dnSpy.Console.exe`.

## Requirement audit

| Requirement | Implementation and evidence |
| --- | --- |
| Full sample and ETS source compilation | Both protected sample scenarios (method encryption alone and with control flow) export/build and execute root/compatibility implementations with expected results 100/120 in `reactor-current-source-audit5`. Expanded ETS builds compile 111/178 projects, with zero SDK contract issues. |
| Keep duplicate physical contexts and file layout | Batch/context resolution and `Build/Stage-RecompiledTree.ps1` preserve separate same-identity implementations, unchanged files, empty directories and culture satellites. Expanded stages verify 381/403 assembly/satellite overlays and original input hashes. The uploader abstraction copies remain separate projects. |
| Skip components not protected by Reactor | Slayer's protected fixture reports process two protected components and skip eight for deobfuscation. Unprotected dependencies can receive necessary reference updates; unrelated clean copies remain unchanged. `slayer-final-audit2.log` records the batch suite. |
| Improve batch throughput | Slayer bounds parallel inspection/copying, retains inspected modules and incrementally captures reference graphs. Process-wide Reactor reflection/JIT operations remain serialized. This is not a claim that all decryption stages run concurrently. |
| Unique generic/parameter names | dnSpy allocates deterministic valid source names while restoring original runtime metadata names. The invalid-name regression covers nested generic positions, constructors, indexers, delegates, return rows, execution, exact metadata, one/four workers and incremental stability. See `ParameterMetadataNames.md`. |
| Preserve meaningful overloads and learn domain words | de4dotEx `MethodNameAnalysis` tokenizes names and learns corroborated words from names/literals per batch. Overload count does not determine obfuscation. Tests preserve `IsDeviceTesterLicensed`, common short verbs and learned `ETS`, rename private obfuscated overloads, and reject vocabulary leakage/order dependence. Current source hash matches the tested implementation; lexical checks pass. |
| Custom batch maps | Binary maps support guarded type/method/parameter renames across contexts, including virtual-family validation. Source maps provide readable aliases while retaining original runtime contracts. `custom-name-map-regression8.log` covers all frontends, execution, duplicates, preview and rejection cases. See `SourceNameMap.md`. |
| Use 6.3 as the 6.4 reference | de4dotEx NameCandidates consumes the reviewed 6.3 source map and records hash/token/signature-bound correspondence. The accepted 6.3 map has one type, five methods and one parameter; 6.4 has 496 methods across 25 modules and one parameter. Expanded-tree alias audits report zero issues. |
| Preserve strings | Decoder-parity reports cover 117,047 strings in 6.3, 93,181 in 6.4 and 120,291 in compatibility inputs, with no unverified strings or remaining decoder calls. `source-goal-string-audit2.json` records report hashes. |
| Keep official-SDK compatibility | Expanded contract audits cover 13,863/24,955 types, 103,176/183,678 methods and 17,441/32,702 fields. Unchanged SDK add-ins load 407/410 types and directly access test-mcp's 29 devices/502 group addresses in each rebuilt host. |
| Preserve runtime behavior across versions | Expanded 6.3 protected SDK edits survive restart/password entry. Expanded 6.4 reads that saved project, then persists additional edits to both migrated and native protected fixtures across restart/password entry. Saving is enabled and protection retained. Original profile/add-in and 4,811 original data files are restored after each test. |
| Generic tool fixes and milestones | Production changes use metadata, IL, dependency context and compiler patterns; ETS paths/names are test inputs, not production special cases. de4dotEx checkpoint `9d745a7d`, Slayer `e781981`; dnSpy runtime includes `444a5ef4b`. Expanded live milestones are `f1c51b563` and `e321c0682`. |

`D:\knx_analysis\source-goal-completion-audit1.json` rechecks every current
rebuilt project hash against its per-module audit (111 + 178 outputs), complete
export counts, alias results and live cleanup evidence. The expanded builds
match their independently validated baseline unions over 194,229/385,538
method bodies, with zero differences and no additional name alignment.

## Validation limits

Recovered names are reviewed aliases, not a claim to know every author's
original identifier. Unsupported or ambiguous mappings fail rather than guess.
Third-party/nonmanaged dependencies outside the exported project set are
preserved in the application tree. Installer/uploader helpers are compiled and
checked for contracts, integration and resources; their updater/network side
effects were not invoked. Compiler transformations can legitimately change
original IL; normalized comparisons and live scenarios are regression evidence,
not formal equivalence of every execution path. Builds retain compiler warnings.

The supplied 6.3 input already contained an older injected VirtualDongle runtime.
Its save-disabling ExtendedLogging default is preserved by source reconstruction
and was removed only in the disposable live copy using the reviewed helper.
Current VirtualDongle rejects that feature even through configuration overrides.
No original application input, user project, or installed profile was left
modified. ETS and test daemons are closed; port 37620 is free after cleanup.

See `EtsSourceValidation.md` for the detailed validation sequence and prior
failures that led to the generic fixes.
