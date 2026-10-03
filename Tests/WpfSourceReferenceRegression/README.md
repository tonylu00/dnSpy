# Readable XAML and original runtime names

```
dotnet run --project Tests/WpfSourceReferenceRegression -c Release -- <dnSpy.Console> <new-work-directory>
```

This test requires Windows because it executes WPF. Its runner, mapping and process
control use .NET APIs. Build both the BAML plugin and console before running it.

A library's original control type is referenced only by the client's resource dictionary.
The exporter gives it a readable source alias. The test builds both exported projects,
checks that the reference assembly retains the alias while the runtime library restores
the original type, loads the rebuilt BAML and checks control behavior. An incremental
build must preserve the output hash; original inputs must also remain unchanged.

This catches two independent gaps: markup compilation must use source reference assemblies,
and aliases used only inside BAML need restoration instructions even without CLR TypeRefs.
