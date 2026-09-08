# Staging rebuilt applications

`Build/Stage-RecompiledTree.ps1` stages a built dnSpy source export into a new
copy of its input tree. It uses physical source paths in `dnspy-export-map.xml`
to keep assemblies with duplicate identities in their original directories.
Build the exported solution successfully before running it:

```powershell
./Build/Stage-RecompiledTree.ps1 -InputDirectory D:\analysis\input `
  -ExportDirectory D:\analysis\source -OutputDirectory D:\analysis\rebuilt
```

The script copies each project's main assembly and its own culture satellite
assemblies. Rebuilt unsigned parents need matching rebuilt satellites; retaining
the original signed satellites can silently select neutral English resources.
Transitive dependencies in build output directories are not used as overlays.
Missing satellites and ambiguous outputs fail before creating the destination.
The script verifies input hashes, output hashes and the complete tree shape,
and writes a manifest next to the output. Native components and other files
remain copied from the input. Standard `bin/[platform/]Release/[framework]`
layouts are supported; ambiguous multi-target outputs require a separate export.
Custom satellite probing directories are rejected when they cannot be mapped
unambiguously to the original culture folders.

Run `Tests/Invoke-SatelliteStagingRegression.ps1` with `-DnSpyConsole` and a new
`-OutputDirectory`. It creates two signed fixtures with the same assembly
identity and different Chinese resources, exports/rebuilds with one and four
workers, and verifies runtime culture lookup, duplicate contexts, unchanged data,
empty directories and rejection of missing rebuilt satellites.
