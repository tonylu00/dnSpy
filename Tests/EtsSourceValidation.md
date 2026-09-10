# ETS source recompilation milestones

## Current checkpoint: 2026-09-11

The current tool runtime is `D:\knx_analysis\delegate-cache-runtime2`, including
the state-machine and delegate-cache name fixes. Full 6.3 source45 validation
passed before starting the corresponding 6.4 source18 run.

The initial passing builds omitted some shipped application assemblies. A
physical input inventory found three additional 6.3 assemblies under
`Uploader/Windows` absent from the source45 export. The uploader's telemetry
abstraction assembly differs from the root copy, so it needs its own context.
`ets63-uploader-validation2` exports all three as SDK projects, compiles with zero
errors and audits 86 types / 304 methods / 35 fields with zero contract issues.
The expanded `ets63-api-source-validation46` passes with 114 inputs, 110 managed
projects, zero SDK issues, 3,013 valid state-machine attributes and all approved
aliases preserved. `source46-body-audit-repo1` compares all 194,222 bodies against
the disjoint source45/uploader-source2 baselines with zero differences; staging
preserves 380 assembly/satellite overlays and the unchanged SDK add-in loads.
A publisher-metadata inventory additionally finds `PostActivation.exe` in both
versions. Its isolated 6.3 SDK export/build/contract audit passes in
`ets63-postactivation-validation2`. The 115-input source47 run passes: 111
projects compile with zero SDK issues, all 3,013 state-machine attributes and
approved aliases pass, and 194,229 bodies match the disjoint source46/helper
baselines with zero differences. Staging preserves 381 assembly/satellite
overlays; the unchanged official-SDK MCP add-in loads 407 types.
The 6.4 inventory identified six uncovered application files in total;
their expansion followed the 6.3 gate. Initial filename inventory artifacts are
`ets63-source-coverage-20260911.json` and `ets64-source-coverage-20260911.json`.
The 6.4 inventory covers its primary input tree; the 172-project export also
includes explicit external 6.3 compatibility contexts.
Publisher metadata results are in `ets63-preserved-vendor-metadata-20260911.json`
and `ets64-preserved-vendor-metadata-20260911.json`; filename prefixes alone did
not establish complete coverage.

After that 6.3 gate, `ets64-additional-validation1` exports and compiles all six
additional assemblies as SDK projects. Its contract audit checks 89 types, 318
methods and 35 fields with zero issues. The expanded 182-input full 6.4 run is
`ets64-api-source-validation19`. It passes export/build with 178 managed projects
and zero SDK issues (24,955 types, 183,678 methods, 32,702 fields). All 496 method
aliases and the parameter alias pass, as do 5,891 local state-machine attributes.
`source19-body-audit-repo1` compares 385,538 bodies against source18 plus the
isolated six-component baseline: zero differences, without owner-name alignment.
Staging preserves 403 assembly/satellite overlays and the unchanged official-SDK
MCP add-in loads 410 types. All six publisher-identified additions appear in the
export manifest.

`additional-source-resource-parity1.json` compares all ten added assemblies
(four in 6.3, six in 6.4) against their original input resources. Resource names,
flags, counts and the sole embedded resource's bytes match. The audit includes
the x86 output directory of the 6.4 PluginInstaller project. Source47/source19
are now the expanded offline-validated trees.

`ets63-source47-live1` directly validates the expanded 6.3 tree. The unchanged
official-SDK add-in opens test-mcp with 29 devices and 502 group addresses.
The protected P-07CC copy accepts its password, and an SDK contract-number
edit (`SRC47-PROTECTED-SAVE`) survives a complete process restart and another
password entry. The prior project-number marker and protection remain intact;
the bridge reports `save_suppressed: false`. The original profile, add-in and
all 4,811 original data-file hashes are restored after shutdown. Its legacy
injected DevKit default was removed only in the disposable live copy, with
input/output hashes recorded. Direct 6.4 live evidence still covers source18;
source19's automation and separate test stores are prepared for the next check.

