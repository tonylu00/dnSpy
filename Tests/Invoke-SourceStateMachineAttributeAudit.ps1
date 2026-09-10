param([Parameter(Mandatory)][string]$DnlibPath,
      [Parameter(Mandatory)][string]$ExportDirectory,
      [Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new audit output directory.'}
$export=(Resolve-Path -LiteralPath $ExportDirectory).Path
$dnlib=[Security.SecurityElement]::Escape((Resolve-Path -LiteralPath $DnlibPath).Path)
$output=[IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $output | Out-Null
'<Project/>' | Set-Content (Join-Path $output 'Directory.Build.props')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'SourceStateMachineAttributes.cs') -Destination $output
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><ImplicitUsings>enable</ImplicitUsings></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $output 'Audit.csproj')
dotnet build (Join-Path $output 'Audit.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'State-machine audit build failed.'}
& dotnet (Join-Path $output 'bin\Release\net8.0\Audit.dll') $export > (Join-Path $output 'result.json')
if($LASTEXITCODE){throw "State-machine attribute audit failed; see $output\result.json"}
$result=Get-Content (Join-Path $output 'result.json') -Raw | ConvertFrom-Json
$result | Select-Object Export,Projects,StateAttributes,ExternalStateAttributes,IssueCount | ConvertTo-Json
