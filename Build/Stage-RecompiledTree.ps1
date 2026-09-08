param(
    [Parameter(Mandatory)][string]$InputDirectory,
    [Parameter(Mandatory)][string]$ExportDirectory,
    [Parameter(Mandatory)][string]$OutputDirectory,
    [string]$Configuration = 'Release'
)
$ErrorActionPreference = 'Stop'
$InputDirectory = [IO.Path]::GetFullPath($InputDirectory).TrimEnd('\')
$ExportDirectory = [IO.Path]::GetFullPath($ExportDirectory).TrimEnd('\')
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory).TrimEnd('\')
function RelativeWithin([string]$root, [string]$path) {
    $prefix = $root.TrimEnd('\') + '\'
    $full = [IO.Path]::GetFullPath($path)
    if (!$full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw "Path outside expected root: $full" }
    $full.Substring($prefix.Length)
}
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new output directory.' }
foreach ($root in @($InputDirectory, $ExportDirectory)) {
    if ($OutputDirectory.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Output must be outside input and export trees.' }
}
[xml]$map = Get-Content -LiteralPath (Join-Path $ExportDirectory 'dnspy-export-map.xml')
if ($map.DnSpyExportMap.ExportErrors -ne '0') { throw 'Export map reports errors.' }
$overlays = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::OrdinalIgnoreCase)
function AddOverlay([string]$source, [string]$built, [string]$kind) {
    $relative = RelativeWithin $InputDirectory $source
    if (!(Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing input file: $source" }
    if ($overlays.ContainsKey($relative)) { throw "Duplicate destination: $relative" }
    $overlays.Add($relative, [pscustomobject]@{ Relative=$relative; Built=$built; Kind=$kind; Hash=(Get-FileHash -LiteralPath $built).Hash })
}
foreach ($entry in $map.DnSpyExportMap.Project) {
    $null = RelativeWithin $InputDirectory $entry.Source
    $project = [IO.Path]::GetFullPath((Join-Path $ExportDirectory $entry.Project))
    $null = RelativeWithin $ExportDirectory $project
    $name = $entry.AssemblyName + [IO.Path]::GetExtension($entry.Source)
    $bin = Join-Path (Split-Path $project) 'bin'
    $configurationSegment = '\' + $Configuration + '\'
    $outputs = @(Get-ChildItem -LiteralPath $bin -Recurse -File | Where-Object {
        $_.Name -eq $name -and $_.FullName.IndexOf($configurationSegment, [StringComparison]::OrdinalIgnoreCase) -ge 0
    })
    if ($outputs.Count -ne 1) { throw "Ambiguous or missing build output for $project" }
    $built = $outputs[0].FullName
    AddOverlay $entry.Source $built 'Assembly'

    # Copy only this project's satellite outputs, never its transitive dependencies.
    # Their signing identity must match the rebuilt parent, not the original parent.
    $identity = [Reflection.AssemblyName]::GetAssemblyName($built)
    $satelliteName = $entry.AssemblyName + '.resources.dll'
    foreach ($satellite in Get-ChildItem -LiteralPath (Split-Path $built) -Recurse -File | Where-Object Name -eq $satelliteName) {
        $satIdentity = [Reflection.AssemblyName]::GetAssemblyName($satellite.FullName)
        $culture = $satIdentity.CultureName
        if (!$culture -or $satIdentity.Name -ne ($identity.Name + '.resources') -or
            [Convert]::ToBase64String($satIdentity.GetPublicKeyToken()) -ne [Convert]::ToBase64String($identity.GetPublicKeyToken())) {
            throw "Invalid satellite identity: $($satellite.FullName)"
        }
        $parent = Split-Path $entry.Source
        $candidates = @(@(
            (Join-Path $parent "$culture\$satelliteName"),
            (Join-Path $parent "$culture\$($entry.AssemblyName)\$satelliteName")
        ) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })
        if ($candidates.Count -ne 1) { throw "Ambiguous or missing satellite destination for $($satellite.FullName)" }
        AddOverlay $candidates[0] $satellite.FullName 'Satellite'
    }
    foreach ($directory in Get-ChildItem -LiteralPath (Split-Path $entry.Source) -Directory) {
        try { $culture = [Globalization.CultureInfo]::GetCultureInfo($directory.Name).Name } catch { continue }
        if (!$culture) { continue }
        foreach ($original in @((Join-Path $directory.FullName $satelliteName), (Join-Path $directory.FullName "$($entry.AssemblyName)\$satelliteName"))) {
            if ((Test-Path -LiteralPath $original -PathType Leaf) -and !$overlays.ContainsKey((RelativeWithin $InputDirectory $original))) {
                throw "Missing rebuilt satellite: $original"
            }
        }
    }
}
$tree = @(Get-ChildItem -LiteralPath $InputDirectory -Recurse -Force)
if ($tree | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }) { throw 'Input contains a link or junction.' }
$hashes = @($tree | Where-Object { !$_.PSIsContainer } | Get-FileHash)
Copy-Item -LiteralPath $InputDirectory -Destination $OutputDirectory -Recurse
foreach ($overlay in $overlays.Values) {
    Copy-Item -LiteralPath $overlay.Built -Destination (Join-Path $OutputDirectory $overlay.Relative)
}
foreach ($file in $hashes) {
    if ((Get-FileHash -LiteralPath $file.Path).Hash -ne $file.Hash) { throw "Input changed: $($file.Path)" }
    $relative = RelativeWithin $InputDirectory $file.Path
    $expected = if ($overlays.ContainsKey($relative)) { $overlays[$relative].Hash } else { $file.Hash }
    if ((Get-FileHash -LiteralPath (Join-Path $OutputDirectory $relative)).Hash -ne $expected) { throw "Output mismatch: $relative" }
}
if (@(Get-ChildItem -LiteralPath $OutputDirectory -Recurse -Force).Count -ne $tree.Count) { throw 'Runtime tree shape changed.' }
@{ Input=$InputDirectory; Export=$ExportDirectory; Output=$OutputDirectory; Files=$hashes.Count; Overlays=@($overlays.Values | Sort-Object Relative) } |
    ConvertTo-Json -Depth 5 | Set-Content ($OutputDirectory + '-manifest.json')
Write-Output "PASS: staged $($overlays.Count) assemblies and satellites; input hashes and tree structure preserved."
