param(
    [Parameter(Mandatory)][string]$MetadataReport,
    [Parameter(Mandatory)][string[]]$CaseManifests,
    [Parameter(Mandatory)][string]$OutputDirectory
)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $root){throw 'Choose a fresh output directory.'}
New-Item -ItemType Directory -Path $root |Out-Null
'<Project />' | Set-Content (Join-Path $root 'Directory.Build.props')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><LangVersion>latest</LangVersion></PropertyGroup><ItemGroup><Reference Include="System.Xml.Linq"/></ItemGroup></Project>' | Set-Content (Join-Path $root 'Probe.csproj')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'XmlSerializerBehaviorProbe.cs') -Destination (Join-Path $root 'Program.cs')
dotnet build (Join-Path $root 'Probe.csproj') -c Release -v quiet
if($LASTEXITCODE){throw 'Behavior probe build failed.'}
$metadata=Get-Content -LiteralPath $MetadataReport -Raw|ConvertFrom-Json
if(!$metadata.Success){throw 'Metadata/storage comparison did not pass.'}
$probe=Join-Path $root 'bin/Release/net48/Probe.exe'
$comparisonArguments=@((Join-Path $PSScriptRoot 'compare_xml_serializer_behavior.py'),'--metadata',$MetadataReport)
$index=0
foreach($manifest in $CaseManifests){
    [xml]$cases=Get-Content -LiteralPath $manifest -Raw
    $source=[IO.Path]::GetFullPath($cases.Tests.Source)
    $module=@($metadata.Modules|Where-Object {[IO.Path]::GetFullPath($_.Source) -eq $source})
    if($module.Count -ne 1 -or $module[0].OriginalSha256 -ne $cases.Tests.Sha256 -or $module[0].Identity -ne $cases.Tests.Identity){throw 'Case manifest does not match one checked physical module.'}
    $original=Join-Path $root ("original-$index.xml"); $rebuilt=Join-Path $root ("rebuilt-$index.xml")
    & $probe $module[0].Source $manifest $original
    if($LASTEXITCODE){throw 'Original physical probe failed.'}
    & $probe $module[0].Rebuilt $manifest $rebuilt
    if($LASTEXITCODE){throw 'Rebuilt physical probe failed.'}
    $comparisonArguments+=@('--pair',$original,$rebuilt);$index++
}
$comparisonArguments+=@('--output',(Join-Path $root 'comparison.json'))
python @comparisonArguments
if($LASTEXITCODE){throw 'Serializer behavior differs.'}
