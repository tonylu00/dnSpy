# Verify rebuilt source aliases

This .NET 8 command reads metadata on Windows, macOS or Linux. It checks every
mapped type, method signature and parameter name against the rebuilt assembly.
It resolves each physical project from the export manifest, including separate
same-identity components and architecture-specific output directories. Inputs
and rebuilt binaries are never executed or modified.

```text
dotnet run --project Tests/SourceAliasContracts/SourceAliasContracts.csproj -c Release -- ./built-export ./new-alias-report.json
```

The export must contain `dnspy-export-map.xml`, `dnspy-source-name-map.xml`, and
exactly one matching Release output per mapped project. Input hash, MVID,
token, name and signature must match the map. Reports use a new path; an
existing report is never overwritten. Exit 0 means all mapped runtime names
were restored, 1 means missing or ambiguous output names, and 2 means invalid
inputs or another incomplete audit. This checks metadata restoration; use the
SDK-contract, state-machine and method-body audits for the corresponding
additional guarantees.
