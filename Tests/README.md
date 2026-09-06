# Decompiler regression checks

After building `dnSpy.sln` in Release, run these scripts with a new output folder
outside the repository (so repository build settings do not affect the fixtures):

```powershell
.\Tests\Invoke-LogicalChainRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-logical-check
.\Tests\Invoke-ProjectExportRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-export-check
.\Tests\Invoke-AsyncLayoutRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-async-check
.\Tests\Invoke-NullableAliasRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-nullable-check
.\Tests\Invoke-ValueTaskRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-valuetask-check
.\Tests\Invoke-ApplicationConfigRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-binding-check
.\Tests\Invoke-DelegateReceiverRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-delegate-check
.\Tests\Invoke-CollisionNamesRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-collision-check
.\Tests\Invoke-SourceMetadataRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-source-metadata-check
.\Tests\Invoke-LoopControlRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-loop-control-check
.\Tests\Invoke-LargeMethodRegression.ps1 `
  -DnSpyConsole "$PWD\dnSpy\dnSpy\bin\Release\net10.0-windows\dnSpy.Console.exe" `
  -OutputDirectory D:\knx_analysis\dnspy-large-method-check
```

The first test compiles long AND/OR expressions, exports them, rebuilds them and
checks 1,538 evaluation paths, including operand order and every short-circuit
position. It reproduces the stack failure seen in ETS's generated XML serializer.
The second checks a consumer without `TargetFrameworkAttribute` and an implicit
conversion used as an array receiver. Both original and rebuilt programs execute.
The async fixture reproduces reordered suspension/resume blocks and unrelated
branches between resume and result collection. It checks completed, suspended,
faulted and cancelled tasks, the unrelated branch, and finally execution before
and after export and recompilation. Two-await cases exercise backward layouts,
shared state dispatch, every completed/suspended combination and both failure
positions. An unsupported kickoff pattern checks that its referenced state-machine
implementation remains in the export.
Incomplete reconstruction also retains the original implementation. The tests
cover side effects before await result collection, nested iterator cleanup,
early disposal, captured owner references and valid names for retained helpers.
Awaited finally blocks check cleanup after success, failure and cancellation,
suspended cleanup, and cleanup exceptions taking precedence over body exceptions.
Captured delegate caches retain their original zero-initialized storage.

The nullable fixture emits IL that copies a local's managed pointer across a
branch. It checks present and absent values and ensures the source is evaluated
once. The ValueTask fixture checks typed results from ordinary and configured
awaits, actual suspension, and exception behavior. It uses the framework support
libraries from dnSpy's `net48` build; `-TasksExtensionsPath` can select another copy.
The delegate fixture reproduces an object-typed field invoked without `castclass`
in the input IL. It checks the returned value, invocation count and null failure
before and after export and recompilation.

The application configuration fixture checks a signed library version redirect
and a transitive dependency exposed by an overload in the newer library. The
original and rebuilt consumer must select the same overload and return the same
result. It also verifies traditional project references and rejects redirects
whose token, culture or version range does not match. For application exports,
pass `--app-config path\Application.exe.config`
to use that host's binding redirects. Without this option, normal assembly
resolution remains unchanged. File dependencies needed for overload resolution
are included in both SDK and traditional project exports.

The collision fixture rewrites metadata with repeated generic and parameter names,
including nested types, constraints, abstract methods and interfaces. The exported
declarations and uses must agree, compile and preserve each argument's behavior.
The source metadata fixture checks readonly conversion arguments, readonly reference
methods and indexers, mutable reference writes, tuples, static operations on dynamic
fields and stack allocation sizes. It removes the unsafe marker before export and
checks both execution and readonly return metadata after recompilation. Compiler
reserved attributes are projected into C# syntax rather than emitted as illegal
explicit attributes; the input assembly metadata is not changed.
It also covers private nested types exposed by helper signatures, guarded
constructor argument preparation (including null rejection and side-effect order),
and conversions through interfaces with substituted generic type arguments.
Additional emitted IL checks cover zero-initialized local storage and generic
`isinst`/unboxing for reference, value and nullable types, including failure and
single-evaluation behavior. Null arguments retain their selected overload and
generic arguments, while non-disposable enumerators retain conditional cleanup.
Catch variables used after their handler retain their outer lifetime. Filtered
handlers check exception identity and both accepting and rejecting the filter.

The loop-control fixture checks `continue` paths that skip a final assignment,
increment or condition. Moving that operation into a `for`, `foreach` or
`do/while` header must preserve the original control flow. Nested loops are
included so a continue in an inner loop does not change the outer loop's behavior.

The large-method fixture generates hundreds of live locals and repeated object
initializers with shared references and conditional values. Original and rebuilt
programs verify side-effect order, values and reference identity. Export time is
recorded in `timing.json`; use `-Count 4000` for a larger performance comparison.
There is no machine-dependent timing threshold in the regression.

The expression-evaluator submodule and the `RoslynVersion` package setting must
use compatible Roslyn internals. Updating only the package can break dnSpy's build.
