# Runtime generated-method names

SDK exports retain generated methods that have source aliases, including methods
which another assembly or reflection can call. A shared allocation assigns stable
source names. Virtual override families share an alias after substituting generic
base arguments; field allocation reserves these aliases to avoid hidden members.

`.dnspy-metadata/MethodNames.cs` records resolved owner/assembly context, source
alias and original raw name. The build task restores definitions, MemberRefs and
generic method specifications. Method-group targets follow the same restoration.
Reference assemblies retain source names. Native import entry points are emitted
explicitly when a managed method gets an alias.

Restoration can expose collisions with newly generated compiler methods. New
nonvirtual helpers receive distinct runtime names and retain their own bodies and
callers. A record's synthesized clone is replaced by the retained input clone,
preserving the original override family and copy-constructor behavior. Other
ambiguous or unsupported virtual collisions fail explicitly.

Run `Invoke-GeneratedMethodRegression.ps1 -DnSpyConsole <exe> -OutputDirectory
<new folder>`. It verifies overloads, readable API names, generic owners and
methods, abstract overrides across assemblies, inherited field collisions, instance/static method
groups, reflection and native entry-point metadata. Record `with` expressions
exercise polymorphic cloning and copy-constructor side effects. A compiler base
wrapper deliberately collides with a retained method whose behavior differs.
The test runs rebuilt and unchanged binary clients, compares source across one
and four workers, checks incremental DLL/PDB hashes, and preserves input hashes.
