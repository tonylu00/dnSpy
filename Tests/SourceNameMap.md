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

Version 1 supports non-generic types, ordinary fields, ordinary nonvirtual methods and complete
implicit interface/virtual override families. Constructor renames, unsupported accessors,
runtime methods, unsupported native imports, explicit `MethodImpl` declarations and static virtual
contracts remain unsupported.
Choose type/method aliases unique across their module, including original
type/member names, namespace segments, parameters and generic parameters.
Alias swaps and invisible Unicode format characters are rejected. These
conservative limits avoid ambiguous compiler binding and metadata restoration.

Static nongeneric P/Invoke declarations with a complete `ImplMap` and no body
support reviewed managed method/parameter aliases. The emitter keeps the native
library, entry point, calling convention, flags and marshaling. If the managed
name changes, even an originally implicit entry point is emitted explicitly.
Runtime restoration changes managed definitions/references only.
`NativeImportAliasRegression` consumes `native-imports/names.xml` from the
portable NameCandidates suite and checks the actual parser, attribute emitter
and signature-qualified restoration instructions without executing native code:

```sh
dotnet run --project Tests/NativeImportAliasRegression -c Release -- /path/to/fixture/native-imports/names.xml
```

Managed instance constructors and type initializers accept parameter/local-only
rows with no `NewName` attribute on the method. The parser uses the same scoped
eligibility rule as NameCandidates; `.ctor` and `.cctor` remain unchanged.
Native/runtime constructors and constructor method aliases remain rejected.
The portable fixture consumes the NameCandidates suite's scoped map and checks
both physical compatibility copies, source aliases and invalid rename/stale rows:

```sh
dotnet run --project Tests/ConstructorScopeAliasRegression -c Release -- /path/to/fixture/constructor-scope/names.xml /path/to/new-report-directory
```

For an interface or virtual family, generate the map with NameCandidates
`--review-families` and `--update-map`. Select a descriptive `NewName` on one
reviewed member; the updater expands the actual metadata family and allocates
one alias for all its declarations, implementations and overrides. Each resulting
method row carries a `ContractFamily` identifier. dnSpy recomputes that graph
using the complete export inputs and validates all members and aliases before
registering any names. Member, type and field aliases are reserved in their C#
declaration scope — the declaring type, its base chain and its nested declarations —
so unrelated types may both use one name and an unmodified declaration still blocks
it. The only sharing allowed beyond that is the single alias of one fully validated
family. Generic interface/base argument
substitution, inherited implementations and separate overloads are supported;
ambiguous or external contracts are blocked. Physical duplicate assembly
identities retain their dependency contexts.

Field rows use `Token`, `ExpectedName`, `Signature`, and `NewName` in the same
format. Generate them with NameCandidates `--review-fields` and `--update-map`.
Field names are reserved in their declaring class and inheritance chain, so
unrelated classes can both use `logger`. Original member names are also reserved;
name swaps and shadowing inherited storage are rejected. Ordinary fields and
enum literals are supported; global/runtime-special fields and fields requiring
separate RVA/compiler-controlled/nonliteral-constant restoration are blocked.
The existing `FieldNames.cs` instructions restore runtime names and references
by source owner and resolved assembly identity. See `FieldNames.md`.

`SourceFieldAliasRegression` consumes `fields.xml` from the portable
NameCandidates regression and checks the actual exporter map parser, field
allocation, generic inherited receiver instructions and literal storage.
`ApplicationNameGraphRegression` optionally accepts the `SourceAliasReferences`
DLL and verifies that a wrong-vendor field signature is reported rather than
bound to an alias in a same-name compatibility assembly. These are metadata
checks; consolidated exported-source and runtime validation is still required.

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

Method rows also accept source-only local variable aliases:

```xml
<Method Token="0x06000002" ExpectedName="b"
        Signature="System.Int32 Example.Api::b(System.Int32)">
  <Local Index="0" ExpectedType="System.Int32" NewName="runningTotal" />
</Method>
```

`Index` is the zero-based slot in the method body's variable list, and
`ExpectedType` must equal that variable's dnlib `TypeSig.FullName` exactly. The
row is rejected when the index or the type does not match, so a stale map fails
loudly instead of renaming an unrelated variable. `NewName` must be a valid
identifier that does not collide with the method's parameters (original or
aliased), generic parameter names in scope, or other local aliases of the same
method; invisible Unicode format characters and swaps are rejected. The alias
wins over debug-symbol names; when the alias is unusable the exporter falls back
to the existing name generation. Locals are source-only names: local variables
are not persisted in metadata, so no runtime restoration is required. The
application naming pass records local aliases in the same staged maps as member
and parameter decisions.

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
where required by the source map's declaration-scope collision guard. This validation
does not replace a full-tree build or application launch with the expanded map.
