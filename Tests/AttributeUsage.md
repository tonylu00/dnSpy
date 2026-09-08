# Attribute usage restoration

Run `Invoke-AttributeUsageRegression.ps1` with `-DnSpyConsole` and a fresh `-OutputDirectory`. Requires the .NET 10 SDK and .NET Framework 4.8 targeting/runtime support.

The fixture compiles an attribute applied to a property in its own library and a method in a separate executable. The emitter then restricts its original metadata to class targets. The original executable runs successfully, but directly decompiled C# fails with CS0592.

SDK exports relax ValidOn for compilation and carry an instruction restoring its original value after CoreCompile. Reference assemblies retain the relaxed rule for dependent source projects. Runtime assemblies recover the original rule, retain AllowMultiple and Inherited, and contain no restoration markers. This does not remove attribute applications or change their arguments.

The regression builds and runs exports with one and four workers, checks both attribute applications and their labels, verifies the restored usage rule, compares generated source across worker counts, and checks that inputs remain unchanged. The normal decompiler view and non-SDK exports retain original usage rules.
