param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory,
    [string] $ManagementAssemblyPath
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
if (!$ManagementAssemblyPath) {
    $ManagementAssemblyPath = Get-ChildItem -LiteralPath (Join-Path $env:WINDIR 'Microsoft.NET\assembly\GAC_MSIL\System.Management') -Filter 'System.Management.dll' -Recurse |
        Select-Object -First 1 -ExpandProperty FullName
}
if (!$ManagementAssemblyPath -or !(Test-Path -LiteralPath $ManagementAssemblyPath)) { throw 'Supply the installed GAC System.Management assembly.' }
$management = [Security.SecurityElement]::Escape([IO.Path]::GetFullPath($ManagementAssemblyPath))
$emitterDirectory = Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $emitterDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitGacReferences.cs') -Destination $emitterDirectory
$dnlib = [Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" |
    Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
foreach ($framework in @('net48','netstandard2.0')) {
    $directory = Join-Path $OutputDirectory $framework
    $library = Join-Path $directory 'library'
    $hostDirectory = Join-Path $directory 'host'
    New-Item -ItemType Directory -Path $library,$hostDirectory | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'GacReferenceFixture.cs') -Destination $library
    "<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>$framework</TargetFramework></PropertyGroup><ItemGroup><Reference Include=`"System.Management`"><HintPath>$management</HintPath><Private>false</Private></Reference></ItemGroup></Project>" |
        Set-Content (Join-Path $library 'GacReferenceFixture.csproj')
    '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><ProjectReference Include="..\library\GacReferenceFixture.csproj" /></ItemGroup></Project>' |
        Set-Content (Join-Path $hostDirectory 'GacReferenceHost.csproj')
    'using System; public static class Program { public static int Main() { string name = GacReferenceFixture.ReadType(); Console.WriteLine(name); return name == "System.Management.ManagementObject:3:AesCryptoServiceProvider" ? 0 : 1; } }' |
        Set-Content (Join-Path $hostDirectory 'Program.cs')
    dotnet build (Join-Path $hostDirectory 'GacReferenceHost.csproj') -c Release --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'GAC reference fixture build failed.' }
    $bin = Join-Path $hostDirectory 'bin\Release\net48'
    $rewritten = Join-Path $directory 'GacReferenceFixture.dll'
    dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- (Join-Path $bin 'GacReferenceFixture.dll') $rewritten
    if ($LASTEXITCODE -ne 0) { throw 'GAC reference emission failed.' }
    Copy-Item -LiteralPath $rewritten -Destination (Join-Path $bin 'GacReferenceFixture.dll')
    & (Join-Path $bin 'GacReferenceHost.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Original GAC reference resolution failed.' }
    $export = Join-Path $directory 'export'
    & $DnSpyConsole --no-color --sdk-project --threads 4 -o $export (Join-Path $bin 'GacReferenceFixture.dll')
    if ($LASTEXITCODE -ne 0) { throw 'GAC reference export failed.' }
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    [xml]$xml = Get-Content -LiteralPath $project.FullName -Raw
    $reference = $xml.SelectSingleNode('//*[local-name()="Reference" and @Include="System.Management"]')
    if (!$reference) { throw 'System.Management reference was lost.' }
    if ($framework -eq 'net48' -and $reference.HintPath) { throw '.NET Framework should keep its normal framework reference.' }
    if ($framework -eq 'netstandard2.0' -and !$reference.HintPath) { throw '.NET Standard requires the resolved non-framework reference path.' }
    $core = $xml.SelectSingleNode('//*[local-name()="Reference" and @Include="System.Core"]')
    if ($core -and $core.HintPath) { throw 'System.Core must resolve through target references, not a conflicting framework implementation.' }
    $rebuilt = Join-Path $directory 'rebuilt'
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Exported GAC reference source compilation failed.' }
    Copy-Item -LiteralPath (Join-Path $bin 'GacReferenceHost.exe') -Destination $rebuilt
    $config = Join-Path $bin 'GacReferenceHost.exe.config'
    if (Test-Path -LiteralPath $config) { Copy-Item -LiteralPath $config -Destination $rebuilt }
    & (Join-Path $rebuilt 'GacReferenceHost.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Rebuilt GAC reference resolution changed.' }
}
Write-Output 'PASS: .NET Framework and .NET Standard references rebuild and resolve System.Management under the original framework host.'
