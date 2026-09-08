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
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'BamlTemplateScopeFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'BamlTemplateScopeDictionary.xaml') -Destination (Join-Path $inputDirectory 'Dictionary.xaml')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><UseWPF>true</UseWPF><Optimize>true</Optimize></PropertyGroup></Project>' |
    Set-Content (Join-Path $inputDirectory 'BamlTemplateScopeFixture.csproj')
dotnet build (Join-Path $inputDirectory 'BamlTemplateScopeFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'BAML template fixture compilation failed.' }
$original = Join-Path $inputDirectory 'bin\Release\net48\BamlTemplateScopeFixture.exe'
$inputHash = (Get-FileHash -LiteralPath $original).Hash
& $original
if ($LASTEXITCODE -ne 0) { throw 'Original BAML template behavior failed.' }
foreach ($threads in @(1,4)) {
$export = Join-Path $OutputDirectory "export-$threads"
& $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
if ($LASTEXITCODE -ne 0) { throw 'BAML template source export failed.' }
$project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
$rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Exported BAML template compilation failed.' }
& (Join-Path $rebuilt 'BamlTemplateScopeFixture.exe')
if ($LASTEXITCODE -ne 0) { throw 'Rebuilt BAML template behavior changed.' }
}
if ((Get-FileHash -LiteralPath $original).Hash -ne $inputHash) { throw 'Input assembly changed.' }
