param([Parameter(Mandatory)][string]$DnSpyConsole, [Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression output folder.'}
$source=Join-Path $OutputDirectory 'source'
New-Item -ItemType Directory -Path $source | Out-Null
'<Project />' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'NonEnclosingConversionFixture.cs') -Destination $source
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' | Set-Content (Join-Path $source 'NonEnclosingConversionFixture.csproj')
dotnet build $source -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Conversion fixture compilation failed.'}
$original=Join-Path $source 'bin\Release\net48\NonEnclosingConversionFixture.exe'
$emitter=Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory $emitter | Out-Null
$dnlib=[Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitter 'Emitter.csproj')
@"
using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        using var module=ModuleDefMD.Load(args[0]);
        var method=module.Types.Single(t=>t.Name=="Widened").Methods.Single(m=>m.Name=="Convert");
        method.Name="op_Implicit";
        method.IsSpecialName=true;
        var explicitMethod=module.Types.Single(t=>t.Name=="Widened").Methods.Single(m=>m.Name=="ConvertRef");
        explicitMethod.Name="op_Explicit";
        explicitMethod.IsSpecialName=true;
        module.Write(args[1]);
    }
}
"@ | Set-Content (Join-Path $emitter 'Program.cs')
dotnet build $emitter -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Conversion emitter build failed.'}
$patched=Join-Path (Split-Path $original) 'patched.exe'
dotnet (Join-Path $emitter 'bin\Release\net10.0\Emitter.dll') $original $patched
if($LASTEXITCODE -ne 0){throw 'Conversion metadata rewrite failed.'}
Move-Item -LiteralPath $patched -Destination $original -Force
$hash=(Get-FileHash -LiteralPath $original).Hash
$expected=@(& $original)
if($LASTEXITCODE -ne 0){throw 'Original conversion behavior failed.'}
foreach($threads in @(1,4)) {
    $export=Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
    if($LASTEXITCODE -ne 0){throw 'Conversion export failed.'}
    $project=Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt=Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if($LASTEXITCODE -ne 0){throw 'Conversion source compilation failed.'}
    $client=Join-Path $rebuilt 'Caller.cs'
    'class Caller { static int Main() { Valid<int> v=23; return (int)v==23 && (int)(Maybe?)new Maybe { Value=11 }==11 && (int)(Maybe?)null==-1 ? 0 : 1; } }' | Set-Content $client
    $compiler=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
    & $compiler /nologo ('/r:'+(Join-Path $rebuilt 'NonEnclosingConversionFixture.exe')) ('/out:'+(Join-Path $rebuilt 'Caller.exe')) $client
    if($LASTEXITCODE -ne 0){throw 'Valid conversion metadata could not compile a new caller.'}
    & (Join-Path $rebuilt 'Caller.exe')
    if($LASTEXITCODE -ne 0){throw 'Fresh valid conversion caller behavior changed.'}
    $actual=@(& (Join-Path $rebuilt 'NonEnclosingConversionFixture.exe'))
    if($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -CaseSensitive -SyncWindow 0)){throw 'Conversion behavior changed.'}

}
if((Get-FileHash -LiteralPath $original).Hash -ne $hash){throw 'Input assembly changed.'}
Write-Output $expected



