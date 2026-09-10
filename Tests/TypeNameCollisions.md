# Reversible C# type aliases

CLR metadata allows a type to share its name with a method, and a nested type to
share a name with a method in its parent. C# rejects these declarations even when
the method overload signatures differ. `MetadataTypeNames` allocates stable,
module-wide `Type_<RID>` aliases for these types and for invalid identifiers.
Declarations, constructors and resolved references use the same allocation.
This does not rename overload or virtual method families.

SDK exports write `.dnspy-metadata/TypeNames.cs`. The existing metadata build task
restores original type names in runtime definitions and external references,
including nested and generic references, after compilation. Reference assemblies
retain C# aliases so project references compile against the source contract.
Instructions use base64 names plus assembly name, version, culture and full source
type name. Input resolution supplies the dependency context; a simple assembly
name alone is never the lookup key. Strong-name signing remains unsupported by
the metadata restoration target.

Run `Tests/Invoke-TypeNameCollisionRegression.ps1 -DnSpyConsole <exe>
-OutputDirectory <new folder>`. It checks overloaded calls, nested generic types,
reflection and an unchanged binary caller against rebuilt output, at one and four
export workers. `Invoke-InvalidTypeNamesRegression.ps1` covers invalid metadata
names and positional generic/parameter binding.

The ETS 6.3 compatibility-preserving batch (`ETS6.3_api_preserved2`) exported 76
managed projects and four retained native dependencies. Its fresh build went from
1,498 declaration errors to 123 expression/binding errors after this change.
This is a compilation milestone, not a claim of a successful full rebuild or a
runtime validation of that rebuilt tree.
