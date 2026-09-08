param([Parameter(Mandatory)][string]$DnSpyConsole, [Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new output directory.' }
$inputRoot = Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory -Path $inputRoot | Out-Null
'<Project />' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ExpressionFallbackFixture.cs') -Destination $inputRoot
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><LangVersion>latest</LangVersion><Optimize>true</Optimize></PropertyGroup></Project>' | Set-Content (Join-Path $inputRoot 'Fixture.csproj')
dotnet build (Join-Path $inputRoot 'Fixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Fixture build failed.' }
$original = Join-Path $inputRoot 'bin\Release\net48\Fixture.exe'
& $original
if ($LASTEXITCODE -ne 0) { throw 'Original behavior failed.' }
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
    if ($LASTEXITCODE -ne 0) { throw 'Export failed.' }
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Rebuild failed.' }
    & (Join-Path $rebuilt 'Fixture.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Rebuilt behavior changed.' }
}


