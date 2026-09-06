param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$inputDirectory = Join-Path $OutputDirectory 'input'
$emitterDirectory = Join-Path $OutputDirectory 'emitter'
$exportDirectory = Join-Path $OutputDirectory 'export'
New-Item -ItemType Directory -Path $inputDirectory,$emitterDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'NullableAliasFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitNullableAlias.cs') -Destination $emitterDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' |
    Set-Content -LiteralPath (Join-Path $inputDirectory 'NullableAliasFixture.csproj')
$dnlib = [Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" |
    Set-Content -LiteralPath (Join-Path $emitterDirectory 'Emitter.csproj')
dotnet build (Join-Path $inputDirectory 'NullableAliasFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Fixture compilation failed.' }
$compiled = Join-Path $inputDirectory 'bin\Release\net48\NullableAliasFixture.exe'
$inputExe = Join-Path $OutputDirectory 'NullableAliasFixture.exe'
dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- $compiled $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Alias IL generation failed.' }
& $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Original nullable alias behavior failed.' }
& $DnSpyConsole --no-color --sdk-project --threads 1 -o $exportDirectory $inputExe
if ($LASTEXITCODE -ne 0) { throw 'dnSpy export failed.' }
$project = Get-ChildItem -LiteralPath $exportDirectory -Recurse -Filter '*.csproj' | Select-Object -First 1
$rebuilt = Join-Path $OutputDirectory 'rebuilt'
dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Exported nullable source compilation failed.' }
& (Join-Path $rebuilt 'NullableAliasFixture.exe')
if ($LASTEXITCODE -ne 0) { throw 'Rebuilt nullable behavior changed.' }
