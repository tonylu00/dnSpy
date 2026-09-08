param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$source = Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory -Path $source | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'FieldKeywordFixture.cs') -Destination $source
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>14.0</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $source 'FieldKeywordFixture.csproj')
dotnet build (Join-Path $source 'FieldKeywordFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Fixture compilation failed.' }
$original = Join-Path $source 'bin\Release\net48\FieldKeywordFixture.exe'
$hash = (Get-FileHash -LiteralPath $original).Hash
& $original
if ($LASTEXITCODE -ne 0) { throw 'Original behavior failed.' }
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
    if ($LASTEXITCODE -ne 0) { throw 'Export failed.' }
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt -p:LangVersion=14.0 --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'C# 14 source compilation failed.' }
    & (Join-Path $rebuilt 'FieldKeywordFixture.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Rebuilt behavior changed.' }
}
if ((Get-FileHash -LiteralPath $original).Hash -ne $hash) { throw 'Input assembly changed.' }
Write-Output 'PASS: C# 14 getter, setter, captured local, field metadata and parameter bindings.'
