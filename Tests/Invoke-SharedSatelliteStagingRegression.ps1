param([Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new test directory.'}
$root=[IO.Path]::GetFullPath($OutputDirectory)
$inputRoot=Join-Path $root 'input'; $export=Join-Path $root 'export'
New-Item -ItemType Directory -Path $inputRoot,$export | Out-Null
'<Project/>' | Set-Content (Join-Path $root 'Directory.Build.props')
foreach($name in 'Current','Compatibility','Conflict'){
 $folder=Join-Path $export $name
 New-Item -ItemType Directory -Path $folder | Out-Null
 $version=if($name -eq 'Compatibility'){'1.0.0.0'}else{'2.0.0.0'}
 "<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><AssemblyName>Fixture</AssemblyName><RootNamespace>Fixture</RootNamespace><AssemblyVersion>$version</AssemblyVersion></PropertyGroup></Project>" | Set-Content (Join-Path $folder 'Fixture.csproj')
 'class Program { static int Main(string[] args) { var r = new System.Resources.ResourceManager("Fixture.Text",typeof(Program).Assembly); return r.GetString("Greeting",System.Globalization.CultureInfo.GetCultureInfo("zh-CN")) == args[0] ? 0 : 1; } }' | Set-Content (Join-Path $folder 'Program.cs')
 "<root><resheader name=`"resmimetype`"><value>text/microsoft-resx</value></resheader><resheader name=`"version`"><value>2.0</value></resheader><resheader name=`"reader`"><value>System.Resources.ResXResourceReader, System.Windows.Forms</value></resheader><resheader name=`"writer`"><value>System.Resources.ResXResourceWriter, System.Windows.Forms</value></resheader><data name=`"Greeting`"><value>$name 中文</value></data></root>" | Set-Content (Join-Path $folder 'Text.zh-CN.resx')
 dotnet build (Join-Path $folder 'Fixture.csproj') -c Release --nologo -v quiet
 if($LASTEXITCODE){throw 'Fixture build failed.'}
 Copy-Item -LiteralPath (Join-Path $folder 'bin\Release\net48\Fixture.exe') -Destination (Join-Path $inputRoot "$name.exe")
}
Copy-Item -LiteralPath (Join-Path $export 'Current\bin\Release\net48\zh-CN') -Destination $inputRoot -Recurse
$stage=Join-Path $PSScriptRoot '..\Build\Stage-RecompiledTree.ps1'
function Set-Map($names){
 $rows=foreach($name in $names){$path=[Security.SecurityElement]::Escape((Join-Path $inputRoot "$name.exe")); "<Project Source=`"$path`" Project=`"$name\Fixture.csproj`" AssemblyName=`"Fixture`"/>"}
 "<DnSpyExportMap ExportErrors=`"0`">$($rows -join '')</DnSpyExportMap>" | Set-Content (Join-Path $export 'dnspy-export-map.xml')
}
foreach($reverse in $false,$true){
 Set-Map $(if($reverse){@('Compatibility','Current')}else{@('Current','Compatibility')})
 $output=Join-Path $root "staged-$reverse"
 & $stage -InputDirectory $inputRoot -ExportDirectory $export -OutputDirectory $output
 & (Join-Path $output 'Current.exe') 'Current 中文'
 if($LASTEXITCODE){throw 'Current satellite lookup changed.'}
 foreach($name in 'Current','Compatibility'){
  if((Get-FileHash (Join-Path $output "$name.exe")).Hash -ne (Get-FileHash (Join-Path $export "$name\bin\Release\net48\Fixture.exe")).Hash){throw 'Parent assembly lost.'}
 }
 $manifest=Get-Content ($output+'-manifest.json') -Raw | ConvertFrom-Json
 if(@($manifest.SatelliteCandidates).Count -ne 2 -or @($manifest.SatelliteCandidates | Where-Object Selected).Count -ne 1){throw 'Candidate provenance missing.'}
}
foreach($case in 'missing','conflicting'){
 Set-Map $(if($case -eq 'missing'){@('Compatibility')}else{@('Current','Conflict')})
 $output=Join-Path $root $case
 $rejected=$false
 try { & $stage -InputDirectory $inputRoot -ExportDirectory $export -OutputDirectory $output }
 catch { if($_.Exception.Message -notmatch '^(Missing compatible rebuilt satellite|Conflicting rebuilt satellite content):'){throw}; $rejected=$true }
 if(!$rejected -or (Test-Path -LiteralPath $output)){throw 'Invalid shared satellite reached staging.'}
}
'PASS shared satellites selected independently of project order; missing and conflicting candidates rejected before copy.'
