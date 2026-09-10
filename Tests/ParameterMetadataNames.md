# Parameter names in source and rebuilt metadata

C# export allocates distinct names for duplicate or invalid method arguments and
generic parameters. Nested generic redeclarations bind by position even when
their metadata names differ from the enclosing type. Existing meaningful names
remain available; generated suffixes avoid both existing names and generic names
in scope. Indexer accessors share a single source parameter list.

SDK export now emits `dnSpy.metadata.parameter-names.v1` instructions for names
which source projection changes. The build task restores the original UTF-8
metadata names by generic position or parameter sequence. Runtime assemblies
retain reflection-visible names; compiler reference assemblies keep their valid
source identifiers for cross-project compilation. The restoration does not
change parameter types, constraints, values or method dispatch.

Delegates carry instructions on their type for runtime-generated methods,
including constructor and BeginInvoke/EndInvoke parameter names. Ordinary
constructors carry instructions on a parameter because ObfuscationAttribute is
not valid on constructor declarations. A named return row on a parameterless
constructor uses its declaring type as the carrier. Consumed instructions are
removed from runtime output. Duplicate or invalid instruction positions fail
the build instead of silently targeting another member.

`Invoke-InvalidTypeNamesRegression.ps1` builds an IL-mutated fixture with
duplicate generic/argument names, different nested redeclaration names,
constructors, indexers, event accessors, delegates and named return rows. It
executes original and rebuilt programs, compares exact parameter/generic names,
checks one/four-worker source determinism, incremental output hashes and input
preservation. `Assert-ParameterMetadataNames.ps1` is the reusable exact-name
comparison for fixtures whose original definitions are all retained.

`--source-name-map` also accepts custom parameter aliases on ordinary nonvirtual
methods, including generic methods. The same runtime restoration path preserves
their original metadata names. See `SourceNameMap.md` for guarded sequence/name
mapping and `Invoke-SourceParameterAliasRegression.ps1` for caller/runtime checks.

The ETS 6.3 source26 export rebuilt all 76 managed projects with zero errors.
An expanded public-contract audit found 265 parameter-name differences in the
previous source25 output and zero in source26. It also checked names and flags
for 9,603 types, 69,790 methods and 13,761 fields plus generic parameter names.
This is metadata and compilation evidence, not complete method-body equivalence
or a live test of source26.