- **6.3:** `ets63-api-source-validation45` compiles 107 managed projects, with
  zero SDK contract issues. All 193,872 method-body fingerprints match the
  live-tested source44 without additional name normalization. Original mapped
  names and all 3,005 local state-machine attributes pass independent audits.
  `ETS6.3_source45` preserves the full staged tree; the unchanged official-SDK
  MCP add-in loads 407 types.
- **6.3 live evidence:** `ets63-source44-live1` verifies Chinese UI, test-mcp
  project access, an SDK metadata update surviving a process restart, and
  password-protected project opening. Original profile/add-in and all 4,811
  recorded original data-file hashes were restored; ETS and its daemon exited.
  The later `ets63-source45-live1` runs the latest tree directly: a UI edit and
  an official-SDK edit to a disposable protected project both survive a full
  ETS process restart and password entry. The project remains protected and
  healthy, with saving enabled. Its profile/add-in, original data and source
  fixture hash checks pass as well.
- **6.4:** `ets64-api-source-validation18` compiles 172 managed projects with
  zero SDK contract issues. All 496 reviewed method aliases across 25 modules
  retain their original runtime names, and all 5,883 local state-machine
  attributes resolve. Its 385,160 method bodies match the tested source14 after
  71 verified generated-owner name corrections. The two delegate-cache
  mismatches from source17 are fixed, including exact instruction-text checks
  of the affected constructor/disposal bodies. Staging preserves 397 assembly/
  satellite overlays and the unchanged SDK add-in loads 410 types.
- **6.4 live evidence:** `ets64-source18-live1` verifies Chinese UI and an
  unchanged official-SDK MCP add-in accessing test-mcp (29 devices and 502 group
  addresses). Its SDK metadata update survives an ETS process restart. Fresh
  frozen password-protected projects from both 6.3 and 6.4 open successfully.
  Saving is not suppressed. This run does not separately prove a protected
  project save/reopen cycle. Cleanup verifies the original profile, add-in,
  all 4,811 recorded original data files and frozen fixtures are unchanged;
  ETS and its daemon exited, and port 37620 is free.
- **6.4 protected persistence:** `ets64-source18-live2` copies the protected
  project just saved by source45 into the 6.4 test store and opens it with its
  password. The unchanged official-SDK add-in reads both 6.3 edits correctly.
  An additional SDK edit to that migrated copy and another to a native 6.4
  protected fixture both survive a full ETS process restart and fresh password
  entry. Both projects remain protected and healthy, with saving enabled.
  `protected-roundtrip-result.json` and the SDK before/update/restarted reports
  record the exact markers and process IDs. Source fixture hashes and the
  original profile, add-in and all 4,811 original data-file hashes match after
  restoration.

`delegate-cache-regression4` covers async methods, iterators, constructor
lambdas, ordinary/generic delegate caches, original reflection names, event
subscription/removal and incremental rebuilds with one/four export workers.
`delegate-cache-baml-regression1` additionally covers WPF type/event aliases,
resource-URI loading and opaque resource preservation on this tool build.
`reactor-current-source-audit5` repeats both protected fixture scenarios on this
same runtime: method encryption alone and encryption with control flow both
export, compile and execute in the root and compatibility contexts (100/120).
`source-goal-string-audit2.json` verifies all retained decoder-parity reports have
successful exits, no unverified strings and no remaining decoder calls, and
records their hashes: 117,047 strings for 6.3, 93,181 for 6.4 and 120,291 for the
compatibility tree. This checks the existing evidence; it is not a fresh decoder
execution or a claim that every rebuilt method has identical original IL.

The repository runner in `SourceMethodBodies.md` independently repeats the
full comparison: `source45-body-audit-repo2` checks 107 projects / 193,872 bodies
with zero differences and no alignment; `source18-body-audit-repo1` checks 172
projects / 385,160 bodies with 71 verified owner-name corrections and zero
remaining differences. The first 6.3 runner attempt completed comparisons but
failed its Windows PowerShell summary formatting; repo2 includes that fix.
`source-body-audit-regression1` verifies physical duplicate isolation, changed-body
and missing-project rejection, and unchanged input hashes. A separate negative
check also detects both source17 delegate-cache regressions.

