param([Parameter(Mandatory)][string]$DnlibPath,[Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new test directory.'}
$output=[IO.Path]::GetFullPath($OutputDirectory)
$fixture=Join-Path $output 'fixture'
New-Item -ItemType Directory -Path $fixture | Out-Null
'<Project/>' | Set-Content (Join-Path $output 'Directory.Build.props')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework></PropertyGroup></Project>' | Set-Content (Join-Path $fixture 'Fixture.csproj')
'public class Root {} public class Api<T> : Root where T : class { public void Run(int count = 17) {} }' | Set-Content (Join-Path $fixture 'Fixture.cs')
dotnet build (Join-Path $fixture 'Fixture.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'Fixture build failed.'}
$original=Join-Path $fixture 'bin\Release\net48\Fixture.dll'
$export=Join-Path $output 'export'
$project=Join-Path $export 'Fixture'
$binaryRoot=Join-Path $project 'bin\Release\net48'
New-Item -ItemType Directory -Path $binaryRoot | Out-Null
$binary=Join-Path $binaryRoot 'Fixture.dll'
Copy-Item -LiteralPath $original -Destination $binary
'<Project><PropertyGroup><TargetFramework>net48</TargetFramework><AssemblyName>Fixture</AssemblyName><OutputType>Library</OutputType></PropertyGroup></Project>' | Set-Content (Join-Path $project 'Fixture.csproj')
$escaped=[Security.SecurityElement]::Escape($original)
"<Export><Project Source=`"$escaped`" Project=`"Fixture\Fixture.csproj`"/></Export>" | Set-Content (Join-Path $export 'dnspy-export-map.xml')
$audit=Join-Path $output 'audit'
& (Join-Path $PSScriptRoot 'Invoke-SdkSourceContractAudit.ps1') -DnlibPath $DnlibPath -ExportDirectory $export -OutputDirectory $audit
Add-Type -Path $DnlibPath
$module=[dnlib.DotNet.ModuleDefMD]::Load($binary)
try {
 $type=$module.GetTypes() | Where-Object Name -eq 'Api`1'
 $type.BaseType=$module.CorLibTypes.Object.TypeDefOrRef
 $type.GenericParameters[0].Flags=[dnlib.DotNet.GenericParamAttributes]::NonVariant
 $method=$type.Methods | Where-Object Name -eq 'Run'
 $parameter=$method.ParamDefs | Where-Object Sequence -eq 1
 $parameter.IsOptional=$false
 $parameter.Constant.Value=[int]18
 $module.Write($binary+'.changed')
} finally {$module.Dispose()}
Move-Item -LiteralPath ($binary+'.changed') -Destination $binary -Force
& dotnet (Join-Path $audit 'bin\Release\net10.0\Audit.dll') $export > (Join-Path $output 'negative-result.json')
if($LASTEXITCODE -ne 1){throw 'Changed SDK contract did not fail the audit.'}
$result=Get-Content (Join-Path $output 'negative-result.json') -Raw | ConvertFrom-Json
foreach($kind in 'BaseType','GenericFlags','ParameterFlags','ParameterDefault'){
 if($kind -notin $result.Issues.Kind){throw "Missing contract diagnostic: $kind"}
}
'PASS identical contracts accepted; inheritance, generic constraints and parameter changes rejected.'
