param([Parameter(Mandatory)][string]$DnlibPath,
      [Parameter(Mandatory)][string]$ExportDirectory,
      [Parameter(Mandatory)][string]$OutputDirectory,
      [string]$StagingManifest,
      [string]$SdkWhitelist)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new audit output directory.'}
$export=(Resolve-Path -LiteralPath $ExportDirectory).Path
$dnlib=[Security.SecurityElement]::Escape((Resolve-Path -LiteralPath $DnlibPath).Path)
$output=[IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $output | Out-Null
'<Project/>' | Set-Content (Join-Path $output 'Directory.Build.props')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'SdkSourceContracts.cs') -Destination $output
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Shared/ExportBuildOutput.cs') -Destination $output
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $output 'Audit.csproj')
dotnet build (Join-Path $output 'Audit.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'Contract audit build failed.'}
$manifestArguments = @()
if ($StagingManifest) { $manifestArguments = @([IO.Path]::GetFullPath($StagingManifest)) }
if ($SdkWhitelist) {
 if (!$StagingManifest) { throw 'A physical staging manifest is required for SDK whitelist scope.' }
 $manifestArguments += [IO.Path]::GetFullPath($SdkWhitelist)
}
& dotnet (Join-Path $output 'bin\Release\net10.0\Audit.dll') $export @manifestArguments > (Join-Path $output 'result.json')
if($LASTEXITCODE){throw "SDK contract audit failed; see $output\result.json"}
Get-Content -LiteralPath (Join-Path $output 'result.json')
