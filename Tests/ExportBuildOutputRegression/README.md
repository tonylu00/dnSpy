# Evaluated export output paths

```
dotnet run --project Tests/ExportBuildOutputRegression -c Release -- <fresh-directory>
```

The portable fixture builds two physically distinct assemblies with the same name
in separate shared output directories, adds stale project-local `bin` decoys and
checks that the audit selects each evaluated MSBuild `TargetPath`. It also checks
missing projects, paths outside the export tree, invalid filenames and malformed
property-query output. The shared resolver evaluates properties without building
the exported application.
