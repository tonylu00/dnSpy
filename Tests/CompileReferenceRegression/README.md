Run with .NET 10 on Windows, Linux or macOS:

```
dotnet run --project Tests/CompileReferenceRegression -c Release -- <fresh-directory>
```

Exercises the actual exported build task and refresh implementation. It preserves distinct
physical references, different signing identities and cultures, refuses to guess between
explicit versions, and reports missing preserved binaries. Refresh changes only generated
compile-reference support, leaves source and unrelated projects untouched, and is idempotent.
It also executes the inline task under legacy MSBuild and exercises WPF references whose
original metadata has been stripped, using the preserved physical-contract item list.

The real ETS solution build supplies the integration check for SDK/WPF NuGet target ordering.
Exported legacy projects must not require SDK-only package targets.
