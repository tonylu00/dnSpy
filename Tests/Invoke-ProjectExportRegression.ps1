param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$library = Join-Path $OutputDirectory 'library'
$consumer = Join-Path $OutputDirectory 'consumer'
$export = Join-Path $OutputDirectory 'export'
New-Item -ItemType Directory -Path $library,$consumer | Out-Null
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework></PropertyGroup></Project>' |
    Set-Content -LiteralPath (Join-Path $library 'Library.csproj')
@'
public sealed class Buffer {
    public static implicit operator byte[](Buffer value) { return new byte[] { 17 }; }
}
public static class Library {
    public static int Read(Buffer value) { return ((byte[])value)[0]; }
}
'@ | Set-Content -LiteralPath (Join-Path $library 'Library.cs')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><GenerateTargetFrameworkAttribute>false</GenerateTargetFrameworkAttribute></PropertyGroup><ItemGroup><ProjectReference Include="..\library\Library.csproj" /></ItemGroup></Project>' |
    Set-Content -LiteralPath (Join-Path $consumer 'Consumer.csproj')
'public static class Consumer { public static int Main() { return Library.Read(new Buffer()); } }' |
    Set-Content -LiteralPath (Join-Path $consumer 'Consumer.cs')
dotnet build (Join-Path $consumer 'Consumer.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Fixture compilation failed.' }
$bin = Join-Path $consumer 'bin\Release\net48'
& (Join-Path $bin 'Consumer.exe')
if ($LASTEXITCODE -ne 17) { throw 'Original fixture behavior failed.' }
& $DnSpyConsole --no-color --sdk-project --threads 4 -o $export (Join-Path $bin 'Consumer.exe') (Join-Path $bin 'Library.dll')
if ($LASTEXITCODE -ne 0) { throw 'dnSpy export failed.' }
$projects = Get-ChildItem -LiteralPath $export -Filter '*.csproj' -Recurse
foreach ($project in $projects) {
    if ((Get-Content -LiteralPath $project.FullName -Raw) -notmatch '<TargetFramework>net48</TargetFramework>') {
        throw 'Exported project target does not match its dependency requirements.'
    }
}
$solution = Get-ChildItem -LiteralPath $export -Filter '*.sln' | Select-Object -First 1
dotnet build $solution.FullName -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Exported source compilation failed.' }
$rebuilt = Get-ChildItem -LiteralPath $export -Filter Consumer.exe -Recurse |
    Where-Object FullName -Match '\\bin\\' | Select-Object -First 1
& $rebuilt.FullName
if ($LASTEXITCODE -ne 17) { throw 'Rebuilt fixture behavior changed.' }
Write-Output 'PASS: inferred framework target and receiver conversion survive export, rebuild and execution.'
