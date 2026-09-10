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
When an export also builds dependencies from separate source trees, declare
those roots with `-ReferenceOnlyDirectories D:\analysis\compatibility`.
Their projects must have build outputs; the manifest records their source and
rebuilt hashes, but they are not copied into the application tree. Undeclared
external roots and roots overlapping the application input are rejected.
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
It also checks resource sets without a neutral counterpart and byte-identical
satellites distributed under additional culture paths. The exporter preserves
the resource manifest names; staging copies the matching rebuilt satellite to
each original physical location.

When differently versioned parents share a satellite destination, staging collects
all candidates before selecting the original physical satellite's name, version
and culture. Each candidate must still match its rebuilt parent's signing key.
This supports unsigned rebuilds without allowing a compatibility parent's older
satellite to replace the current one. Both parent assembly paths are retained.
The manifest records selected and unused candidates. Matching candidates must
have identical bytes; conflicting content or a missing version fails before copy.

`Invoke-SharedSatelliteStagingRegression.ps1` verifies both project orders,
localized lookup, retention of both parents, and missing/conflicting rejection.
