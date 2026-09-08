# TypeSpec-encoded struct constraints

Run `Invoke-TypeSpecConstraintRegression.ps1` with `-DnSpyConsole` and a fresh `-OutputDirectory` (.NET 10 SDK and .NET Framework 4.8 required).

The emitter wraps ordinary generic constraint references in simple TypeSpec signatures, for both a generic class and a generic method. The original assemblies remain executable. Before the fix, export produces invalid C# such as `where T : struct, ValueType`.

The decompiler recognizes a simple TypeSpec-encoded System.ValueType as redundant only when NotNullableValueTypeConstraint is already set. It retains other constraints and does not turn a standalone ValueType constraint into struct. C# compilation regenerates the equivalent ValueType constraint, although it may encode it as a TypeRef rather than the original TypeSpec.

The regression builds and runs one- and four-worker exports, checks generic parameter flags and interface/base constraints, rejects reference types, nullable types and a struct that violates the interface constraint, and verifies that an unconstrained-by-interface struct still works with the generic method. Generated source must be deterministic and input hashes unchanged.
