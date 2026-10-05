# Raw BAML helper preservation

Run on Windows with the old and repaired native exporters:

```
dotnet run --project Tests/RawBamlHelperRegression -c Release -- <old-console> <new-console> <fresh-directory>
```

The fixture compiles and executes a WPF resource dictionary containing an internal
control. It confirms that the old SDK exporter omits the public generated helper
when BAML decompilation is disabled. The repaired export must retain the helper's
method contracts and exact embedded BAML bytes, compile, execute the same internal
control load and retain its output hash after an incremental build. Original input
hashes must remain unchanged. This exercises raw BAML; it does not claim coverage
of every WPF markup or external App contract.
