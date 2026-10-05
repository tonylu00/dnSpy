# Automatic property runtime storage

```text
dotnet run --project Tests/AutomaticPropertyStorageRegression -c Release -- <native-console> <fresh-directory>
```

Requires Windows and .NET Framework 4.8 for fixture execution. The C# harness
creates its own generic fixture and uses dnlib to give three compiler fields
short names, then exports and builds through the native dnSpy pipeline with
explicit field aliases. It never modifies ETS inputs.

The original and rebuilt executables test 128 accessor/reflection cases,
readonly and nonserialized flags, thread-static isolation, and original field
names. Each executable reads the other's serialized payload. The test also checks
metadata flags, consumed restoration markers, unchanged input bytes, and stable
incremental output. The exporter keeps readable auto-properties and marks their
compiled storage directly; restoration updates generic MemberRefs as well as the
field definitions.
