# Generated closure ownership

Run the end-to-end regression with a built console and a fresh work directory:

```
dotnet run --project Tests/ClosureOwnerRegression -c Release -- <dnSpy.Console> <new-work-directory>
```

The fixture assigns the same readable alias to legal overloads with different original
names. It covers captured lambdas, a forwarding overload without a lambda, async owners
and a generic local function on a generic type. The test exports and builds source,
executes original and rebuilt behavior, checks restored method/generated-owner names,
and verifies that an incremental build and the original input remain unchanged.

The .NET runner supplies its runtime assembly directory to the exporter so framework
types and compiler-generated attributes resolve. No PowerShell parsing is required.
