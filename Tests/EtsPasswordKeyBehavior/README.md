# ETS password-key behavior checks

This C# harness executes the selected Common assembly's password-key helper on
synthetic values, without starting ETS or opening a project. It checks four
password/salt vectors against .NET's PBKDF2-SHA256 implementation: ordinary text,
an empty password, Unicode with compatibility-normalized salt, and an embedded
null with an empty salt. A fifth check verifies the null-password contract.

The ETS implementation invokes Windows BCrypt, so these execution checks require
Windows. The metadata inventory and map-editing tools remain portable.

```text
dotnet build Tests/EtsPasswordKeyBehavior/EtsPasswordKeyBehavior.csproj -c Release
dotnet Tests/EtsPasswordKeyBehavior/bin/Release/net8.0/EtsPasswordKeyBehavior.dll <Common.dll> <dependency-root> aqu aci <new-report.json>
```

For the reviewed 6.3 generation, the original runtime type/method are `aqu.aci`.
For 6.4, pass `Knx.Ets.Common.Security.Encryptor GetPasswordKey`. Run the input
and rebuilt assemblies in separate processes, with their matching dependency
root. The report pins the tested assembly's SHA-256 hash. Successful isolated
checks do not establish that every ETS project operation works.
