param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$inputDirectory = Join-Path $OutputDirectory 'input'
$exportDirectory = Join-Path $OutputDirectory 'export'
New-Item -ItemType Directory -Path $inputDirectory | Out-Null

# These checks exercise both every short-circuit point and the no-match path.
# Each operand records its position, so reordering or evaluating extra operands fails.
$or = (0..767 | ForEach-Object { "Probe($_, false)" }) -join ' || '
$and = (0..767 | ForEach-Object { "Probe($_, true)" }) -join ' && '
@"
using System;
public static class LogicalChains {
    static int target, count;
    static bool ordered;
    static bool Probe(int position, bool invert) {
        ordered &= position == count++;
        return (position == target) ^ invert;
    }
    static bool Any() { return $or; }
    static bool All() { return $and; }
    public static int Main() {
        for (target = -1; target < 768; target++) {
            count = 0; ordered = true;
            if (Any() != (target >= 0) || !ordered || count != (target < 0 ? 768 : target + 1)) return 1;
            count = 0; ordered = true;
            if (All() != (target < 0) || !ordered || count != (target < 0 ? 768 : target + 1)) return 2;
        }
        Console.WriteLine("PASS: 1538 logical-chain evaluation paths preserve order and short-circuit behavior.");
        return 0;
    }
}
"@ | Set-Content -LiteralPath (Join-Path $inputDirectory 'LogicalChains.cs')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' |
    Set-Content -LiteralPath (Join-Path $inputDirectory 'LogicalChains.csproj')

dotnet build (Join-Path $inputDirectory 'LogicalChains.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Fixture compilation failed.' }
$inputExe = Join-Path $inputDirectory 'bin\Release\net48\LogicalChains.exe'
& $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Original fixture behavior failed.' }
& $DnSpyConsole --no-color --sdk-project --threads 4 -o $exportDirectory $inputExe
if ($LASTEXITCODE -ne 0) { throw 'dnSpy export failed.' }
$failures = Get-ChildItem -LiteralPath $exportDirectory -Recurse -Filter '*.cs' |
    Select-String -Pattern 'An exception occurred when decompiling|Error decompiling'
if ($failures) { throw 'dnSpy wrote a decompilation error into the exported source.' }
$project = Get-ChildItem -LiteralPath $exportDirectory -Recurse -Filter '*.csproj' | Select-Object -First 1
$rebuilt = Join-Path $OutputDirectory 'rebuilt'
dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Exported source compilation failed.' }
& (Join-Path $rebuilt 'LogicalChains.exe')
if ($LASTEXITCODE -ne 0) { throw 'Rebuilt fixture behavior changed.' }
