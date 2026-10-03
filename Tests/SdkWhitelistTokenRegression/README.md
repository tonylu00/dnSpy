# SDK token identity regression

Run from the repository root with a fresh fixture directory:

```text
dotnet run --project Tests/SdkWhitelistTokenRegression/SdkWhitelistTokenRegression.csproj -c Release -- <new-fixture-directory>
```

This portable test links the actual dnSpy SDK whitelist guard. It creates a
metadata snapshot containing protected public types, methods, fields and a
named parameter, then attempts renames with prefixed/unprefixed, padded/unpadded
and mixed-case hexadecimal tokens. Tokens contain alphabetic hexadecimal digits.
Every equivalent spelling must preserve the same SDK identity. Unchanged names
remain valid. This protects the source-export boundary; it does not prove ETS
runtime or third-party App compatibility.
