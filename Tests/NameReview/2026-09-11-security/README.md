# Reviewed security and ZIP names

This batch adds 98 source aliases: 21 types, 28 methods and 49 parameters. The
6.3 changes cover 20 types, 16 methods and 33 parameters; the 6.4 changes cover
one type, 12 methods and 16 parameters. Names come from inspected implementations
and, for many 6.3 security classes, independently inspected readable 6.4
counterparts. Inferred names describe behavior; they are not a claim to recover
the original source identifiers.

Examples include `DirectAccessKeyProvider`, `Pbkdf2DeriveBytes`,
`EtsExportZipper`, `DerivePbkdf2Sha256PasswordBytes`,
`TryExtractNestedZipWithKey`, `ReadProjectNameFromProjectInformation`, and
`CreateValidProjectCertificateWithRetries`. Meaningful public overload names
remain intact. All accepted aliases preserve original runtime metadata names.

The reviewed JSON inputs carry exact physical module paths, input hashes,
MVIDs, tokens, signatures and original names. `ets63-evidence.json` and
`ets64-evidence.json` record the reasoning. Parameter edits use real metadata
sequences. NameCandidates validates and merges these inputs without hand-editing
XML; its C# implementation runs on Windows, macOS and Linux.

```text
dotnet NameCandidates.dll --update-map ets63-reviewed.json base63.xml new63.xml report63.json
dotnet NameCandidates.dll --update-map ets64-reviewed.json base64.xml new64.xml report64.json
```

Use the cumulative maps from the preceding reviewed batch as the bases. Current
machine paths, counts and verification reports are recorded in `validation.json`.
The complete cumulative maps are also captured in each source export as
`dnspy-source-name-map.xml`.

Validated source outputs are `D:\git\ets63-name-self03` and
`D:\git\ets64-name-self02`. All 111/178 managed projects build. Comparisons of
194,229/385,538 compiled method bodies against the preceding validated exports
report zero differences without name normalization. SDK, mapped runtime-name
and state-machine checks also report zero issues. The input and rebuilt Common
assemblies in both versions each pass five synthetic password-key behavior
checks. These isolated execution checks do not replace a live ETS project test.

The full ETS test found that protected-call compilation stubs were resolved
before source aliases, causing an invalid-stub error. dnSpy now restores member
names first. The focused regression reproduces the old failure and verifies
the correction for ordinary/async/generic methods, type/parameter aliases,
unchanged binary callers and incremental builds with one and four workers.

`deferred-families.json` records reviewed interface/virtual method families that
still need atomic family mapping support. They have not been partially renamed.
The earlier 6.4 ETS6C string ambiguity remains deferred. This batch does not
finish naming ETS, launch the application or replace an installed runtime.