`goal-api-audit-20260911-1` reruns de4dot's lexical/SDK caller checks, including
meaningful overloads, learned vocabulary and journal hashes.
`goal-name-candidates-public-audit1` checks guarded cross-version maps and physical
contexts after exposing the shared fingerprint API in de4dotEx commit `9d745a7d`.
`goal-parameter-audit-20260911-1` repeats duplicate generic/parameter export with
one/four workers, successful execution and exact restoration of 38 parameter rows.

Artifact names above are under `D:\knx_analysis`; exported source trees are under
`D:\git`. The sections below retain the evidence and failures that led here.

## Earlier expanded reference-map validation

The 496-method, 25-module 6.4 map exposed a BAML export omission in source15:
the C# event handlers had source aliases, while reconstructed XAML still used
their original names. Export completed, but compilation failed with 16 CS1061
errors in UserControls. This is not a successful full rebuild.

The generic connector exporter now obtains handler names from the same metadata
name service as C#, covering ordinary events, attached events and style event
setters. The connector regression passes with and without source aliases, using
one/four workers, and checks runtime event execution and original reflection
names. Evidence: `D:\knx_analysis\baml-source-alias-regression3.log` and
`baml-no-alias-regression1.log`. Full 6.3 source40 validation starts before the
6.4 retry; the previously validated source39/source14 trees remain separate.

The current de4dot matcher still produces zero candidates for a 528-module 6.3
self-comparison. An independent metadata check of source39 verifies its one
mapped type, five methods and one parameter retain their original runtime names:
`D:\knx_analysis\ets63-source39-alias-audit1.json`.

## Earlier completed milestones

The source40 build subsequently completed: 111 inputs, 107 managed projects,
zero build errors and zero SDK audit differences (13,776 types, 102,871 methods,
17,406 fields). Evidence: `D:\knx_analysis\ets63-api-source-validation40`.

An independent WPF type-map probe then found source/runtime naming gaps in
`x:Class`, child-control references, temporary markup assemblies and compiled
BAML type records. The generic type-alias regression now covers these paths,
including resource-URI loading and incremental builds. Both aliased and default
exports pass with one/four workers; the modern WPF markup compilation mode also
passes. Evidence: `baml-type-alias-regression3.log`,
`baml-type-no-alias-regression1.log`, `baml-type-alias-modern1.log` under
`D:\knx_analysis`. These additional changes require the next full 6.3/6.4 run;
source40 does not validate changes made after its export.

Source41 caught an additional resource-format regression: Reports contains a
container requiring `System.Resources.Extensions.DeserializingResourceReader`,
which the BAML restoration task incorrectly opened with the standard reader.
The task now checks reader headers and preserves nonstandard containers without
deserializing values. `baml-resource-reader-regression1.log` verifies opaque
preserialized bytes survive while aliased WPF controls execute correctly, with
one/four workers and incremental builds. Source41 remains a failed build;
source42 is the subsequent full validation run.

Source42 completed after an interrupted export/build handoff. Before resuming
compilation, its zero-error export manifest, all 107 project files and exact
source-map snapshot were verified. The full build and SDK audit passed with the
same 111-input/107-project and contract counts as source40. All mapped original
runtime names were independently verified. Staging preserved tree structure and
377 assembly/satellite overlays, and the unchanged SDK-built MCP add-in loaded
all 407 types with the host's binding configuration.

A whole-project comparison against source39 found zero normalized differences
across 193,872 method bodies in 107 physical projects. It checks scoped signatures,
flags, IL, referenced locals and exception handlers; this does not prove equality
of all attributes/resources or replace unexercised runtime checks. The first
comparison attempt used an incorrect path for an x86 output; the corrected
comparison discovers the unique Release/framework output within each project.
Evidence: `ets63-api-source-validation42`, `ets63-source42-alias-audit1.json`,
`source42-bodycheck2`, `ets63-source42-staging.log` and
`ets63-source42-sdk-load.log` under `D:\knx_analysis`.

