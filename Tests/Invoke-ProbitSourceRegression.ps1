param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$source = Join-Path $OutputDirectory 'source'
New-Item -ItemType Directory -Path $source | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ProbitSourceFixture.cs') -Destination $source
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><UseWindowsForms>true</UseWindowsForms><AllowUnsafeBlocks>true</AllowUnsafeBlocks><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $source 'ProbitSourceFixture.csproj')
dotnet build (Join-Path $source 'ProbitSourceFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Fixture compilation failed.' }
$inputExe = Join-Path $source 'bin\Release\net48\ProbitSourceFixture.exe'
$hash = (Get-FileHash -LiteralPath $inputExe).Hash
# A plain non-obfuscated program must export to source that builds unmodified.
$expected = @(& $inputExe)
if ($LASTEXITCODE -ne 0) { throw 'Original behavior failed.' }
$expected | Set-Content (Join-Path $OutputDirectory 'expected.txt')
foreach ($threads in @(1, 4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $inputExe
    if ($LASTEXITCODE -ne 0) { throw 'Source export failed.' }
    if ((Get-ChildItem -LiteralPath $export -Recurse -Filter '*.cs' | Where-Object { $_.FullName -notlike '*\.dnspy-metadata\*' } |
        Select-String -Pattern 'Type_\d+|RuntimeHelpers\.InitializeArray\(new ' -List)) {
        throw 'Exported source still references a compiler data type.'
    }
    $sources = @(Get-ChildItem -LiteralPath $export -Recurse -Filter '*.cs' | Sort-Object FullName | Get-FileHash | ForEach-Object Hash)
    if ($threads -eq 1) { $firstSources = $sources }
    elseif (Compare-Object $firstSources $sources -SyncWindow 0 -CaseSensitive) { throw 'Source differs by worker count.' }
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Exported source did not compile without changes.' }
    $actual = @(& (Join-Path $rebuilt 'ProbitSourceFixture.exe'))
    if ($LASTEXITCODE -ne 0) { throw 'Rebuilt behavior failed.' }
    if (Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive) { throw 'Rebuilt behavior differs from the original.' }
}
if ((Get-FileHash -LiteralPath $inputExe).Hash -ne $hash) { throw 'Input assembly changed.' }
Write-Output 'PASS: non-obfuscated export, rebuild and behavior across worker counts.'
