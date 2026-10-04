param([Parameter(Mandatory)][string] $Worklist,
      [Parameter(Mandatory)][string] $RuntimeDirectory,
      [Parameter(Mandatory)][string] $Inspector,
      [Parameter(Mandatory)][string] $ReferenceManifest,
      [Parameter(Mandatory)][string] $SourceMap,
      [Parameter(Mandatory)][string] $OutputDirectory,
      [string] $ReuseDirectory)
$ErrorActionPreference='Stop'
foreach($name in @('Worklist','RuntimeDirectory','Inspector','ReferenceManifest','SourceMap','OutputDirectory')) {
    Set-Variable -Name $name -Value ([IO.Path]::GetFullPath((Get-Variable -Name $name -ValueOnly)))
}
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a fresh diagnostic directory.'}
if($ReuseDirectory){$ReuseDirectory=[IO.Path]::GetFullPath($ReuseDirectory)}
$work=Get-Content -Raw -LiteralPath $Worklist | ConvertFrom-Json
if($work.Kind -ne 'NativeStateSourceCoverageGaps' -or $work.CandidatesRetired -ne 0){throw 'Unsupported state source worklist.'}
if((Get-FileHash $work.Audit).Hash -ne $work.AuditSha256){throw 'Stale worklist audit.'}
$rows=@($work.Rows | Where-Object {$_.Status -eq 'RetainedDeclaration'})
if(!$rows.Count){throw 'No retained state implementations.'}
$pins=@{}
foreach($path in @($Worklist,$Inspector,$ReferenceManifest,$SourceMap,$work.Audit)+(Get-ChildItem $RuntimeDirectory -File -Filter '*.dll' | ForEach-Object FullName)) {$pins[$path]=(Get-FileHash $path).Hash}
New-Item -ItemType Directory $OutputDirectory | Out-Null
$producer=Join-Path $OutputDirectory 'producer.ps1'
Copy-Item -LiteralPath $PSCommandPath -Destination $producer
$pins[$producer]=(Get-FileHash $producer).Hash
if($ReuseDirectory){$previousProducer=Join-Path $ReuseDirectory 'producer.ps1'; $pins[$previousProducer]=(Get-FileHash $previousProducer).Hash}
$results=[Collections.Generic.List[object]]::new()
$index=0; $reused=0
foreach($row in $rows) {
    if((Get-FileHash $row.Module).Hash -ne $row.Sha256){throw 'Stale physical state input.'}
    $pins[$row.Module]=$row.Sha256
    if(@($row.Owners.Token | Sort-Object -Unique).Count -ne 1 -or @($row.Owners.Signature | Sort-Object -Unique).Count -ne 1 -or
       @($row.Owners.Kind | Sort-Object -Unique).Count -ne 1){throw 'Retained state needs exactly one independently proven owner.'}
    $owner=$row.Owners[0]
    $token='0x'+([uint32]$owner.Token).ToString('X8')
    $prefix=Join-Path $OutputDirectory ([string]$index+'-'+[IO.Path]::GetFileName($row.Module)+'-'+$token)
    $cached=if($ReuseDirectory){Join-Path $ReuseDirectory ([IO.Path]::GetFileName($prefix))}else{$null}
    if($cached -and (Test-Path -LiteralPath ($cached+'.json')) -and (Test-Path -LiteralPath ($cached+'.cs')) -and (Test-Path -LiteralPath ($cached+'.log'))) {
        $prefix=$cached; $reused++
        Write-Output "REUSE: $($row.Module) $token"
    } else {
        Write-Output "INSPECT: $($row.Module) $token"
        & dotnet $Inspector $RuntimeDirectory $row.Module ($prefix+'.json') inspect "--references=$ReferenceManifest" "--map=$SourceMap" --sdk-source "--method=$token" "--source=$prefix.cs" 2>&1 | Tee-Object -FilePath ($prefix+'.log') | Out-Host
        if($LASTEXITCODE -ne 0){throw 'Native state source inspection failed.'}
    }
    $report=Get-Content -Raw -LiteralPath ($prefix+'.json') | ConvertFrom-Json
    if($report.Input -ne $row.Module -or $report.InputSha256 -ne $row.Sha256 -or $report.Mvid -ne $row.Mvid -or $report.AssemblyIdentity -ne $row.Identity -or
       $report.MapSha256 -ne $pins[$SourceMap] -or $report.ReferenceManifestSha256 -ne $pins[$ReferenceManifest] -or $report.Roots.Count -ne 1 -or
       $report.ToolSha256 -ne $pins[$Inspector] -or $report.Mode -ne 'MappedFinalCSharpAst' -or !$report.RestoreMetadataOnlyFields -or
       $report.Options -notcontains "--method=$token" -or $report.SourceOutput -ne "$prefix.cs"){throw 'Native observation provenance mismatch.'}
    foreach($dependency in $report.Dependencies){
        if((Get-FileHash $dependency.Path).Hash -ne $dependency.Sha256){throw 'Stale native dependency.'}
        $pins[$dependency.Path]=$dependency.Sha256
    }
    if($report.SourceHashes.Count -ne 1 -or (Get-FileHash "$prefix.cs").Hash -ne $report.SourceHashes[0].SourceSha256){throw 'Native source output differs from its observation.'}
    $root=$report.Roots[0]
    if($root.CompleteTypeScope){throw 'Member diagnostic must not claim complete root coverage.'}
    $witness=@($root.BodyWitnesses | Where-Object {$_.OwnerToken -eq $owner.Token -and $_.ImplementationTypeToken -eq [Convert]::ToUInt32($row.TypeToken.Substring(2),16)})
    foreach($path in @("$prefix.json","$prefix.cs","$prefix.log")){$pins[$path]=(Get-FileHash $path).Hash}
    $results.Add(@{Module=$row.Module;Sha256=$row.Sha256;Mvid=$row.Mvid;Identity=$row.Identity;TypeToken=$row.TypeToken;OwnerToken=$token;
        OwnerSignature=$owner.Signature;OwnerEvidence=$row.Owners;Before=$row.Status;ExactWitness=($witness.Count -eq 1);Witnesses=$witness;
        MissingEvidence=if($witness.Count -eq 1){'Whole-scope canonical-owner, escape and metadata-restoration closure still required.'}else{$row.MissingEvidence};
        Report=$prefix+'.json';Source=$prefix+'.cs';Log=$prefix+'.log';ElapsedSeconds=$report.ElapsedSeconds;PeakWorkingSetBytes=$report.PeakWorkingSetBytes})
    $report=$null; $root=$null; $index++
}
foreach($path in $pins.Keys){if((Get-FileHash $path).Hash -ne $pins[$path]){throw "Changed diagnostic pin: $path"}}
@{Format=1;Kind='RetainedStateOwnerSourceDiagnostics';Status='complete';Pins=$pins;Rows=@($results.ToArray());
    Owners=$results.Count;ExactWitnesses=@($results | Where-Object ExactWitness).Count;ReusedNativeReports=$reused;ColdChildren=$results.Count-$reused;CandidatesRetired=0;
    Limits='Partial exact-owner diagnostics only. New witnesses do not update whole-scope coverage, prove metadata restoration or retire naming candidates.'
} | ConvertTo-Json -Depth 12 | Set-Content (Join-Path $OutputDirectory 'summary.json')
Write-Output "PASS: $($results.Count) retained owners; $(@($results | Where-Object ExactWitness).Count) exact witnesses. No candidates retired."