Validation on 2026-09-10 used original SDK callers and separate rebuilt trees.
The 6.3 regression build and live test passed before the 6.4 live test.

| Check | ETS 6.3 source36 | ETS 6.4 source11 |
| --- | --- | --- |
| Batch inputs | 111 | 176 |
| Managed projects compiled | 107 | 172 |
| Native inputs retained | 4 | 4 |
| SDK contract audit differences | 0 | 0 |
| Staged assemblies and satellites | 377 | 397 |
| Unchanged MCP add-in types loaded | 407 | 410 |
| Live project | test-mcp / P-6790 | isolated copy of test-mcp / P-6790 |

Both live copies opened with Chinese UI and MCP 4.13.1 ready. Read-only SDK
checks returned project details, all 29 devices, 502 group addresses and sampled
communication-object metadata. The 6.4 test also read sampled parameter metadata.
The 6.4 run used copied project/product stores and a temporary settings profile;
cleanup verified the original profile and 1,877 original data-file hashes.
Both ETS processes and test daemons exited, and installed add-ins were restored.

The 6.4 export includes compatibility assemblies in explicit physical contexts.
Its source map contains twelve method aliases, ten derived from reviewed 6.3
reference candidates. Runtime names/signatures are restored by the metadata task.
Shared satellite paths select the original destination's version independently
of project order. Reference-only projects are recorded separately when staging.

Standalone SDK loading must use the host's actual configuration and binding
redirects. An exact-identity probe without ETS6N.exe.config failed equally on
pristine and rebuilt 6.4; applying that configuration resolved the dependency.

Evidence folders on the validation machine are `D:\knx_analysis\ets63-source36-live1`,
`D:\knx_analysis\ets64-source11-live1`, and the corresponding source-validation,
SDK-audit and staging manifests. Source trees are `D:\git\ets63-api-source36`
and `D:\git\ets64-api-source11`.

These are compilation, metadata and exercised-runtime milestones. They do not
prove equivalence of every body/custom attribute, every third-party app, password
projects or physical KNX operations. The test project was not password protected.
Compiler warnings and existing development-add-in/network/MyKNX warnings remain.

## Source-only parameter map follow-up

The subsequent source37 (6.3) and source12 (6.4) builds added a descriptive
`schemaVersionValue` argument alias to the schema helper. The full 6.3 build and
expanded audit passed before starting 6.4. Both retained the same input/project
and staging counts above, with zero SDK contract differences. The expanded audit
also checks enum/string constants and event accessor associations.

Both staged trees loaded the unchanged SDK-built MCP add-ins (407/410 types),
and the automation patcher recognized their hash-verified rebuilt provenance.
Comparisons against the live-tested source36/source11 Common assemblies found no
normalized method-body differences across 1,305 methods in 6.3 and 1,814 in 6.4.
Those comparisons include scoped signatures, method flags, IL, locals and
exception handlers; they do not compare every attribute or resource.

Latest source trees: `D:\git\ets63-api-source37`, `D:\git\ets64-api-source12`.
Staged trees: `D:\knx_analysis\ETS6.3_source37`, `D:\knx_analysis\ETS6.4_source12`.
Evidence: `ets63-api-source-validation37`, `ets64-api-source-validation12`,
`ets-sdk-loader3` and `parameter-alias-bodycheck1` under `D:\knx_analysis`.
These follow-up trees were validated offline; the live checks above remain tied
to source36/source11. Original installations and project data were not changed.

The generic de4dot NameCandidates scanner independently recovered ten of the
reviewed 6.4 method aliases using 6.3 as reference. Its guarded source-map converter
also exported and rebuilt the four affected modules with zero SDK differences.
It retains relative physical module contexts and rejects ambiguous candidates;
it does not claim to recover every original obfuscated name.

## Explicit string extraction follow-up

Compilation of the earlier API-preserving trees did not prove string readability:
their ObjectModel source still called the decoder with encrypted literals.
The fresh 6.3 batch `ETS6.3_api_preserved4` explicitly requests static string
extraction while retaining the default public API preservation policy. It processes
86 protected modules and copies 442 other managed modules unchanged.

