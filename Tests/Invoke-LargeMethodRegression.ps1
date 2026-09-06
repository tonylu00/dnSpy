param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory,
    [ValidateRange(1,4000)][int] $Count = 400,
    [switch] $Guarded
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$inputDirectory = Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory -Path $inputDirectory | Out-Null
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' |
    Set-Content (Join-Path $inputDirectory 'LargeMethodFixture.csproj')
$source = [Text.StringBuilder]::new()
[void]$source.AppendLine(@'
using System;
public sealed class Cell { public int Value; public Cell Link; }
public static class Program {
    static int calls;
    static int cleanups;
    static int Next() { return ++calls; }
    static Cell[] Create(bool alternate) {
'@)
if ($Guarded) { [void]$source.AppendLine('        try {') }
for ($index = 0; $index -lt $Count; $index++) {
    $previous = if ($index -eq 0) { 'null' } else { 'item' + ($index - 1) }
    [void]$source.AppendLine("        var item$index = new Cell { Value = alternate ? -Next() : Next(), Link = $previous };")
}
[void]$source.AppendLine('        return new[] { ' + ((0..($Count - 1) | ForEach-Object { "item$_" }) -join ', ') + ' };')
if ($Guarded) { [void]$source.AppendLine('        } finally { cleanups++; }') }
[void]$source.AppendLine(@'
    }
    public static int Main() {
        foreach (bool alternate in new[] { false, true }) {
            calls = 0;
            cleanups = 0;
            var cells = Create(alternate);
            if (calls != cells.Length) throw new Exception("Duplicated or missing initialization");
            if (cleanups != EXPECTED_CLEANUPS) throw new Exception("Cleanup count");
            for (int index = 0; index < cells.Length; index++) {
                if (cells[index].Value != (alternate ? -1 : 1) * (index + 1)) throw new Exception("Initialization order");
                if (!ReferenceEquals(cells[index].Link, index == 0 ? null : cells[index - 1])) throw new Exception("Shared stack reference");
            }
        }
        Console.WriteLine("PASS: large generated method preserves initialization order and shared references.");
        return 0;
    }
}
'@)
$source.ToString().Replace('EXPECTED_CLEANUPS', $(if ($Guarded) { '1' } else { '0' })) | Set-Content (Join-Path $inputDirectory 'Program.cs')
dotnet build (Join-Path $inputDirectory 'LargeMethodFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Large fixture compilation failed.' }
$original = Join-Path $inputDirectory 'bin\Release\net48\LargeMethodFixture.exe'
& $original
if ($LASTEXITCODE -ne 0) { throw 'Original large-method behavior failed.' }
$export = Join-Path $OutputDirectory 'export'
$timer = [Diagnostics.Stopwatch]::StartNew()
& $DnSpyConsole --no-color --sdk-project --threads 1 -o $export $original
$exportCode = $LASTEXITCODE
$timer.Stop()
[pscustomobject]@{ Count=$Count; Guarded=$Guarded.IsPresent; ExportSeconds=$timer.Elapsed.TotalSeconds; ExitCode=$exportCode } |
    ConvertTo-Json | Set-Content (Join-Path $OutputDirectory 'timing.json')
if ($exportCode -ne 0) { throw 'Large method source export failed.' }
$project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
$rebuilt = Join-Path $OutputDirectory 'rebuilt'
dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Exported large-method compilation failed.' }
& (Join-Path $rebuilt 'LargeMethodFixture.exe')
if ($LASTEXITCODE -ne 0) { throw 'Rebuilt large-method behavior changed.' }
