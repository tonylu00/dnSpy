param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$source = Join-Path $OutputDirectory 'source'
New-Item -ItemType Directory -Path $source | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'SettingsPartialFixture.cs') -Destination $source
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include="System.Configuration" /></ItemGroup></Project>' | Set-Content (Join-Path $source 'SettingsPartialFixture.csproj')
dotnet build (Join-Path $source 'SettingsPartialFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Fixture compilation failed.' }
$inputExe = Join-Path $source 'bin\Release\net48\SettingsPartialFixture.exe'
& $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Original behavior failed.' }
$hash = (Get-FileHash -LiteralPath $inputExe).Hash
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $inputExe
    if ($LASTEXITCODE -ne 0) { throw 'Settings export failed.' }
    $sources = @(Get-ChildItem -LiteralPath $export -Recurse -Filter '*.cs' | Sort-Object FullName | Get-FileHash | ForEach-Object Hash)
    if ($threads -eq 1) { $firstSources = $sources }
    elseif (Compare-Object $firstSources $sources -SyncWindow 0 -CaseSensitive) { throw 'Source differs by worker count.' }
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Settings source compilation failed.' }
    & (Join-Path $rebuilt 'SettingsPartialFixture.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Rebuilt settings behavior failed.' }
}
if ((Get-FileHash -LiteralPath $inputExe).Hash -ne $hash) { throw 'Input assembly changed.' }
Write-Output 'PASS: settings partial export, metadata and behavior across worker counts.'