Comparison with the original pure decoder implementations verified 117,047
strings across 43 assemblies, including all six `AddCertificate` strings. The
ETS6C check requires a genuinely x86 probe; force a rebuild and check its PE flags
when changing architecture, rather than trusting an output directory name.
Evidence: `D:\knx_analysis\ets63-all-string-parity4-final.json` and the x86 rerun
`ets63-ets6c-string-parity4b.log`. The checks verify literals at the known decoder
call sites; they do not establish equivalence of every method body.

Source39 uses this decoded batch. Before rebasing the source-name map hash, each
mapped token, MVID, expected name, signature and parameter name was verified.
All 107 managed projects compile (111 inputs including four native dependencies),
and the SDK audit reports zero differences across 13,776 types, 102,871 methods
and 17,406 fields. Source: `D:\git\ets63-api-source39`; build/audit evidence:
`D:\knx_analysis\ets63-api-source-validation39`. This is offline evidence;
the live results above remain tied to their original source versions.

The decoded 6.4 source14 follow-up also compiles all 172 managed projects
(176 inputs) with zero SDK differences across 24,866 types, 183,360 methods and
32,667 fields. Its main input is `ETS6.4_api_preserved5`; legacy references use
the separately decoded `ETS6.3_compat_api2` tree. The batch must bind the legacy
`UserControls_patched` component to its 6.3 signing dependency context. Omitting
that context correctly rejected publication instead of substituting the root
assembly. Staging retained 397 assemblies/satellites and loaded all 410 MCP types.
Evidence: `D:\knx_analysis\ets64-api-source-validation14`,
`ets64-source14-staging.log` and `ets64-source14-sdk-load.log`.

Original-decoder parity checks cover 93,181 strings in 26 identified Dotfuscator
decoder assemblies in that main tree, and 120,291 strings in 44 assemblies in
the compatibility tree. These overlapping tree counts are separate, not additive.
The refreshed cross-version scan still produces ten reviewed candidates; decoding
the strings did not establish additional unique method matches.

Source39 subsequently passed a fresh isolated 6.3 launch test: Chinese UI opened
test-mcp, MCP 4.13.1 registered 151 tools, and project/device/group-address,
communication-object and parameter-metadata reads succeeded. Original profile,
installed add-in and all 1,877 original project/product file hashes were restored
and verified after ETS closed. Evidence: `D:\knx_analysis\ets63-source39-live1`.
This project is unprotected; password-project and broader runtime equivalence
remain separate requirements.

Source14 then passed the corresponding fresh 6.4 launch test against separately
copied stores. Chinese UI opened test-mcp, and the original-SDK MCP returned all
29 devices plus sampled group addresses, communication objects and parameter
metadata. The initial dispatcher snapshot timed out during copied-product
conversion; the completed launch and subsequent reads succeeded. After ETS
closed, original add-in/profile hashes and all 1,877 original data hashes matched.
Evidence: `D:\knx_analysis\ets64-source14-live1`. This remains an unprotected
test-mcp check; the earlier P-01C0 password-project failure is not covered by it.

### Reported P-01C0 parsing exception

The user's supplied log fails while constructing `SpaceUsageId` from
`tag:livingRoom`, before the later null-reference errors. The current P-01C0
building store contains that value and similar semantic tags. A focused runtime
probe of the original ETS 6.3 `IdCache.Create<SpaceUsageId>(string)` and source39's
rebuilt equivalent accepts `SU-1` in both and rejects `tag:livingRoom` and
`tag:kitchen` with identical `ArgumentException` messages. Evidence:
`D:\knx_analysis\ets63-spaceusage-parity1\original.txt` and `rebuilt.txt`.

The 6.4 BuildingPart reader explicitly accepts semantic location tags as well as
legacy `SU-` identifiers; the 6.3 reader requires the latter. This isolates the
reported identifier rejection from the decompilation pipeline. No original
project data or parser behavior was altered. It does not test the complete
password-opening flow, nor prove when the project's stored format changed.

### Password fixture control follow-up

