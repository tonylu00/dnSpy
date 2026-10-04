param(
    [Parameter(Mandatory)][string] $BaseAudit,
    [Parameter(Mandatory)][string] $RuntimeDirectory,
    [Parameter(Mandatory)][string] $Inspector,
    [Parameter(Mandatory)][string[]] $Modules,
    [Parameter(Mandatory)][string] $OutputDirectory,
    [switch] $RequireUnchangedSource
)
$ErrorActionPreference='Stop'
foreach($name in @('BaseAudit','RuntimeDirectory','Inspector','OutputDirectory')) {
    Set-Variable -Name $name -Value ([IO.Path]::GetFullPath((Get-Variable -Name $name -ValueOnly)))
}
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a fresh physical refresh directory.'}
$audit=Get-Content -Raw -LiteralPath $BaseAudit | ConvertFrom-Json
if($audit.Kind -ne 'PhysicalScopeFinalAstCoverageAudit' -or $audit.CandidatesRetired -ne 0 -or
    (Get-FileHash -LiteralPath $audit.Auditor).Hash -ne $audit.AuditorSha256 -or
    (Get-FileHash -LiteralPath $audit.Summary).Hash -ne $audit.SummarySha256){throw 'Invalid/stale base audit.'}
$base=Get-Content -Raw -LiteralPath $audit.Summary | ConvertFrom-Json
if($base.Kind -ne 'MappedPhysicalScopeFinalAstObservations' -or $base.Status -ne 'complete' -or
    $base.ExpectedModules -ne $base.CompletedModules -or $base.ExpectedModules -ne $audit.TotalModules){throw 'Incomplete base scope.'}
