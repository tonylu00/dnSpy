# ETS native records and event chains

This batch adds **611 descriptive source aliases** in one full export/build per
version. The review starts with bit fields, fixed-width records, arithmetic,
dictionary lookups and system-library calls, then follows their native API callers
and event chains. Names describe observed behavior; they are not claims to recover
the vendor's original identifiers. Naming remains in progress.

| New aliases | ETS 6.3 | ETS 6.4 | Total |
| --- | ---: | ---: | ---: |
| Methods | 248 | 152 | 400 |
| Types | 38 | 21 | 59 |
| Parameters | 92 | 60 | 152 |
| Total | 378 | 233 | 611 |

## Reviewed behavior

- Packed calendar and UTC-offset fields, time settings, USB identity, version,
  configuration flags, log records, hash and signature buffers.
- Managed record readers corroborated by readable 6.4 properties and constructors.
- Native delegate lookup, call lifetime counters, status handling, USB enumeration,
  device configuration, device logs and UTC/local device clock readers.
- PE directory and section helpers, import/export resolution, base relocation,
  and narrowly defined PE/ELF header predicates.
- Change/error payloads, subscription methods, lifecycle publishers and the
  callbacks that forward them through NativeManager.

For example, the 6.3 NativeManager constructor now connects
`SubscribeNativeLibraryLoading` to `ForwardNativeLibraryLoading`, using
`DeviceChangeEventHandler` and `DeviceChangeEventArgs`. References across the
exported project use the same aliases. Original file paths remain stable.

Meaningful existing methods and properties, including 6.3 `Invoke<T>` and 6.4
NativeManager events, retain their names. Unknown USB flag bits and uncertain
ELF layout decisions remain deferred. The PE layout decision still depends on
process bitness, the local date decoder still applies the stored signed offset,
and lifecycle payloads still obtain the existing Windows load counter. This pass
does not change those behaviors or execute native load/write operations.

## Validated outputs

| | ETS 6.3 | ETS 6.4 |
| --- | --- | --- |
| Source tree | `D:\git\ets63-name-self08` | `D:\git\ets64-name-self04` |
| Cumulative map | `D:\knx_analysis\self-name-review06\names63-final.xml` | `D:\knx_analysis\self-name-review06\names64-final.xml` |
| Comparison baseline | `D:\git\ets63-name-self07` | `D:\git\ets64-name-self03` |
| Managed projects | 111 | 178 |
| Physical mapped modules | 6 | 29 |
| Cumulative types / methods / parameters | 94 / 641 / 279 | 34 / 806 / 127 |
| Compared method bodies | 194,229 | 385,538 |
| Layout types / instance fields / fixed arrays | 27 / 89 / 16 | 26 / 85 / 16 |

Both exports and full solution builds passed. The cumulative maps retain every
previous edit, add every reviewed physical identity, and need no collision
suffixes. SDK contracts, original runtime name restoration, state-machine
attributes, native layouts and complete compiled method-body comparisons all
report **zero issues or differences**. Body comparisons use no owner-name
alignment or name normalization. Physical project sets are unchanged.

Layout checks cover packing, class size, field order, field signatures, flags,
offsets and fixed-array marshal metadata. Per-version validation JSON files
record exact report paths, hashes, totals, exporter hash and tool commits.

This was an offline pass; ETS was not launched. The comparison baselines are
previous validated source builds from inputs that already contain restoration
and test patches. These checks do not establish equivalence with an untouched
vendor installation or replace a live ETS test.

## Apply the batch

Use the preceding cumulative maps from `self-name-review05`. Mapping edits and
preflight use the portable C#/.NET NameCandidates tool:

```text
dotnet NameCandidates.dll --update-map ets63-reviewed.json base63.xml names63.xml update63.json
dotnet NameCandidates.dll --check-map names63.xml check63.json
dotnet NameCandidates.dll --update-map ets64-reviewed.json base64.xml names64.xml update64.json
dotnet NameCandidates.dll --check-map names64.xml check64.json
```

Review rows bind each symbol to its physical module, token, input hash, MVID and
signature. The companion evidence records the proposed name, parameter roles,
review order, source hashes and independently checked counterparts. Apply the
whole map during export with the complete input set and dependency contexts;
dnSpy's build task restores original runtime identities for binary callers.
