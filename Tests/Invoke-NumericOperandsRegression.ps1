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
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'NumericOperandsFixture.cs') -Destination $inputDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' |
    Set-Content (Join-Path $inputDirectory 'NumericOperandsFixture.csproj')
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
        var type = module.GetTypes().Single(t => t.Name == "NumericOperandsFixture");
        foreach (var name in new[] { "Greater", "Less", "AtLeast", "AtMost" }) {
            var method = type.Methods.Single(m => m.Name == name);
            method.Body = new CilBody();
            var il = method.Body.Instructions;
            il.Add(Instruction.Create(OpCodes.Ldarg_0));
            il.Add(Instruction.Create(OpCodes.Call, type.Methods.Single(m => m.Name == "Left")));
            il.Add(Instruction.Create(OpCodes.Ldarg_1));
            il.Add(Instruction.Create(OpCodes.Call, type.Methods.Single(m => m.Name == "Right")));
            il.Add(Instruction.Create(name == "Greater" || name == "AtMost" ? OpCodes.Cgt : OpCodes.Clt_Un));
            if (name == "AtLeast" || name == "AtMost") { il.Add(Instruction.Create(OpCodes.Ldc_I4_0)); il.Add(Instruction.Create(OpCodes.Ceq)); }
            il.Add(Instruction.Create(OpCodes.Ret));
        }
        foreach (var name in new[] { "Negate32", "Negate64" }) {
            var method = type.Methods.Single(m => m.Name == name);
            method.Body = new CilBody();
            method.Body.Instructions.Add(Instruction.Create(OpCodes.Ldarg_0));
            method.Body.Instructions.Add(Instruction.Create(OpCodes.Neg));
            method.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
        }
        foreach (var name in new[] { "Single", "Double", "UnsignedDouble", "BoxDouble", "OverloadDouble", "CompareDouble" }) {
            var method = type.Methods.Single(m => m.Name == name);
            method.Body = new CilBody();
            var il = method.Body.Instructions;
            il.Add(Instruction.Create(OpCodes.Ldarg_0));
            if (name == "CompareDouble") { il.Add(Instruction.Create(OpCodes.Ldarg_1)); il.Add(Instruction.Create(OpCodes.Cgt)); }
            else il.Add(Instruction.Create(OpCodes.Call, type.Methods.Single(m => m.Name == "Right")));
            il.Add(Instruction.Create(name == "Single" ? OpCodes.Conv_R4 : name == "UnsignedDouble" ? OpCodes.Conv_R_Un : OpCodes.Conv_R8));
            if (name == "BoxDouble") il.Add(Instruction.Create(OpCodes.Box, module.CorLibTypes.Double.TypeDefOrRef));
            if (name == "OverloadDouble") il.Add(Instruction.Create(OpCodes.Call, type.Methods.Single(m => m.Name == "Select" && m.MethodSig.Params[0].ElementType == ElementType.R8)));
            il.Add(Instruction.Create(OpCodes.Ret));
        }
        module.Write(args[1]);
    }
}
'@ | Set-Content (Join-Path $emitterDirectory 'Program.cs')
dotnet build (Join-Path $inputDirectory 'NumericOperandsFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Numeric fixture compilation failed.' }
$original = Join-Path $OutputDirectory 'NumericOperandsFixture.exe'
dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- (Join-Path $inputDirectory 'bin\Release\net48\NumericOperandsFixture.exe') $original
if ($LASTEXITCODE -ne 0) { throw 'Numeric IL emission failed.' }
& $original
if ($LASTEXITCODE -ne 0) { throw 'Original numeric behavior failed.' }
$export = Join-Path $OutputDirectory 'export'
& $DnSpyConsole --no-color --sdk-project --threads 4 -o $export $original
if ($LASTEXITCODE -ne 0) { throw 'Numeric source export failed.' }
$project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
$rebuilt = Join-Path $OutputDirectory 'rebuilt'
dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Exported numeric compilation failed.' }
& (Join-Path $rebuilt 'NumericOperandsFixture.exe')
if ($LASTEXITCODE -ne 0) { throw 'Rebuilt numeric behavior changed.' }
