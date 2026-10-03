# Compilation framework inference

Run this portable console project with `dotnet run --project Tests/CompilationFrameworkInferenceRegression/CompilationFrameworkInferenceRegression.csproj -c Release`.

The helper consumes dependencies already resolved in the physical compatibility context. It preserves explicit target metadata, bounds cyclic traversal and infers a newer .NET Framework target from transitive untouched binaries only for modules lacking explicit target metadata. The exporter rejects nearest-version/name resolver fallbacks as inference evidence. Root and CV copies are tested independently; inference never writes input metadata.
