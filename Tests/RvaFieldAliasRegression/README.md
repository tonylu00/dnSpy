# RVA field source aliases

Build the portable fixture with `dotnet build Tests/RvaFieldAliasRegression/RvaFieldAliasRegression.csproj -c Release`. It consumes the native updater and the actual exporter map parser. Unsupported storage shapes remain blocked.

Run `Tests/Invoke-RvaFieldAliasRegression.ps1` with `-DnSpyConsole`, `-FixtureTool` (the portable fixture DLL) and a fresh `-OutputDirectory`. Build the real ILSpy plugin before the console used for this check. The script creates synthetic inputs only; it never modifies ETS source or binaries.

The execution fixture covers primitive and explicit-layout RVA fields, a nested type alias, original reflection names and direct field references, exact field flags/types/constants/bytes, unchanged binary callers, one/four-worker source determinism, unchanged inputs and stable incremental DLL/PDB hashes.

The same portable tool supports `--compare <checked-map.xml> <dnspy-export-map.xml> <fresh-report.json>`. After compiling that export, it compares the selected physical modules and mapped runtime types, fields and parameters against their original identities. This is metadata/storage evidence, not application behavior or unchanged-App compatibility proof.
