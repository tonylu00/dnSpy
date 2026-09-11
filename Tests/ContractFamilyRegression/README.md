# Contract family source-name regression

Run with .NET 8, a built dnSpy console and the portable NameCandidates DLL:

```text
dotnet run --project Tests/ContractFamilyRegression/ContractFamilyRegression.csproj -c Release -- <dnSpy.Console.exe> <NameCandidates.dll> <new-output-directory>
```

The C# runner creates Contracts, Implementation and Client assemblies, builds a
family review map from metadata, exports with one and four workers, and rebuilds
the generated sources. Both rebuilt callers and unchanged original callers must
retain generic interface dispatch, inherited implementations, virtual overrides,
overloads and async results. Reflection must retain original method/parameter
names; async, iterator and generic async state fields must also retain the
original parameter names, including the iterator's initial argument copy.
Incremental output hashes and input hashes must remain stable. An
incomplete family map must fail export. Each child command has a separate log.

This end-to-end fixture executes .NET Framework 4.8 assemblies and dnSpy, so it
requires Windows and the .NET Framework targeting pack. Family discovery, map
editing and the de4dotEx `tests/NameCandidates` metadata regression are .NET 8
code that runs on Windows, macOS and Linux without PowerShell.
