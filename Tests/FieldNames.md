# Runtime field names after C# compilation

CLR fields can share names with other fields of different types, methods,
properties or their declaring type. The source exporter allocates stable C#
aliases, accounting for inherited fields and members. `MetadataFieldNames`
shares this allocation between decompilation and metadata restoration.

SDK exports include `.dnspy-metadata/FieldNames.cs`. Each instruction identifies
the source owner, assembly name/version/culture, unique alias and original raw
name bytes. Runtime definitions and field MemberRefs regain the input names.
Generic owners and inherited receiver references are included. Definitions keep
their types, flags, storage, offsets and values; reference assemblies retain the
source aliases for dependent compilation. Conflicting instructions fail rather
than choose a name by assembly simple name alone.

Run `Invoke-FieldCollisionRegression.ps1 -DnSpyConsole <exe> -OutputDirectory
<new folder>`. It verifies duplicate typed fields, property/method/type
collisions, inherited generic storage, reflection, unchanged binary callers,
one/four-worker source determinism and incremental library/PDB hashes. The
existing metadata-only string-field and WPF type-alias regressions also exercise
the shared post-compilation task.

The fixture also checks generic types whose input names omit the usual arity
suffix, including nested generics. Type restoration uses the actual C# arity
when locating source aliases, then restores the input spelling. A retained helper
and a newly compiled lambda helper deliberately compete for the same name: the
retained input type keeps its name, and only the new compiler-generated helper
receives a unique name. Unchanged binary calls, lambda behavior and reflection
check that the two helpers remain distinct and that runtime type names are unique.

This restores explicit field aliases. It does not promise that compiler-synthesized
members or reconstructed automatic properties have identical layouts; those need
separate metadata/behavior audits.