$pins=@{}
foreach($pin in $base.Pins.PSObject.Properties) {
    if((Get-FileHash -LiteralPath $pin.Name).Hash -ne $pin.Value){throw "Stale base producer pin: $($pin.Name)"}
    $pins[$pin.Name]=$pin.Value
}
$pins[$BaseAudit]=(Get-FileHash -LiteralPath $BaseAudit).Hash
$pins[$audit.Summary]=$audit.SummarySha256
foreach($path in @($Inspector)+(Get-ChildItem -LiteralPath $RuntimeDirectory -File -Filter '*.dll' | ForEach-Object FullName)) {
    $hash=(Get-FileHash -LiteralPath $path).Hash
    if($pins.ContainsKey($path) -and $pins[$path] -ne $hash){throw 'Producer path reused with different bytes.'}
    $pins[$path]=$hash
}
$selected=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach($name in $Modules){if(!$selected.Add($name)){throw 'Duplicate refresh module.'}}
$available=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach($row in $base.Results){$available.Add($row.Path) | Out-Null}
foreach($name in $selected){if(!$available.Contains($name)){throw "Foreign refresh module: $name"}}
$context=Get-Content -Raw -LiteralPath $base.ReferenceManifest | ConvertFrom-Json
$relative=[IO.Path]::GetRelativePath($context.InputDirectory,$OutputDirectory)
if($relative -ne '..' -and !$relative.StartsWith('..'+[IO.Path]::DirectorySeparatorChar) -and ![IO.Path]::IsPathRooted($relative)){throw 'Write refresh outside application inputs.'}
$results=[Collections.Generic.List[object]]::new()
$changes=[Collections.Generic.List[object]]::new()
$watch=[Diagnostics.Stopwatch]::StartNew()
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
$producer=Join-Path $OutputDirectory 'producer.ps1'
Copy-Item -LiteralPath $PSCommandPath -Destination $producer
$pins[$producer]=(Get-FileHash -LiteralPath $producer).Hash
function ReadHeader([string]$path,[string]$output) {
    & dotnet $Inspector $RuntimeDirectory $path $output report-summary
    if($LASTEXITCODE -ne 0){throw 'Native observation summary failed.'}
    return (Get-Content -Raw -LiteralPath $output | ConvertFrom-Json)
}
foreach($row in $base.Results) {
    if((Get-FileHash -LiteralPath $row.Report).Hash -ne $row.ReportSha256 -or
        (Get-FileHash -LiteralPath $row.Input).Hash -ne $row.InputSha256){throw 'Stale base input/report.'}
    if(!$selected.Contains($row.Path)){$results.Add($row);continue}
    $reportPath=Join-Path (Join-Path $OutputDirectory 'native') ($row.Path+'.json')
    New-Item -ItemType Directory -Path (Split-Path $reportPath) -Force | Out-Null
    Write-Output "REFRESH: $($row.Path)"
    & dotnet $Inspector $RuntimeDirectory $row.Input $reportPath inspect "--references=$($base.ReferenceManifest)" "--map=$($base.SourceMap)" --sdk-source 2>&1 | Tee-Object -FilePath ($reportPath+'.log') | Out-Host
    if($LASTEXITCODE -ne 0){throw 'Native refresh failed.'}
    $report=ReadHeader $reportPath ($reportPath+'.header.json')
    $previous=ReadHeader $row.Report ($reportPath+'.previous-header.json')
    if($report.InputSha256 -ne $row.InputSha256 -or $report.Mvid -ne $row.Mvid -or $report.AssemblyIdentity -ne $row.Identity -or
        $report.NormalizedMapSha256 -ne $previous.NormalizedMapSha256 -or $report.MapSha256 -ne $previous.MapSha256 -or
        $report.ReferenceManifestSha256 -ne $previous.ReferenceManifestSha256){throw 'Refresh physical/map/context mismatch.'}
    $before=($previous.SourceHashes | Sort-Object RootTypeToken | ConvertTo-Json -Depth 4 -Compress)
    $after=($report.SourceHashes | Sort-Object RootTypeToken | ConvertTo-Json -Depth 4 -Compress)
    if($RequireUnchangedSource -and $before -cne $after){throw 'Refresh changed emitted source.'}
    $changes.Add(@{Module=$row.Path;PreviousReport=$row.Report;PreviousReportSha256=$row.ReportSha256;UnchangedSource=($before -ceq $after)})
    $results.Add(@{Path=$row.Path;Input=$row.Input;InputSha256=$row.InputSha256;Mvid=$row.Mvid;Identity=$row.Identity;
        Report=$reportPath;ReportSha256=(Get-FileHash -LiteralPath $reportPath).Hash;Roots=$report.Roots.Count;
        BodyWitnesses=$report.BodyWitnesses;FieldBindings=$report.FieldBindings;
        PinnedNonlocalUses=$report.NonlocalReferenceAudit.PinnedDefinitions;UnresolvedNonlocalUses=$report.NonlocalReferenceAudit.UnresolvedUses;
        UnpinnedDefinitions=$report.NonlocalReferenceAudit.UnpinnedDefinitions.Count;ElapsedSeconds=$report.ElapsedSeconds;PeakChildWorkingSetBytes=$report.PeakWorkingSetBytes})
    $previous=$null; $report=$null
}
foreach($path in $pins.Keys){if((Get-FileHash -LiteralPath $path).Hash -ne $pins[$path]){throw "Refresh pin changed: $path"}}
@{Format=1;Kind='MappedPhysicalScopeFinalAstObservations';Status='complete';ExpectedModules=$base.ExpectedModules;CompletedModules=$results.Count;
    Runtime=$RuntimeDirectory;Inspector=$Inspector;ReferenceManifest=$base.ReferenceManifest;SourceMap=$base.SourceMap;Pins=$pins;
    Results=@($results.ToArray());CandidatesRetired=0;ElapsedSeconds=$watch.Elapsed.TotalSeconds;
    Refresh=@{BaseAudit=$BaseAudit;ReusedModules=($results.Count-$changes.Count);RefreshedModules=$changes.Count;Changes=@($changes.ToArray());RequireUnchangedSource=[bool]$RequireUnchangedSource};
    Limits='Explicit physical refresh of an audited scope. Reused reports retain their original immutable producer pins. New reports require a fresh complete native scope audit; no source, map, binary or candidate decisions are changed.'
} | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'summary.json')
Write-Output "PASS: $($changes.Count) modules refreshed, $($results.Count-$changes.Count) immutable reports reused. Run the native complete scope audit."
