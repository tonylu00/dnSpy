param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$inputDirectory = Join-Path $OutputDirectory 'input'
$emitterDirectory = Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $inputDirectory,$emitterDirectory | Out-Null
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' |
    Set-Content (Join-Path $inputDirectory 'DelegateFixture.csproj')
@'
using System;
public static class DelegateFixture {
    static object callback;
    static int calls;
    static int Increment(int value) { calls++; return value + 1; }
    public static int Read(int value) { return ((Func<int, int>)callback)(value); }
    public static int Main() {
        callback = new Func<int, int>(Increment);
        if (Read(16) != 17 || calls != 1) return 1;
        callback = null;
        try { Read(0); return 2; } catch (NullReferenceException) { }
        if (calls != 1) return 3;
        Console.WriteLine("PASS: object-typed delegate receiver preserves result, call count and null failure.");
        return 0;
    }
}
'@ | Set-Content (Join-Path $inputDirectory 'Program.cs')
$dnlib = [Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" |
    Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
@'
using System.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var method = module.Types.Single(t => t.Name == "DelegateFixture").Methods.Single(m => m.Name == "Read");
        var cast = method.Body.Instructions.Single(i => i.OpCode == OpCodes.Castclass);
        cast.OpCode = OpCodes.Nop;
        cast.Operand = null;
        module.Write(args[1]);
    }
}
'@ | Set-Content (Join-Path $emitterDirectory 'Program.cs')
dotnet build (Join-Path $inputDirectory 'DelegateFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Delegate fixture build failed.' }
$inputExe = Join-Path $OutputDirectory 'DelegateFixture.exe'
dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- (Join-Path $inputDirectory 'bin\Release\net48\DelegateFixture.exe') $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Delegate receiver IL generation failed.' }
& $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Original delegate behavior failed.' }
$export = Join-Path $OutputDirectory 'export'
& $DnSpyConsole --no-color --sdk-project --threads 1 -o $export $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Delegate export failed.' }
$project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
$rebuilt = Join-Path $OutputDirectory 'rebuilt'
dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Exported delegate source compilation failed.' }
& (Join-Path $rebuilt 'DelegateFixture.exe')
if ($LASTEXITCODE -ne 0) { throw 'Rebuilt delegate behavior changed.' }
