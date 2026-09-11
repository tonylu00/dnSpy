# Captured parameter alias regression

```text
dotnet run --project Tests/SourceParameterCaptureRegression -c Release -- path/to/dnSpy.Console.exe new-regression-directory
```

The C# driver creates a small library and caller, exports a baseline and an alias
variant, builds both, and executes generated and unchanged callers. It compares
all field names/signatures and checks original parameter names through reflection.
Fixtures cover synchronous and nested lambdas, async methods, generic async
methods, iterators and an ordinary field sharing the requested alias. A repeated
incremental build must preserve the result. This integration test needs a dnSpy
console build and .NET Framework 4.8 execution support.

Before the fix, parameter aliases changed compiler-generated display-class fields
even after state-machine fields had been restored. The regression fails against
the earlier exporter with four captured-field differences. It passes with the
updated build task.

The task follows direct stores from the original parameter or its proven hoisted
copy into a local compiler-generated display class. It does not rename arbitrary
same-named fields. Existing field collision checks, generic local reference
restoration and incremental-build behavior remain in effect.
