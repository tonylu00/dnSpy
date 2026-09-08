param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$library = Join-Path $OutputDirectory 'library'
$consumer = Join-Path $OutputDirectory 'consumer'
New-Item -ItemType Directory -Path $library,$consumer | Out-Null
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>netstandard2.0</TargetFramework></PropertyGroup></Project>' | Set-Content (Join-Path $library 'Library.csproj')
@'
using System.Net.Http;
namespace Extensions {
    public static class Numbers {
        public static int Read(this int value) { return value + 7; }
    }
    public static class Messages {
        public static int Read(this HttpContent value) { return value == null ? 31 : 43; }
    }
}
'@ | Set-Content (Join-Path $library 'Library.cs')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><ProjectReference Include="..\library\Library.csproj" /></ItemGroup></Project>' | Set-Content (Join-Path $consumer 'Consumer.csproj')
@'
public static class Consumer {
    public static int Main() {
        int value = 10;
        return Extensions.Numbers.Read(value);
    }
}
'@ | Set-Content (Join-Path $consumer 'Consumer.cs')
dotnet build (Join-Path $consumer 'Consumer.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Fixture compilation failed.' }
$bin = Join-Path $consumer 'bin\Release\net48'
$inputs = @((Join-Path $bin 'Consumer.exe'), (Join-Path $bin 'Library.dll'))
& $inputs[0]
if ($LASTEXITCODE -ne 17) { throw 'Original behavior failed.' }
$hashes = @($inputs | Get-FileHash | ForEach-Object Hash)
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export @inputs
    if ($LASTEXITCODE -ne 0) { throw 'Export failed.' }
    $consumerProject = Get-Content (Join-Path $export 'Consumer\Consumer.csproj') -Raw
    $libraryProject = Get-Content (Join-Path $export 'Library\Library.csproj') -Raw
    if ($consumerProject -notmatch '<Reference Include="System.Net.Http"') { throw 'Consumer omitted the forwarded dependency.' }
    if ($libraryProject -match '<Reference Include="System.Net.Http"') { throw 'Standard library acquired a framework-specific reference.' }
    $sources = @(Get-ChildItem $export -Recurse -Filter '*.cs' | Sort-Object FullName | Get-FileHash | ForEach-Object Hash)
    if ($threads -eq 1) { $firstSources = $sources }
    elseif (Compare-Object $firstSources $sources -SyncWindow 0 -CaseSensitive) { throw 'Source differs by worker count.' }
    $solution = Get-ChildItem $export -Filter '*.sln' | Select-Object -First 1
    dotnet build $solution.FullName -c Release --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Forwarded dependency source compilation failed.' }
    $rebuilt = Get-ChildItem $export -Recurse -Filter Consumer.exe | Where-Object FullName -Match '\\bin\\' | Select-Object -First 1
    & $rebuilt.FullName
    if ($LASTEXITCODE -ne 17) { throw 'Rebuilt behavior differs.' }
}
if (Compare-Object $hashes @($inputs | Get-FileHash | ForEach-Object Hash) -SyncWindow 0) { throw 'Inputs changed.' }
Write-Output 'PASS: forwarded API dependency survives cross-framework export and rebuild.'
