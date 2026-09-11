# Personally reviewed ETS method names

This batch contains 100 accepted method aliases: 66 in ETS 6.3 and 34 in
ETS 6.4. Each evidence entry records the inspected implementation, behavioral
reason, token, signature, input hash and MVID. These are inferred names, not a
claim to have recovered original source identifiers. They cover LicenseManager
and the 6.3 URI, lock-count and task helpers; thousands of other methods remain
unreviewed.

The 6.3 executable copies have separately pinned entries despite their shared
assembly identity. The 6.4 additions target ETS6N.exe only; `deferred.json`
records why transfer to ETS6C.exe needs more evidence. Meaningful public SDK
overloads and property accessors keep their existing contracts.

`ets63-reviewed.json` and `ets64-reviewed.json` are executable NameCandidates
inputs, with populated `NewName` values. Use the corresponding validated export
map as the base for `--update-map`; do not merge by assembly simple name or
replace existing type/parameter rows. The captured input roots refer to this
validation machine and exact binary generation.

```text
dotnet NameCandidates.dll --update-map ets63-reviewed.json base63.xml new63.xml merge63.json
dotnet NameCandidates.dll --update-map ets64-reviewed.json base64.xml new64.xml merge64.json
```

Current output locations:

| Item | Path |
| --- | --- |
| ETS 6.3 source | `D:\git\ets63-name-self02` |
| ETS 6.4 source | `D:\git\ets64-name-self01` |
| Merged maps and audit evidence | `D:\knx_analysis\self-name-review01` |
| Exporter with closure-name restoration | `D:\knx_analysis\self-name-review01\runtime\dnSpy.Console.exe` |

The naming tests exposed a restoration gap for compiler-generated lambdas and
local functions under aliased owners, including nested async state types.
The C# SDK build task now restores these names and their local references with
physical-module and compiler-generated-scope checks. The regression fixture
executes captured async lambdas, ordinary lambdas, local functions, generic
types/methods, event subscription/removal, reflection checks and incremental
builds with one and four export workers.

Full exports build all 111 managed projects in 6.3 and 178 in 6.4. Their SDK,
state-machine and mapped-name audits pass. Method-body comparisons use
separate copies of the baseline source built with the same corrected task:
this distinguishes the new aliases from fixes to generated names that older
baseline builds retained incorrectly. No ETS application was launched or
installation replaced for this naming batch.

The controlled comparisons passed without name normalization: 194,229 method
bodies in 6.3 and 385,538 in 6.4, with zero differences. `validation.json`
records the counts, map/report hashes and evidence locations. The portable
alias checker also rejected a disposable binary with one deliberately changed
method name. This is an offline naming milestone, not complete naming of ETS.
