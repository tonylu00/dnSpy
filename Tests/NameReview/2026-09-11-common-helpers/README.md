# ETS Common helpers and device event dispatch

This batch adds **489 descriptive source aliases** collected before the full
exports: **222 methods, 25 types and 242 parameters**. Review starts with system
library calls, predicates, storage getters and callbacks, then follows their
callers. Names describe observed behavior; they are not claims to recover the
vendor's original identifiers. Naming remains in progress.

| New aliases | ETS 6.3 | ETS 6.4 | Total |
| --- | ---: | ---: | ---: |
| Methods | 175 | 47 | 222 |
| Types | 23 | 2 | 25 |
| Parameters | 202 | 40 | 242 |
| Total | 400 | 89 | 489 |

## Reviewed behavior

- Enumeration, cardinality, partitions, collection mutation, stack pop, optional
  values, observable mirroring, and item property-change subscriptions.
- HTTP request logging, response/error handling, JSON reads, downloads, stream
  progress, headers, URL encoding and XML loading with a disabled resolver.
- Deferred cache persistence, captured work callbacks, completion/error handling,
  file cache cleanup, hydration and retry delay advancement.
- Property storage and notification, command/subscription disposal, enum/field
  presentation, schema file paths and anonymous-type detection.
- Trace comment encryption/decryption, salt and cipher-envelope framing helpers.
- Async delegate capability probing and synchronous device/package dispatch
  settings; existing license getter roles corroborated by named 6.4 properties
  and 6.3 caller assignments.

For example, cache flow now reads `GetPendingCacheWrite`,
`ScheduleCapturedCacheWrite`, `PersistCapturedCacheValueAsync`,
`CompleteCacheWriteResult` and `FinishAndDisposeCachesAsync`. The collection
observer uses `SubscribeToItemChanges`, `OnObservedItemPropertyChanged` and
`UnsubscribeFromItemChanges`. All references in the exported project use the
same source aliases; build tasks restore original runtime identities for SDK
and binary callers.

Existing meaningful APIs remain unchanged. Review records preserve details such
as collection duplicate behavior, non-truncating OpenWrite, cancellation tokens
not forwarded by existing fallback paths, retry multiplication before the first
wait, and malformed Base64 throwing outside an existing catch. No behavior fixes
or license changes are part of this batch.

Three proposed generic type names are stored in `ets63-deferred.json` and
`ets64-deferred.json`, **not applied**: `DeferredStorageCacheDecorator` and the
nested `PendingCacheWrite` types. The mapping tool currently blocks generic type
aliases. Their supported method aliases are included. Ambiguous schema version
getters and unreviewed virtual contract families remain unchanged.

## Validated outputs

| | ETS 6.3 | ETS 6.4 |
| --- | --- | --- |
| Source tree | `D:\git\ets63-name-self10` | `D:\git\ets64-name-self05` |
| Cumulative map | `D:\knx_analysis\self-name-review07\names63-final.xml` | `D:\knx_analysis\self-name-review07\names64-final.xml` |
| Comparison baseline | `D:\git\ets63-name-self08` | `D:\git\ets64-name-self04` |
| Managed projects | 111 | 178 |
| Physical mapped modules | 6 | 29 |
| Cumulative types / methods / parameters | 117 / 816 / 481 | 36 / 853 / 167 |
| Compared method bodies | 194,229 | 385,538 |
| Layout types / instance fields / fixed arrays | 28 / 92 / 16 | 26 / 85 / 16 |

Both final source trees build successfully. All previous map edits are retained,
and every reviewed physical identity is added. The mapper made 12 deterministic
method suffix adjustments in 6.3 and one parameter suffix adjustment in 6.4;
the validation JSON records each requested and applied name.
SDK contracts, original runtime names and parameter restoration, state-machine
attributes, native layouts and complete compiled method-body comparisons report
**zero issues or differences**. Body comparisons use no owner-name alignment or
name normalization. Physical input/MVID/project-path sets are unchanged.

Duplicate Common assemblies are resolved through the export manifest and actual
input path/MVID, not the generated folder name. For this batch the main Common
projects are `Knx.Ets.Common.3` in 6.3 and `Knx.Ets.Common.4` in 6.4. Compatibility
copies retain their independent identities. Each validation JSON records report
paths, hashes, totals, exporter hash and tool commits.

This was an offline pass; ETS was not launched. Comparisons use previous validated
source builds from inputs containing earlier restoration and test patches. They
do not establish equivalence with an untouched vendor installation or replace a
live ETS test.

## Problems caught and fixed

The first 6.3 build exposed two unresolved cross-assembly alias references:
ViewModel uses `System.Net.Http.HttpResponseMessage`, while Common refers to that
type through `netstandard`. Supplying the exact `System.Net.Http, Version=4.2.0.0`
reference assembly fixed strict resolution. The new portable
`Tests/SourceAliasReferences` preflight reproduces the two errors in under five
seconds and passes with the dependency supplied. It retains physical compatibility
contexts and does not replace strict binding with a comparison that ignores scopes.
Its synthetic regression accepts distinct same-identity deployments and rejects
a same-named payload from the wrong vendor assembly.

The first 6.4 compiled-body audit found four closure-field reference differences.
Parameter aliases had renamed compiler-generated display-class fields while only
state-machine fields were restored. Commit `0f02be777` restores fields proven to
capture the original parameter or its hoisted copy. The capture regression fails
against the old exporter and passes with the fix, including generated and
unchanged callers, nested/generic/async/iterator captures and incremental builds.

6.3 therefore used two full exports/build attempts, and 6.4 used one. The closure
fix was applied by refreshing the generated build task, rebuilding Common in
each tree, then performing a final incremental solution build. It required no
additional full export. Validation records distinguish the exporter used for
source generation from the updated build task and ready-to-use exporter under
`D:\knx_analysis\self-name-review07\runtime`.

The added HTTP reference also let the decompiler infer `using` in one unmapped
6.3 uploader method, changing its compiled disposal form. A focused two-second
uploader export with its original dependency paths reproduced the baseline source
exactly. That file was refreshed and its small project rebuilt. The final body
report rechecks this binary and reuses the other 110 passing reports only after
verifying both binary hashes for every report. SDK and state-machine audits were
also repeated after the refresh. `tool-validation.json` records this context
workaround and the regression controls.

## Apply the batch

Use the preceding cumulative maps from `self-name-review06`. Mapping edits and
preflight use the portable C#/.NET NameCandidates tool:

```text
dotnet NameCandidates.dll --update-map ets63-reviewed.json base63.xml names63.xml update63.json
dotnet NameCandidates.dll --check-map names63.xml check63.json
dotnet NameCandidates.dll --update-map ets64-reviewed.json base64.xml names64.xml update64.json
dotnet NameCandidates.dll --check-map names64.xml check64.json
```

Review rows bind symbols to physical module, token, input hash, MVID and signature.
Evidence records names, parameter roles, review order, source hashes and checked
counterparts. Apply the entire cumulative map during export with all inputs and
dependency contexts. Do not add the deferred generic type rows to the map.
