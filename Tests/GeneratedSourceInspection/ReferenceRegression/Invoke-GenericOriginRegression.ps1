param(
    [Parameter(Mandatory)][string] $RuntimeDirectory,
    [Parameter(Mandatory)][string] $Inspector,
    [Parameter(Mandatory)][string] $FrameworkDirectory,
    [Parameter(Mandatory)][string] $OutputDirectory,
    [string] $TargetFramework = 'net10.0'
)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
$FrameworkDirectory=[IO.Path]::GetFullPath($FrameworkDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a fresh generic-origin regression directory.'}
New-Item -ItemType Directory -Path "$OutputDirectory/input" | Out-Null
function Read([string]$path){Get-Content -Raw -LiteralPath $path | ConvertFrom-Json -AsHashtable}
function Save([string]$path,$value){$value | ConvertTo-Json -Depth 24 | Set-Content -LiteralPath $path}
function Native([string[]]$arguments){
    & dotnet $Inspector $RuntimeDirectory @arguments
    if($LASTEXITCODE -ne 0){throw "Native command failed: $($arguments[-1])"}
}
'<Project/>' | Set-Content "$OutputDirectory/Directory.Build.props"
Copy-Item -LiteralPath "$PSScriptRoot/../GenericOriginFixture.cs" -Destination "$OutputDirectory/input/Fixture.cs"
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>$TargetFramework</TargetFramework><Optimize>true</Optimize></PropertyGroup></Project>" | Set-Content "$OutputDirectory/input/Fixture.csproj"
& dotnet build "$OutputDirectory/input/Fixture.csproj" -c Release
if($LASTEXITCODE -ne 0){throw 'Generic fixture build failed.'}
$assembly=[IO.Path]::GetFullPath("$OutputDirectory/input/bin/Release/$TargetFramework/Fixture.dll")
Native @($assembly,"$OutputDirectory/metadata.json",'metadata')
$metadata=Read "$OutputDirectory/metadata.json"
$identity=[Reflection.AssemblyName]::GetAssemblyName($assembly).FullName
$inputDirectory=[IO.Path]::GetDirectoryName($assembly)
Save "$OutputDirectory/seed.json" @{
    Format=1;InputDirectory=$inputDirectory;RequireSourceContexts=$true
    Assemblies=@(@{Path=$assembly;Identity=$identity;Mvid=$metadata.Mvid;Sha256=(Get-FileHash -LiteralPath $assembly).Hash;ExportInput=$true})
    Contexts=@(@{Source=$assembly;Directories=@($inputDirectory,$FrameworkDirectory)})
}
'<AssemblyContexts/>' | Set-Content "$OutputDirectory/contexts.xml"
'<configuration/>' | Set-Content "$OutputDirectory/app.config"
$xml=[xml]'<SourceNameMap Version="1"/>'
$xml.DocumentElement.SetAttribute('InputDirectory',$inputDirectory);$xml.Save("$OutputDirectory/map.xml")
Native @("$OutputDirectory/seed.json","$OutputDirectory/context.json",'prepare-context',"--contexts=$OutputDirectory/contexts.xml","--app-config=$OutputDirectory/app.config","--framework=$FrameworkDirectory")
& "$PSScriptRoot/../Inspect-PhysicalScope.ps1" -RuntimeDirectory $RuntimeDirectory -Inspector $Inspector -ReferenceManifest "$OutputDirectory/context.json" -SourceMap "$OutputDirectory/map.xml" -OutputDirectory "$OutputDirectory/scope"
Native @("$OutputDirectory/scope/summary.json","$OutputDirectory/audit.json",'audit-scope')
$audit=Read "$OutputDirectory/audit.json"
if(!$audit.PrintedReferenceCoverage -or $audit.OriginalBodyContextRebindings -lt 2 -or $audit.UnresolvedPrintedUses -ne 0 -or $audit.UnknownPrintedOwners -ne 0 -or $audit.UnpinnedPrintedDefinitions.Count -ne 0){throw 'Generic fixture lost exact original body-context bindings.'}
$summary=Read "$OutputDirectory/scope/summary.json"
$report=Read $summary.Results[0].Report
$field=@($report.Roots[0].PrintedReferences | Where-Object { !$_.IsDefinition -and $_.RequestedSignature -match '^TFirst .*::First$' })
if($field.Count -ne 2){throw 'Expected generic field assignment and copy access.'}
$field[0].RequestedSignature=$field[0].RequestedSignature.Replace('TFirst','TSecond')
$modifiedReport="$OutputDirectory/modified-report.json";Save $modifiedReport $report
$summary.Results[0].Report=$modifiedReport;$summary.Results[0].ReportSha256=(Get-FileHash -LiteralPath $modifiedReport).Hash
Save "$OutputDirectory/modified-summary.json" $summary
$target="$OutputDirectory/rejected.json"
$oldPreference=$ErrorActionPreference
try{$ErrorActionPreference='Continue';$diagnostics=& dotnet $Inspector $RuntimeDirectory "$OutputDirectory/modified-summary.json" $target audit-scope 2>&1|Out-String;$code=$LASTEXITCODE}
finally{$ErrorActionPreference=$oldPreference}
$diagnostics | Set-Content "$OutputDirectory/rejected.log"
if($code -eq 0 -or (Test-Path -LiteralPath $target) -or $diagnostics -notmatch 'Printed reference origin signature mismatch'){throw 'Wrong generic field role was accepted or published.'}
Save "$OutputDirectory/proof.json" @{
    Format=1;Success=$true;Checks=2;Audit="$OutputDirectory/audit.json";AuditSha256=(Get-FileHash "$OutputDirectory/audit.json").Hash
    Inspector=$Inspector;InspectorSha256=(Get-FileHash -LiteralPath $Inspector).Hash
    OriginalBodyContextRebindings=$audit.OriginalBodyContextRebindings
    Cases=@('generic type field context and reconstructed lambda MemberRef/MethodSpec contexts','wrong generic field role rejected without publishing')
}
Write-Output 'PASS: generic original-reference contexts and rejection of incorrect generic roles.'
