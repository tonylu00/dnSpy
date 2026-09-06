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
```

The first test compiles long AND/OR expressions, exports them, rebuilds them and
checks 1,538 evaluation paths, including operand order and every short-circuit
position. It reproduces the stack failure seen in ETS's generated XML serializer.
The second checks a consumer without `TargetFrameworkAttribute` and an implicit
conversion used as an array receiver. Both original and rebuilt programs execute.
The async fixture reproduces reordered suspension/resume blocks and unrelated
branches between resume and result collection. It checks completed, suspended,
faulted and cancelled tasks, the unrelated branch, and finally execution before
and after export and recompilation.

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

The expression-evaluator submodule and the `RoslynVersion` package setting must
use compatible Roslyn internals. Updating only the package can break dnSpy's build.
