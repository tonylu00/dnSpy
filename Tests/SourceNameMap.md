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

Version 1 supports non-generic types, ordinary nonvirtual methods and complete
implicit interface/virtual override families. Constructors, accessors,
runtime/PInvoke methods, explicit `MethodImpl` declarations and static virtual
contracts remain unsupported.
Choose type/method aliases unique across their module, including original
type/member names, namespace segments, parameters and generic parameters.
Alias swaps and invisible Unicode format characters are rejected. These
conservative limits avoid ambiguous compiler binding and metadata restoration.

For an interface or virtual family, generate the map with NameCandidates
`--review-families` and `--update-map`. Select a descriptive `NewName` on one
reviewed member; the updater expands the actual metadata family and allocates
one alias for all its declarations, implementations and overrides. Each resulting
method row carries a `ContractFamily` identifier. dnSpy recomputes that graph
using the complete export inputs and validates all members and aliases before
registering any names. The only exception to module-wide alias uniqueness is
the shared alias of one fully validated family. Generic interface/base argument
substitution, inherited implementations and separate overloads are supported;
ambiguous or external contracts are blocked. Physical duplicate assembly
identities retain their dependency contexts.

`ContractFamilyRegression` exports and builds a multi-assembly fixture with
one/four workers, then runs rebuilt and unchanged binary callers through generic,
virtual, inherited, overload and async dispatch. It also checks original reflection
names, parameter names, incremental hashes and incomplete-family rejection.

Ordinary method rows also accept source-only parameter aliases:

```xml
<Method Token="0x06000001" ExpectedName="b"
        Signature="System.Int32 Example.Api::b(System.Int32,System.Int32)">
  <Parameter Sequence="1" ExpectedName="a" NewName="tens" />
  <Parameter Sequence="2" ExpectedName="b" NewName="units" />
</Method>
```

The method's `NewName` is optional when parameter rows are present. Sequence is
one-based in the signature, excluding `this`; an existing parameter metadata row
and its exact original name are required. Return rows and absent metadata rows
are rejected. Parameter aliases must be distinct from original argument names,
other aliases and generic parameter names in scope. Swaps and collisions with
mapped type/method aliases are rejected. Generic methods are supported.

Source bodies and declarations use the aliases together. The existing parameter
metadata restoration instructions preserve original reflection-visible names in
runtime output; compiler reference assemblies retain source names for compilation.
Explicit parameter aliases also restore the compiler's captured parameter fields
in async and iterator state machines, including iterator initial-argument copies.
Only fields on the method's proven local generated state type are changed.
Constructed generic field references follow those restored definitions. Ordinary
automatic parameter sanitization retains its existing behavior.
`Invoke-SourceParameterAliasRegression.ps1` checks combined method/parameter maps,
parameter-only maps, generic methods, one/four workers, unchanged callers, runtime
reflection names, input preservation and invalid-map rejection.

BAML connector export uses the same method-name lookup as C# when reconstructing
ordinary event attributes, attached events and style `EventSetter` handlers.
This keeps mapped handler declarations and XAML references consistent without
changing the original runtime method names. Run `Invoke-BamlConnectorsRegression.ps1`
with `-SourceAliases` to check mapped XAML, compilation, event execution and
reflection names with one and four workers; omit the switch to check the default
export path.

Use `-TypeAliases` to cover a mapped WPF root class and child control together
with mapped handlers. The exporter retains original identities for resource
association, emits source names in `x:Class` and type references, and leaves WPF's
temporary markup-compilation assembly in source form. Final runtime restoration
also rewrites scoped BAML type records using the existing BAML reader/writer,
which recalculates deferred-record offsets. Other resource entries are copied as
raw resource data without deserializing their values. The regression checks both
construction and resource-URI loading, original type/method reflection names,
unrelated resource content and byte-stable incremental builds.

Resource restoration checks the declared resource-reader header before scanning
for BAML. Containers requiring a different reader, including preserialized ResX
data, remain byte-identical and their reader/converter types are not loaded.
Pass `-PreserializedResourceLibrary <System.Resources.Extensions.dll>` to the
connector regression to include an opaque converter resource and verify this
preservation behavior alongside the BAML changes.

On 2026-09-10, parameter aliases on the schema-version helper in real ETS 6.3
and then 6.4 Common assemblies exported and compiled with zero errors. Both
public SDK contract audits reported zero differences, including parameter names.
These isolated exports used their respective `ETS6N.exe.config` binding redirects.
The existing duplicate generic/argument-name regression also passed with one/four
workers. These targeted checks do not replace the separately recorded whole-tree
and live validation; no new whole-tree runtime was staged for this change.
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

Cross-version validation also transferred ten descriptive method names from a
6.3 reference into 6.4 source. Candidate comparison required a unique matching
declaring type, signature, normalized instruction sequence, locals, exception
regions and symbolic assembly scopes (ignoring version). Two additional matches
were excluded when scope comparison failed. This is candidate evidence, not
general proof of behavior equivalence; review names before creating a map.

Together with the two schema-method aliases, the expanded map rebuilt five
modules. The SDK contract audit reported no differences, and a separate metadata
check found all twelve mapped methods under their exact original runtime names
and signatures. Repeated candidate names received distinct descriptive aliases
where required by the source map's module-wide collision guard. This validation
does not replace a full-tree build or application launch with the expanded map.
