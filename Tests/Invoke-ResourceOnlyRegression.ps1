param([Parameter(Mandatory)][string]$DnSpyConsole,[Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new output directory.'}
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
$inputs=@()
foreach($name in @('ResourceOnly','RawOnly')){
 $dir=Join-Path $OutputDirectory $name
 New-Item -ItemType Directory -Path (Join-Path $dir 'Data') | Out-Null
 '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><UseWPF>true</UseWPF></PropertyGroup><ItemGroup><Resource Include="Data\message.txt" /></ItemGroup></Project>' | Set-Content (Join-Path $dir ($name+'.csproj'))
 'retained resource' | Set-Content (Join-Path $dir 'Data\message.txt')
 if($name -eq 'ResourceOnly'){'<ResourceDictionary xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" xmlns:s="clr-namespace:System;assembly=mscorlib"><s:String x:Key="Message">BAML-only value</s:String></ResourceDictionary>' | Set-Content (Join-Path $dir 'Dictionary.xaml')}
 dotnet build (Join-Path $dir ($name+'.csproj')) -c Release --nologo -v quiet
 if($LASTEXITCODE -ne 0){throw 'Library build failed.'}
 $inputs+=Join-Path $dir ('bin\Release\net48\'+$name+'.dll')
}
$hostDir=Join-Path $OutputDirectory 'host'
New-Item -ItemType Directory -Path $hostDir | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ResourceOnlyHost.cs') -Destination $hostDir
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><UseWPF>true</UseWPF><OutputType>Exe</OutputType></PropertyGroup></Project>' | Set-Content (Join-Path $hostDir 'Host.csproj')
dotnet build (Join-Path $hostDir 'Host.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Host build failed.'}
$hostExe=Join-Path $hostDir 'bin\Release\net48\Host.exe'
$baseline=Join-Path $OutputDirectory 'baseline'
New-Item -ItemType Directory -Path $baseline | Out-Null
$inputs | ForEach-Object {Copy-Item -LiteralPath $_ -Destination $baseline}
& $hostExe $baseline
if($LASTEXITCODE -ne 0){throw 'Original resources failed.'}
$hashes=@($inputs | Get-FileHash | Select-Object Path,Hash)
foreach($threads in @(1,4)){
 $export=Join-Path $OutputDirectory "export-$threads"
 & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export @inputs
 if($LASTEXITCODE -ne 0){throw 'Export failed.'}
 $rebuilt=Join-Path $OutputDirectory "rebuilt-$threads"
 dotnet build (Join-Path $export 'solution.sln') -c Release -o $rebuilt --nologo -v quiet
 if($LASTEXITCODE -ne 0){throw 'Rebuilt source compilation failed.'}
 & $hostExe $rebuilt
 if($LASTEXITCODE -ne 0){throw 'Rebuilt resources failed.'}
}
if(Compare-Object $hashes @($inputs | Get-FileHash | Select-Object Path,Hash) -Property Path,Hash){throw 'Input changed.'}
