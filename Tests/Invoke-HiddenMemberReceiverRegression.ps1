param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$source = Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory -Path $source | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'HiddenMemberReceiverFixture.cs') -Destination $source
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' | Set-Content (Join-Path $source 'HiddenMemberReceiverFixture.csproj')
dotnet build (Join-Path $source 'HiddenMemberReceiverFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Fixture compilation failed.' }
$original = Join-Path $source 'bin\Release\net48\HiddenMemberReceiverFixture.exe'
$hash = (Get-FileHash -LiteralPath $original).Hash
& $original
if ($LASTEXITCODE -ne 0) { throw 'Original behavior failed.' }
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
    if ($LASTEXITCODE -ne 0) { throw 'Export failed.' }
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Source compilation failed.' }
    & (Join-Path $rebuilt 'HiddenMemberReceiverFixture.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Rebuilt behavior changed.' }
}
if ((Get-FileHash -LiteralPath $original).Hash -ne $hash) { throw 'Input assembly changed.' }