The isolated `ets63-password-live1` source39 run failed while creating a new
password-protected project. An original-binary control with automation hooks
(`ets63-original-control1`) reproduced the same creation exception and incomplete
store. This control is instrumented, so the result does not establish a defect
in untouched vendor ETS.

Setting a password on the control's disposable test-mcp copy through the project
details UI completed and temporarily reported `password_protected: true`.
However, its persisted project metadata remained byte-identical to the original
unprotected input. A separate source39 launch (`ets63-protected-open1`) reopened
that copy with `password_protected: false`. This is a failed fixture-persistence
check, **not** successful password-opening validation. The partial newly created
project was excluded from the second test.

The source contains signing-identity checks and a save-suppression state; their
runtime involvement is unverified. Metadata inspection found the same expected
public-key token on the shell, ViewModel and ObjectModel in all three trees, so
a changed token on those files does not explain the result. No integrity or
password checks were changed. Further persistence diagnosis needs a valid
control before any recompiler fix can be justified. Both runs restored the
original profile/add-in and verified all 1,877 original data hashes.

Follow-up inspection found `ExtendedLogging version: 1.23.3.9.23` in both
the original-control and source39 test startup logs. The shell adds `3.9` when
`ExtendedLoggingAvailable` is reported as licensed; this produces the state
that suppresses `Project.Save` in both versions. This supplies a concrete host
configuration explanation for the missing persistence, rather than evidence
of a decompiler-only failure. The automation bridge now exposes that state and
rejects create/duplicate/import before calling ETS when saving is suppressed.
Its fixture regression passed 93 checks, including suppression, recovery, and
continued open/close access (`automation-save-suppression-regression2.log`).
The new guard has not yet been restaged into an ETS live runtime. Password
round-trip validation still requires a host configuration that permits saving.

DevKit provenance subsequently confirmed that `ETS6.3_orig` already contains an
injected `KnxVirtualDongle.Vd`; its default optional-feature array includes
`ExtendedLoggingAvailable`. Source39 preserves that input behavior. The current
VirtualDongle runtime source excludes the feature, and source14's injected runtime
has no such static-initializer literal. Evidence:
`D:\knx_analysis\ets-devkit-runtime-provenance1.json`. Consequently, the 6.3
directory named `orig` must not be described as an untouched vendor distribution.
The patcher now reports this distinction in profiles and instrumentation manifests.

### Corrected 6.3 persistence and password round trip

`ets63-saving-live1` used a separate `ETS6.3_source39_live2` runtime. The only
DevKit method changed from source39 was the injected runtime's static initializer:
`ExtendedLoggingAvailable` was removed from its optional-feature array. The
VirtualDongle preparation script preserved all other entries and method bodies;
applying it to corrected source14 produced a byte-identical copy. The rebuilt
baseline directories and original inputs were not overwritten.

The corrected 6.3 process reported `save_suppressed: false` and startup state
`1.23.1.23`. It created `test-mcp-password-qa` (P-07CC), wrote the complete project
store, and opened it with the supplied disposable-test password. After exiting
and starting a new ETS process, the project remained protected, prompted for
its password, and opened successfully after entering it. Evidence is in
`D:\knx_analysis\ets63-saving-live1`: creation/open action results, persisted
file hashes, restart snapshot, and `projects-password-opened.json`.

This validates a newly created password project on rebuilt 6.3. It does not
establish compatibility of the user's separate P-01C0 data or cover a 6.4
password round trip. The original profile/add-in and all 1,877 tracked original
data hashes were restored; the test-only workspace was backed up and removed.

### Source aliases on state-machine methods

`Invoke-SourceStateMachineAttributeAudit.ps1` accepts `-DnlibPath`,
`-ExportDirectory` and a new `-OutputDirectory`. It checks state-machine attribute
type resolution in every physical exported project, including platform-specific
output directories. External state types are counted separately and are not
resolved through another project's dependency context.

`Invoke-SourceStateMachineAliasRegression.ps1` maps async and iterator methods
on a generic declaring type, including a generic async method. It checks readable
source aliases, execution, original method/state-machine reflection names and
attributes, unchanged input bytes, and byte-stable incremental builds with one
and four export workers. `state-owner-regression2` passed these runtime checks.

