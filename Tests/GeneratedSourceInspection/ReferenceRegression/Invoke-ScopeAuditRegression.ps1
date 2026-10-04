param(
    [Parameter(Mandatory)][string] $RuntimeDirectory,
    [Parameter(Mandatory)][string] $Inspector,
    [Parameter(Mandatory)][string] $FixtureDirectory,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
$FixtureDirectory=[IO.Path]::GetFullPath($FixtureDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a fresh scope audit regression directory.'}
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
$mapPath=Join-Path $OutputDirectory 'empty-map.xml'
$xml=[xml]'<SourceNameMap Version="1"/>'
$xml.DocumentElement.SetAttribute('InputDirectory',$FixtureDirectory); $xml.Save($mapPath)
& (Join-Path $PSScriptRoot '../Inspect-PhysicalScope.ps1') -RuntimeDirectory $RuntimeDirectory -Inspector $Inspector -ReferenceManifest "$FixtureDirectory/bound.json" -SourceMap $mapPath -OutputDirectory "$OutputDirectory/scope"
$summaryPath="$OutputDirectory/scope/summary.json"
function Read([string]$path){Get-Content -Raw -LiteralPath $path | ConvertFrom-Json -AsHashtable}
function SaveJson([string]$path,$value){$value | ConvertTo-Json -Depth 24 | Set-Content -LiteralPath $path}
$checks=0
function Check([bool]$condition,[string]$message){$script:checks++;if(!$condition){throw $message}}
& dotnet $Inspector $RuntimeDirectory $summaryPath "$OutputDirectory/audit.json" audit-scope
Check ($LASTEXITCODE -eq 0) 'valid native scope audit'
$audit=Read "$OutputDirectory/audit.json"
Check ($audit.TotalModules -eq 2 -and $audit.Roots -eq 2) 'complete physical/root coverage'
Check ($audit.PinnedNonlocalUses -eq 8 -and $audit.UnpinnedDefinitions.Count -eq 0) 'exact twin definition coverage'
Check ($audit.CandidatesRetired -eq 0) 'scope audit makes no naming retirement decision'
$serial=0
function Reject([string]$name,[scriptblock]$summaryMutation,[scriptblock]$reportMutation,[string]$message) {
    $script:serial++; $summary=Read $summaryPath
    if($reportMutation) {
        $report=Read $summary.Results[0].Report; & $reportMutation $report
        $reportPath="$OutputDirectory/modified-report-$serial.json"; SaveJson $reportPath $report
        $summary.Results[0].Report=$reportPath; $summary.Results[0].ReportSha256=(Get-FileHash -LiteralPath $reportPath).Hash
    }
    if($summaryMutation){& $summaryMutation $summary}
    $mutated="$OutputDirectory/modified-summary-$serial.json";SaveJson $mutated $summary
    $target="$OutputDirectory/rejected-$serial.json"
    $oldPreference=$ErrorActionPreference
    try{$ErrorActionPreference='Continue';$diagnostics=& dotnet $Inspector $RuntimeDirectory $mutated $target audit-scope 2>&1 | Out-String;$code=$LASTEXITCODE}
    finally{$ErrorActionPreference=$oldPreference}
    Check ($code -ne 0 -and $diagnostics.Contains($message)) "reject $name with expected native guard: $diagnostics"
    Check (!(Test-Path -LiteralPath $target)) "no publication after $name"
}
Reject 'incomplete status' {param($s)$s.Status='running'} $null 'incomplete'
Reject 'missing physical module' {param($s)$s.Results=@($s.Results[0]);$s.ExpectedModules=1;$s.CompletedModules=1} $null 'coverage mismatch'
Reject 'duplicate module' {param($s)$s.Results[1]=$s.Results[0]} $null 'duplicate physical module'
Reject 'stale pin' {param($s)$s.Pins[$s.SourceMap]='0'*64} $null 'pin changed'
Reject 'missing root' $null {param($r)$r.Roots=@()} 'Missing original top-level AST roots'
Reject 'filtered root' $null {param($r)$r.Options+=@('--root=0x02000002')} 'Filtered/unsupported'
Reject 'wrong original definition' $null {param($r)$r.Definitions[0].FullName='Wrong'} 'Original physical definition changed'
Reject 'foreign generic parameter token' $null {param($r)$r.Roots[0].ReferenceTokens+=@(704643073)} 'AST token is not an original local definition'
Reject 'wrong external token' $null {param($r)$use=@($r.Roots[0].NonlocalReferences|Where-Object DefinitionToken -GT 0)[0];$use.DefinitionToken=67109119} 'Nonlocal pinned definition mismatch'
Reject 'wrong witness type' $null {param($r)$r.Roots[0].BodyWitnesses=@(@{Kind='AsyncMethod';OwnerToken=100663297;ImplementationToken=100663297;ImplementationTypeToken=33554687})} 'Body witness implementation/type mismatch'
Reject 'method as field binding' $null {param($r)$r.Roots[0].FieldBindings=@(@{FieldToken=100663297;OwnerToken=100663297;SourceName='value'})} 'Hoisted binding is not an original field'
Reject 'wrong printed root' $null {param($r)$r.SourceHashes[0].RootTypeToken=33554687} 'Printed source hash coverage'
Reject 'nonhex source hash' $null {param($r)$r.SourceHashes[0].SourceSha256='Z'*64} 'Invalid/duplicate printed source hash'
Reject 'different normalized map' $null {param($r)$r.NormalizedMapSha256='0'*64} 'normalized mapping differs'
$summary=Read $summaryPath;$report=Read $summary.Results[0].Report
$use=@($report.Roots[0].NonlocalReferences|Where-Object DefinitionToken -GT 0)[0];$use.DefinitionModulePath=Join-Path $OutputDirectory 'unpinned.dll'
$reportPath="$OutputDirectory/unpinned-report.json";SaveJson $reportPath $report
$summary.Results[0].Report=$reportPath;$summary.Results[0].ReportSha256=(Get-FileHash -LiteralPath $reportPath).Hash
$unpinnedSummary="$OutputDirectory/unpinned-summary.json";SaveJson $unpinnedSummary $summary
& dotnet $Inspector $RuntimeDirectory $unpinnedSummary "$OutputDirectory/unpinned-audit.json" audit-scope
Check ($LASTEXITCODE -eq 0) 'unpinned metadata remains reportable'
$unpinned=Read "$OutputDirectory/unpinned-audit.json"
Check ($unpinned.UnpinnedDefinitions.Count -eq 1 -and $unpinned.CandidatesRetired -eq 0) 'unpinned target cannot establish naming closure'
@{Checks=$checks;Audit=@{Path="$OutputDirectory/audit.json";Sha256=(Get-FileHash -LiteralPath "$OutputDirectory/audit.json").Hash};InspectorSha256=(Get-FileHash -LiteralPath $Inspector).Hash;Limits='Synthetic native physical/root/definition/source-hash coverage guards; no application naming or runtime verdict.'} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$OutputDirectory/proof.json"
Write-Output "PASS: $checks native scope coverage audit guards."
