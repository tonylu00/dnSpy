# Hidden protected method restoration

Metadata can bind a protected base method from a nested helper even when a
derived method hides its name. C# cannot always express that binding with a base
cast because protected receiver restrictions apply. SDK source exports generate
unique protected compilation stubs in the original declaring type. The build
task redirects calls to the original method and removes the stubs. Original
names, visibility and bodies remain intact.

Allocation is deterministic across export workers and confined to the local
module. Imported member names are reserved. Generic method specifications and
generic declaring types are supported when the compiler references the exact
declaring type; unexpected inherited generic owners fail explicitly. Cross-module
protected stub coordination is not implemented. Async stubs are emitted without
the async modifier so no disposable stub state machine is generated.

Run `Invoke-ProtectedCallRegression.ps1 -DnSpyConsole <exe> -OutputDirectory
<new folder>`. It checks protected calls, generic owners and methods, asynchronous
behavior, reflection flags and stub removal through one/four-worker exports.
Both rebuilt clients and unchanged binary clients execute against the rebuilt
library, and original input hashes must remain unchanged.

Source exports retain explicit static extension calls to preserve the selected
container across assemblies. `Invoke-ExtensionBindingRegression.ps1` covers
competing extensions in separate binary dependencies as well as receiver
conversions, generic inference, null behavior and debugger spans.
