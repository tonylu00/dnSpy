# Protected batch source regression

Run NETReactorSlayer.Tests with `--reactor <installed-reactor-console> <new-folder>`
to create and process both method-encryption-only and method/control-flow fixtures.
Then run:

```powershell
./Tests/Invoke-ReactorBatchSourceRegression.ps1 -DnSpyConsole <console.exe> -ReactorTestDirectory <reactor-test-folder> -OutputDirectory <new-source-folder>
```

The test exports every managed assembly in each processed tree, including the
separate compatibility copies, compiles the complete solution, and executes both
applications. Their different expected exit results (100 and 120) check that
compatibility implementations were not merged. The fixture also exercises strings,
generic calls, enum values, named attributes and interface dispatch. Non-managed
payload files are excluded from the compiler input list; Slayer's separate batch
test verifies preservation of those files and the directory tree.

A fresh run on 2026-09-10 exposed a source-projection gap: an ordinary interface
method named `Bad Virtual` retained an escaped space in C#. Method aliases now
cover invalid ordinary names, not only compiler-generated declarations. Resolved
base/interface contracts supply the same source alias to implicit implementations;
the metadata task restores original names in runtime output. Conflicting interface
aliases are rejected rather than silently choosing a contract.

Both protected scenarios now export, compile and execute in both physical contexts.
The existing duplicate type/generic/parameter regression also passes with one/four
workers and exact parameter-name restoration. Evidence is under
`D:\knx_analysis\reactor-final-audit1`, `reactor-final-source-audit4` and
`invalid-interface-names-regression1`. Subsequent full 6.3 source45 and 6.4
source18 builds pass; their contract, body and live validation evidence is
recorded in `EtsSourceValidation.md`.
