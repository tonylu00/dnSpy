# Rebuilt source SDK contract audit

Run `Invoke-SdkSourceContractAudit.ps1 -DnlibPath <dnlib.dll>
-ExportDirectory <built-sdk-export> -OutputDirectory <new-directory>` after
building the exported Release solution. The audit uses `dnspy-export-map.xml`
to compare each physical input with its corresponding rebuilt output, retaining
separate contexts for duplicate assembly identities.

It compares visible types, methods and fields, including scoped signatures,
inheritance, interfaces, flags, generic names and constraints, parameter names,
flags and default values. It also checks property/event rows and property accessor
names. Differences produce `result.json` and fail the command.

This is a metadata audit. It does not prove method-body equivalence, custom
attribute equivalence, native interop behavior or successful live application
startup. Use unchanged SDK callers and application tests as additional evidence.
