param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$inputDirectory = Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory -Path $inputDirectory | Out-Null
'<Project />' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'BamlConnectorsFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'BamlConnectorsView.xaml') -Destination (Join-Path $inputDirectory 'View.xaml')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><UseWPF>true</UseWPF><Optimize>true</Optimize></PropertyGroup></Project>' |
    Set-Content (Join-Path $inputDirectory 'BamlConnectorsFixture.csproj')
dotnet build (Join-Path $inputDirectory 'BamlConnectorsFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'BAML connector fixture compilation failed.' }
$original = Join-Path $inputDirectory 'bin\Release\net48\BamlConnectorsFixture.exe'
& $original
if ($LASTEXITCODE -ne 0) { throw 'Original BAML connector behavior failed.' }
$hash = (Get-FileHash -LiteralPath $original).Hash
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
    if ($LASTEXITCODE -ne 0) { throw 'BAML connector source export failed.' }
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Exported BAML connector compilation failed.' }
    & (Join-Path $rebuilt 'BamlConnectorsFixture.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Rebuilt BAML connector behavior changed.' }
}
if ((Get-FileHash -LiteralPath $original).Hash -ne $hash) { throw 'Original assembly changed.' }