The fixture also maps static event handlers used with ordinary and generic
delegate types. It requires emitted delegate caches, checks their restored
target names, and verifies subscription/removal by execution. The cache-name
restorer follows the compiler's `ldftn/newobj/dup/stsfld` pattern in a generated
cache type, preserves the ordinal, resolves fields within the physical module,
and updates both metadata-table and method-body field references. This addresses
the cache-name mismatch behind two source17 body differences in the online-catalog view model's
constructor/disposal paths; full application validation is still required after
the focused `delegate-cache-regression4` pass.

The subsequent source45 6.3 validation compiles all 107 projects and passes the
SDK contract audit, original-name audit, and all 3,005 local state-machine
attribute checks. Its 193,872 method bodies match the live-tested source44
without any additional name normalization. Staging preserves all original input
hashes and the complete tree with 377 assembly/satellite overlays; the unchanged
official-SDK MCP add-in loads 407 types. The WPF type/event alias regression also
passes on this tool build, including opaque resource preservation and incremental
rebuilds. The full 6.4 source18 run begins only after those 6.3 checks pass.

The expanded 496-method 6.4 map compiled in source16 and passed the SDK contract
audit (172 projects, zero issues). Comparing its bodies with source14 exposed
generated state-machine names containing source aliases. Runtime metadata
restoration now restores those owner names through their state-machine attribute
associations while retaining compiler ordinals and generic arity. Raw iterator
bodies also retain the original association attribute; only reconstructed
async/iterator syntax can rely on the compiler to recreate it. These focused
checks do not replace the next full 6.3-first, then 6.4 validation.

The constructor-lambda regression additionally checks the compiler's dot-to-hyphen
rule (`<.ctor>b__N` becomes `<<-ctor>b__N>d...`). Source43's negative audit found
32 unresolved state types; corrected source44 resolves all 3,005 associations
across 107 projects, with no external associations. Source44 compiles, passes
the SDK and original-name audits, and stages 377 assemblies/satellites with
input hashes and the complete physical tree preserved. Comparing its 193,872
method bodies with source39 leaves no normalized differences after 70 explicitly
verified generated-owner name corrections. The correction ledger uses unchanged
owner signatures and matching attributes, preserving compiler ordinals and
arity; it does not ignore arbitrary names or instruction differences.

In `ets63-source44-live1`, the isolated runtime launched in Chinese and opened
the copied test-mcp project through the unchanged official-SDK add-in. The MCP
reported 29 devices and 502 group addresses. An SDK project-number update
survived a complete ETS process restart. The copied P-07CC protected project
then prompted for its password and opened with protection intact. The runtime
reported saving enabled. After shutdown, original profile/add-in hashes and
all 4,811 recorded original data-file hashes matched their backups. Only the
new test workspace was removed, after backing it up.

### Rebuilt 6.4 password round trips

`ets64-password-live1` used source14 in a separate runtime with the current
automation bridge, copied stores and the original-SDK 6.4 MCP build. Saving was
enabled. The verified protected 6.3 fixture P-07CC opened with its password in
6.4, survived a process restart, prompted for the password, and reopened with
protection intact. The original 6.3 fixture hashes remained unchanged.

The test then created a separate protected project, `test-mcp-password64-qa`
(P-0836, stored version 6.4.8718.0). Its complete store was written, and it also
prompted for and accepted its password after another ETS process restart.
`projects-password-opened.json`, `projects-password64-opened.json`, the snapshots,
action results and persisted file hashes record both checks. The official-SDK
MCP independently returned the copied test-mcp project's 29 devices and 502
group addresses. Early dispatcher timeouts occurred during startup; subsequent
project operations succeeded without restarting that process.

Original profile/add-in and all 1,877 original data hashes were restored after
ETS closed. Two test-only workspace files were backed up and removed. This
extends runtime evidence to new protected-project persistence and cross-version
opening; it does not claim that arbitrary project formats or every method body
have been validated.
