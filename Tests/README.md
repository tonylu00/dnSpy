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
```

The first test compiles long AND/OR expressions, exports them, rebuilds them and
checks 1,538 evaluation paths, including operand order and every short-circuit
position. It reproduces the stack failure seen in ETS's generated XML serializer.
The second checks a consumer without `TargetFrameworkAttribute` and an implicit
conversion used as an array receiver. Both original and rebuilt programs execute.

The expression-evaluator submodule and the `RoslynVersion` package setting must
use compatible Roslyn internals. Updating only the package can break dnSpy's build.
