param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$inputDirectory = Join-Path $OutputDirectory 'input'
$exportDirectory = Join-Path $OutputDirectory 'export'
New-Item -ItemType Directory -Path $inputDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'AsyncLayoutFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'DetachedAwaitFixture.cs') -Destination $inputDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' |
    Set-Content -LiteralPath (Join-Path $inputDirectory 'AsyncLayoutFixture.csproj')
dotnet build (Join-Path $inputDirectory 'AsyncLayoutFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Fixture compilation failed.' }
$inputExe = Join-Path $inputDirectory 'bin\Release\net48\AsyncLayoutFixture.exe'
& $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Original async behavior failed.' }
& $DnSpyConsole --no-color --sdk-project --threads 1 -o $exportDirectory $inputExe
if ($LASTEXITCODE -ne 0) { throw 'dnSpy export failed.' }
$source = Get-Content (Join-Path $exportDirectory 'AsyncLayoutFixture\AsyncLayoutFixture.cs') -Raw
foreach ($name in @('ReadDetachedPositive', 'ReadDetachedNegative', 'ReadDetachedForward', 'ReadDetachedBranched')) {
    if ($source -notmatch ('async Task<int> ' + $name + '\(')) { throw "Detached await was not reconstructed: $name" }
}
$project = Get-ChildItem -LiteralPath $exportDirectory -Recurse -Filter '*.csproj' | Select-Object -First 1
$rebuilt = Join-Path $OutputDirectory 'rebuilt'
dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Exported async source compilation failed.' }
& (Join-Path $rebuilt 'AsyncLayoutFixture.exe')
if ($LASTEXITCODE -ne 0) { throw 'Rebuilt async behavior changed.' }
