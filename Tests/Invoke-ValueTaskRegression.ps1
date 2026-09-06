param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory,
    [string] $TasksExtensionsPath
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$inputDirectory = Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory -Path $inputDirectory | Out-Null
if (!$TasksExtensionsPath) { $TasksExtensionsPath = Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) '..\net48\System.Threading.Tasks.Extensions.dll' }
if (!(Test-Path -LiteralPath $TasksExtensionsPath)) { throw 'Build dnSpy for net48 or supply -TasksExtensionsPath.' }
$tasksPath = [Security.SecurityElement]::Escape([IO.Path]::GetFullPath($TasksExtensionsPath))
$unsafePath = [Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($TasksExtensionsPath))) 'System.Runtime.CompilerServices.Unsafe.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><AutoGenerateBindingRedirects>true</AutoGenerateBindingRedirects></PropertyGroup><ItemGroup><Reference Include=`"System.Threading.Tasks.Extensions`"><HintPath>$tasksPath</HintPath></Reference><Reference Include=`"System.Runtime.CompilerServices.Unsafe`"><HintPath>$unsafePath</HintPath></Reference></ItemGroup></Project>" |
    Set-Content (Join-Path $inputDirectory 'ValueTaskFixture.csproj')
@'
using System;
using System.Threading.Tasks;
public sealed class Payload { public int Number; }
public static class ValueTaskFixture {
    static int Consume(Payload value) { return value.Number; }
    public static async Task<int> Read(ValueTask<Payload> pending) {
        var value = await pending;
        if (value == null) throw new FormatException();
        return Consume(value);
    }
    public static async Task<int> Configured(ValueTask<Payload> pending) {
        var value = await pending.ConfigureAwait(false);
        if (value == null) throw new FormatException();
        return Consume(value);
    }
    public static async Task<int> ConfiguredTask(Task<Payload> pending) {
        var value = await pending.ConfigureAwait(false);
        if (value == null) throw new FormatException();
        return Consume(value);
    }
    public static int Main() {
        var value = new Payload { Number = 17 };
        if (Read(new ValueTask<Payload>(value)).GetAwaiter().GetResult() != 17) return 1;
        var source = new TaskCompletionSource<Payload>();
        var delayed = Configured(new ValueTask<Payload>(source.Task));
        if (delayed.IsCompleted) return 2;
        source.SetResult(value);
        if (delayed.GetAwaiter().GetResult() != 17) return 3;
        if (ConfiguredTask(Task.FromResult(value)).GetAwaiter().GetResult() != 17) return 4;
        try { Read(new ValueTask<Payload>(Task.FromResult<Payload>(null))).GetAwaiter().GetResult(); return 5; }
        catch (FormatException) { }
        Console.WriteLine("PASS: ValueTask and configured await results retain their generic type and behavior.");
        return 0;
    }
}
'@ | Set-Content (Join-Path $inputDirectory 'ValueTaskFixture.cs')
dotnet build (Join-Path $inputDirectory 'ValueTaskFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'ValueTask fixture build failed.' }
$inputDll = Join-Path $inputDirectory 'bin\Release\net48\ValueTaskFixture.exe'
& $inputDll
if ($LASTEXITCODE -ne 0) { throw 'Original ValueTask behavior failed.' }
$export = Join-Path $OutputDirectory 'export'
& $DnSpyConsole --no-color --sdk-project --threads 1 --app-config ($inputDll + '.config') -o $export $inputDll
if ($LASTEXITCODE -ne 0) { throw 'ValueTask export failed.' }
$project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
$rebuilt = Join-Path $OutputDirectory 'rebuilt'
dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Exported ValueTask source compilation failed.' }
& (Join-Path $rebuilt 'ValueTaskFixture.exe')
if ($LASTEXITCODE -ne 0) { throw 'Rebuilt ValueTask behavior changed.' }
