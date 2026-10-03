Run with .NET 8 or newer on Windows, Linux or macOS:

```
dotnet run --project Tests/MethodReferenceResolutionRegression -c Release
```

Links the actual portable alias/resolution helpers. Exercises unresolved .NET Standard versus
framework signatures, generic method calls, different vendor scopes and signing identities,
incompatible nested generic arguments and ambiguous fallback matches. Framework facade
tolerance must propagate the chosen definition's alias without accepting arbitrary vendor types.

The actual ETS export/build remains the integration check for AST name projection.
