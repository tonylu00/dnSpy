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
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'SourceMetadataFixture.cs') -Destination $inputDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><LangVersion>latest</LangVersion><Nullable>enable</Nullable><AllowUnsafeBlocks>true</AllowUnsafeBlocks></PropertyGroup><ItemGroup><Reference Include="Microsoft.CSharp" /></ItemGroup></Project>' |
    Set-Content (Join-Path $inputDirectory 'SourceMetadataFixture.csproj')
$dnlib = [Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" |
    Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
@'
using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        if (args[0] == "check") {
            using var rebuilt = ModuleDefMD.Load(args[1]);
            var type = rebuilt.GetTypes().Single(t => t.Name == "ReferenceValues");
            foreach (var name in new[] { "get_Item", "First" }) {
                var method = type.Methods.Single(m => m.Name == name);
                if (!method.Parameters.ReturnParameter.ParamDef.CustomAttributes.IsDefined("System.Runtime.CompilerServices.IsReadOnlyAttribute"))
                    throw new System.Exception("Readonly reference contract lost: " + name);
            }
            return;
        }
        using var module = ModuleDefMD.Load(args[0]);
        module.GetTypes().Single(t => t.Name == "HiddenValue").Visibility = TypeAttributes.NestedPrivate;
        module.GetTypes().Single(t => t.Name == "HiddenCallback").Visibility = TypeAttributes.NestedPrivate;
        foreach (var attribute in module.CustomAttributes.Where(a => a.TypeFullName == "System.Security.UnverifiableCodeAttribute").ToArray())
            module.CustomAttributes.Remove(attribute);
        module.Write(args[1]);
    }
}
'@ | Set-Content (Join-Path $emitterDirectory 'Program.cs')
dotnet build (Join-Path $inputDirectory 'SourceMetadataFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Source metadata fixture build failed.' }
$inputExe = Join-Path $OutputDirectory 'SourceMetadataFixture.exe'
dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- (Join-Path $inputDirectory 'bin\Release\net48\SourceMetadataFixture.exe') $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Source metadata fixture emission failed.' }
& $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Original source metadata behavior failed.' }
$export = Join-Path $OutputDirectory 'export'
& $DnSpyConsole --no-color --sdk-project --threads 4 -o $export $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Source metadata export failed.' }
$project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
$rebuilt = Join-Path $OutputDirectory 'rebuilt'
dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Exported source metadata compilation failed.' }
& (Join-Path $rebuilt 'SourceMetadataFixture.exe')
if ($LASTEXITCODE -ne 0) { throw 'Rebuilt source metadata behavior changed.' }
dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- check (Join-Path $rebuilt 'SourceMetadataFixture.exe')
if ($LASTEXITCODE -ne 0) { throw 'Rebuilt readonly reference contract changed.' }
