# Layout audit for source-aliased types

This .NET 8 metadata-only audit checks sequential and explicit-layout types
selected by an exported SourceNameMap. It compares original and rebuilt type
flags, packing/class size, instance field count/order, field signatures/flags,
offsets and fixed-array marshal size/element type. It reports unsupported or
changed marshal contracts as issues rather than silently accepting them.

```text
dotnet run --project Tests/SourceAliasLayouts -c Release -- <built-export-directory> <new-report.json>
```

Keep the export's input paths accessible and run SourceAliasContracts first to
validate map identities, hashes and names. This supplements SDK and method-body
audits: neither alone verifies private packed-record layout. It never loads the
analyzed assemblies for execution. The command is C#/.NET, with no PowerShell
dependency; compiling ETS itself remains a Windows operation.

The 2026-09-11 ETS 6.3 and 6.4 leaf-first naming batches each passed for ten
renamed layout types, eighteen instance fields and eight fixed arrays. Full
report paths and hashes are recorded with the naming dataset.
