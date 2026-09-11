# Orphan SpecialName source aliases

Some obfuscated assemblies retain the SpecialName method bit after removing
the associated property or event. Source maps now permit these ordinary method
declarations while keeping actual accessors, operators and runtime methods
guarded. Recompilation restores original runtime names, parameters and flags.

Run on Windows with .NET Framework 4.8 and the .NET 8 SDK, using a fresh folder:

```text
dotnet run --project Tests/OrphanSpecialNameRegression -c Release -- <dnSpy.Console.exe> <NameCandidates.dll> <new-output-folder>
```

The fixture exports with one and four workers and executes both rebuilt and
unchanged original clients. It checks getter/setter and event-like methods,
static methods, SpecialName flags, parameter restoration, attached property
and operator behavior, input hashes and stable incremental build outputs.
Per-command logs are retained in the output folder. It passed on 2026-09-11;
this is a focused regression, not a live ETS test.
