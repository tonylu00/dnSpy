# Alias reference preflight

This portable .NET 8 command checks managed cross-assembly references before an
expensive source export. It reuses dnSpy.Console's physical-input, compatibility
context and application-config resolvers. It reads metadata without loading the
analyzed assemblies as executable code or changing their names.

```text
dotnet build Tests/SourceAliasReferences/SourceAliasReferences.csproj -c Release
dotnet Tests/SourceAliasReferences/bin/Release/net8.0/SourceAliasReferences.dll inputs.json names.xml references.json --contexts contexts.xml --config application.exe.config --asm-path dependencies
```

`inputs.json` is the same array of physical input paths used for export. Repeat
`--asm-path` for additional dependency folders. `--contexts` and `--config` are
optional; use the same values as the planned export. `--no-gac` disables GAC
search. Inputs and the map remain unchanged, and the report must be a new file.

Map entries are checked against the actual module hash, MVID, method/type token,
original name and complete signature. If strict method resolution fails but a
same-name/signature-shaped candidate on a mapped declaring type exists, the
report identifies it and exits nonzero. Comparison without scopes is used only
for this diagnostic; it never binds or renames a reference. Supplying a wrong
vendor assembly with a same-named type cannot make the check pass.

The command also checks global type aliases against declarations and referenced
types in each project's reachable physical dependency graph. A new global name
such as `DeviceCertificate` can shadow an existing imported
`Knx.Ets.Xml.ObjectModel.DeviceCertificate`, even when the alias is unique inside
its own assembly. The report identifies both physical types before export.
Choose a distinct alias, such as `DevKitCertificate`, when this check fails.
This is a conservative name-shadowing check, not a complete C# binding proof.
It follows the exact assembly resolver, including transitive input dependencies,
so independent compatibility deployments do not collide merely by sharing an
assembly identity or alias. Namespaced/nested alias ambiguity and all possible
language lookup rules still require compiler validation.

This complements NameCandidates `--check-map`: that command checks map validity;
this one checks references with the complete export inputs and dependency paths.
It currently examines member references with a resolved, directly mapped
declaring type. It does not replace complete compiler, body, runtime-name or live
behavior checks, and cannot prove all unresolvable declaring types are unrelated.

The ETS 6.3 Common/ViewModel case fails with two references when the exact
`System.Net.Http, Version=4.2.0.0` dependency is absent. Supplying that reference
assembly resolves both through the `netstandard` facade with strict identity
matching; there is no need to ignore assembly scopes. Reference assemblies are
analysis/build inputs, not replacements for deployed runtime libraries.

The metadata-only regression also checks two physical libraries sharing one
assembly identity, wrong-vendor payloads, global type shadowing, distinct
replacement aliases, disjoint deployments with identical aliases, and stale
type-map entries:

```text
dotnet run --project Tests/SourceAliasReferencesRegression -c Release -- path/to/SourceAliasReferences.dll new-regression-directory
```

The command and regression passed on Windows. Their code uses portable .NET
APIs; macOS/Linux execution has not been performed locally.
