# Anonymous types in retained signatures

Run `Invoke-AnonymousSignatureRegression.ps1` with `-DnSpyConsole` and a fresh `-OutputDirectory` (.NET 10 SDK and .NET Framework 4.8 required).

The emitter changes an internal factory's return signature from object to its actual anonymous generic type. This models signatures left behind when obfuscation prevents closure/lambda reconstruction. Anonymous syntax cannot represent that return type. The exporter must retain the concrete class and constructor calls. Ordinary anonymous types confined to method bodies still use anonymous syntax.

The original and rebuilt executables check properties, equality, hash consistency, formatting and a separate local-only anonymous type. One- and four-worker exports must both build and run, produce identical source, and leave input hashes unchanged. Retaining the compiler-generated hash implementation also exercises unchecked constant multiplication.

The current detection covers local TypeDef signatures in non-generated owners and non-generated methods, recursively including generic arguments and element types. It does not claim recovery of all escaped types across arbitrary external references or all compiler-generated closure patterns.
