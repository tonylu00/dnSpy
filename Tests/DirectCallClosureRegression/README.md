Run with a freshly built ILSpy plugin and Console in the same runtime directory:

```powershell
dotnet run --project Tests/DirectCallClosureRegression -c Release -- <dnSpy.Console.exe> <new-work-directory>
dotnet run --project Tests/DirectCallClosureCacheRegression -c Release -p:RuntimeDirectory=<runtime-directory> -- <fixture Library.dll>
```

The export test builds an original .NET Framework library and client, exports
only the library with an aliased public async owner, and compiles native exporter
output. The original client executes against each rebuilt library without being
rewritten. Workers 1 and 4 must produce identical source; an incremental build
must preserve the restored DLL hash.

The fixture checks repeated synchronous and asynchronous calls, shared mutable
captures, default capture values, cancellation, original public metadata and
generated async owner names. Observable constructors, receiver escape, recursive
helpers, an actual parameter-name collision, unmarked containers, identity-sensitive
helper bodies and ref parameters must retain their implementation types.

The companion test exercises concurrent first publication of target and cycle
caches, collection of finished module graphs and pooled-transform budget reset.
Its optional fixture input also checks 17 eligibility/rejection scenarios, including
entry jumps that bypass allocation or callable initialization, and verifies rejected
ASTs and original IL remain unchanged.

The transform emits one named `Func`/`Action` callable in its lexical owner using
the existing lambda and async reconstruction pipeline. This AST generation has no
local-function declaration node. It deliberately retains unsupported generic,
recursive, escaping, identity-sensitive or ambiguous cases. These focused tests
do not establish complete ETS or third-party App runtime compatibility.
