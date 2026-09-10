# Descriptive source names with original runtime contracts

`dnSpy.Console --source-name-map names.xml -o <new-folder> <assemblies>`
exports C# SDK projects using explicit descriptive names. References between
exported projects use those names too. The generated metadata restoration step
restores the original names in compiler references and runtime assemblies, so
existing SDK callers do not need a corresponding binary rename. Combine with
`--public-sign` when the host requires original public-key identities; see
`PublicSigning.md` for its signing limits.

This source-only format is separate from the binary `NameMap` format:

```xml
<SourceNameMap Version="1" InputDirectory="D:\analysis\input">
  <Module Path="Library.dll" Mvid="EXACT-MODULE-GUID" Sha256="EXACT-FILE-SHA256">
    <Type Token="0x02000002" ExpectedName="a" Signature="Example.a"
          NewName="SchemaVersionExtensions" />
    <Method Token="0x06000001" ExpectedName="b"
            Signature="System.String Example.a::b(System.Int32)"
            NewName="ToVersionString" />
  </Module>
</SourceNameMap>
```

Use the original input definition's dnlib `FullName` for `Signature`; escape XML
attribute characters. Each module is bound to a physical input path, MVID and
SHA256, and each definition to a token, exact name and signature. Assemblies
with the same assembly identity in different folders require separate module
rows. A map from another build is rejected rather than matched by filename or
assembly name. The accepted map is saved as `dnspy-source-name-map.xml` beside
the export manifest.

Version 1 supports non-generic types and ordinary nonvirtual methods. It rejects
constructors, accessors, runtime/PInvoke methods, virtual/override methods and
parameter rows. Choose aliases unique across their module, including original
type/member names, namespace segments, parameters and generic parameters.
Alias swaps and invisible Unicode format characters are rejected. These
conservative limits avoid ambiguous compiler binding and metadata restoration.
Names containing characters that cannot be represented in XML attributes are
not supported by this version.

Run `Invoke-SourceNameMapRegression.ps1 -DnSpyConsole <exe>
-SigningKey <development-key> -OutputDirectory <new-folder>`. It verifies
descriptive source declarations, cross-project calls, restored runtime names,
an unchanged signed binary caller and rejection of stale or colliding maps.

ETS 6.3 validation exported and built all 76 managed projects. A mapped schema
helper used descriptive source names for one type and five methods, retained
its original runtime names, and matched all five operations across nine schema
versions. The public-contract audit compared 9,603 types, 69,790 methods and
13,761 fields with zero differences. These checks do not prove equivalence of
all method bodies or arbitrary third-party SDK applications.
