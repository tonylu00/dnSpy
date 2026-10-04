param(
    [Parameter(Mandatory)][string] $RuntimeDirectory,
    [Parameter(Mandatory)][string] $Inspector,
    [Parameter(Mandatory)][string] $ReferenceManifest,
    [Parameter(Mandatory)][string] $SourceMap,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference='Stop'
foreach($name in @('RuntimeDirectory','Inspector','ReferenceManifest','SourceMap','OutputDirectory')) {
    Set-Variable -Name $name -Value ([IO.Path]::GetFullPath((Get-Variable -Name $name -ValueOnly)))
}
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a fresh physical scope inspection directory.'}
$manifest=Get-Content -Raw -LiteralPath $ReferenceManifest | ConvertFrom-Json
if($manifest.Format -ne 1 -or !$manifest.RequireSourceContexts){throw 'Full physical scope requires an explicitly scoped pinned manifest.'}
$inputs=@($manifest.Assemblies | Where-Object ExportInput | Sort-Object Path)
if($inputs.Count -eq 0){throw 'Missing explicit export inputs.'}
$inputRoot=[IO.Path]::GetFullPath($manifest.InputDirectory)
$relativeOutput=[IO.Path]::GetRelativePath($inputRoot,$OutputDirectory)
if($relativeOutput -ne '..' -and !$relativeOutput.StartsWith('..'+[IO.Path]::DirectorySeparatorChar) -and ![IO.Path]::IsPathRooted($relativeOutput)){throw 'Write scope evidence outside the application input tree.'}
$pins=@{}
foreach($path in @($ReferenceManifest,$SourceMap,$Inspector)+(Get-ChildItem -LiteralPath $RuntimeDirectory -File -Filter '*.dll' | ForEach-Object FullName)) {
    $pins[$path]=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
}
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
$summaryPath=Join-Path $OutputDirectory 'summary.json'
$results=[Collections.Generic.List[object]]::new()
$watch=[Diagnostics.Stopwatch]::StartNew()
function Save([string]$status) {
    foreach($path in $pins.Keys){if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $pins[$path]){throw "Inspection input changed: $path"}}
    $summary=@{Format=1;Kind='MappedPhysicalScopeFinalAstObservations';Status=$status;ExpectedModules=$inputs.Count;CompletedModules=$results.Count;
        Runtime=$RuntimeDirectory;Inspector=$Inspector;ReferenceManifest=$ReferenceManifest;SourceMap=$SourceMap;Pins=$pins;Results=@($results.ToArray());
        CandidatesRetired=0;ElapsedSeconds=$watch.Elapsed.TotalSeconds;Limits='Sequential child processes bound decompiler lifetime to one module. All supplied physical export inputs are inspected; reports observe final mapped SDK AST, not full exports, source compilation, semantic naming, contract restoration or runtime compatibility.'}
    $summary | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath ($summaryPath+'.pending')
    Move-Item -LiteralPath ($summaryPath+'.pending') -Destination $summaryPath -Force
}
Save 'running'
try {
    foreach($modulePin in $inputs) {
        $relative=[IO.Path]::GetRelativePath($inputRoot,[IO.Path]::GetFullPath($modulePin.Path))
        if([IO.Path]::IsPathRooted($relative) -or $relative -eq '..' -or $relative.StartsWith('..'+[IO.Path]::DirectorySeparatorChar)){throw 'Export input outside pinned root.'}
        $reportPath=Join-Path (Join-Path $OutputDirectory 'native') ($relative+'.json')
        New-Item -ItemType Directory -Path (Split-Path $reportPath) -Force | Out-Null
        Write-Output "START $($results.Count+1)/$($inputs.Count): $relative"
        & dotnet $Inspector $RuntimeDirectory $modulePin.Path $reportPath inspect "--references=$ReferenceManifest" "--map=$SourceMap" --sdk-source 2>&1 | Tee-Object -FilePath ($reportPath+'.log') | Out-Host
        if($LASTEXITCODE -ne 0){throw "Native inspection failed: $relative"}
        $report=Get-Content -Raw -LiteralPath $reportPath | ConvertFrom-Json
        if(!$report.MapApplied -or !$report.RestoreMetadataOnlyFields -or $report.InputSha256 -ne $modulePin.Sha256 -or $report.Mvid -ne $modulePin.Mvid -or
            $report.AssemblyIdentity -ne $modulePin.Identity -or $report.ReferenceManifestSha256 -ne $pins[$ReferenceManifest] -or $report.MapSha256 -ne $pins[$SourceMap]){throw 'Invalid native physical/source observation binding.'}
        if(@($report.Roots | Where-Object { !$_.CompleteTypeScope -or $_.ModuleMvid -ne $modulePin.Mvid }).Count -ne 0){throw 'Incomplete or foreign AST root.'}
        $results.Add(@{Path=$relative;Input=$modulePin.Path;InputSha256=$modulePin.Sha256;Mvid=$modulePin.Mvid;Identity=$modulePin.Identity;Report=$reportPath;ReportSha256=(Get-FileHash -LiteralPath $reportPath).Hash;
            Roots=$report.Roots.Count;BodyWitnesses=(@($report.Roots | ForEach-Object BodyWitnesses)).Count;FieldBindings=(@($report.Roots | ForEach-Object FieldBindings)).Count;
            PinnedNonlocalUses=$report.NonlocalReferenceAudit.PinnedDefinitions;UnresolvedNonlocalUses=$report.NonlocalReferenceAudit.UnresolvedUses;UnpinnedDefinitions=$report.NonlocalReferenceAudit.UnpinnedDefinitions.Count;
            ElapsedSeconds=$report.ElapsedSeconds;PeakChildWorkingSetBytes=$report.PeakWorkingSetBytes})
        $report=$null
        Save 'running'
        Write-Output "DONE $($results.Count)/$($inputs.Count): $relative"
    }
    Save 'complete'
    Write-Output "PASS: $($results.Count) physical modules observed. No candidates retired."
}
catch { Save 'failed'; throw }
