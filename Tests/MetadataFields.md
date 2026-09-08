# Metadata-only field restoration

Run `Invoke-MetadataFieldsRegression.ps1` with `-DnSpyConsole` and a fresh `-OutputDirectory`. Requires the .NET 10 SDK and .NET Framework 4.8 targeting/runtime support.

The emitter adds private and compiler-controlled string fields to a static class and a delegate. Ordinary C# cannot declare these fields. The unmodified executable verifies delegate invocation and interop, mutable delegate field storage, reflection flags, and the original InvalidOperationException from GetRawConstantValue for the unusual constants.

SDK source exports carry explicit restoration instructions and a generated MSBuild task. The regression rebuilds with one and four export workers, checks runtime behavior and exact constant/name metadata using dnlib, verifies PDB sequence points, and checks incremental rebuilds leave the executable and PDB unchanged. Cases include negative signed constants, null, embedded NUL and Unicode text, and a raw invalid UTF-8 field name.

The generated build step requires unsigned compiler output. Only unreferenced private/compiler-controlled string fields on static classes or delegates, without custom attributes, marshalling, RVA data or explicit field offsets, are currently selected. Unsupported metadata is not silently discarded. The normal decompiler view and non-SDK exports retain field declarations.
