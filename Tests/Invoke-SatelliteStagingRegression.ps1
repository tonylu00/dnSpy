param([Parameter(Mandatory)][string]$DnSpyConsole, [Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new output directory.' }
$inputRoot = Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory -Path $inputRoot | Out-Null
'<Project />' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
$key = [Security.Cryptography.RSACryptoServiceProvider]::new(2048)
$key.PersistKeyInCsp = $false
try { [IO.File]::WriteAllBytes((Join-Path $OutputDirectory 'fixture.snk'), $key.ExportCspBlob($true)) } finally { $key.Dispose() }
foreach ($variant in @('Current','Compatibility')) {
    $source = Join-Path $OutputDirectory $variant
    New-Item -ItemType Directory -Path $source | Out-Null
    @'
using System;
using System.Globalization;
using System.Resources;
class Program {
    static int Main(string[] args) {
        var resources = new ResourceManager("Fixture.Text", typeof(Program).Assembly);
        CultureInfo.CurrentUICulture = CultureInfo.GetCultureInfo("zh-CN");
        var actual = resources.GetString("Greeting");
        Console.WriteLine(actual);
        return actual == args[0] ? 0 : 1;
    }
}
'@ | Set-Content (Join-Path $source 'Program.cs')
    @'
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><AssemblyName>Fixture</AssemblyName><RootNamespace>Fixture</RootNamespace><SignAssembly>true</SignAssembly><AssemblyOriginatorKeyFile>..\fixture.snk</AssemblyOriginatorKeyFile></PropertyGroup></Project>
'@ | Set-Content (Join-Path $source 'Fixture.csproj')
    foreach ($locale in @('','zh-CN')) {
        $value = if ($locale) { "$variant 中文" } else { "$variant English" }
        $suffix = if ($locale) { '.' + $locale } else { '' }
        "<root><resheader name=`"resmimetype`"><value>text/microsoft-resx</value></resheader><resheader name=`"version`"><value>2.0</value></resheader><resheader name=`"reader`"><value>System.Resources.ResXResourceReader, System.Windows.Forms</value></resheader><resheader name=`"writer`"><value>System.Resources.ResXResourceWriter, System.Windows.Forms</value></resheader><data name=`"Greeting`" xml:space=`"preserve`"><value>$value</value></data></root>" |
            Set-Content (Join-Path $source "Text$suffix.resx")
    }
    dotnet build (Join-Path $source 'Fixture.csproj') -c Release --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Fixture build failed.' }
    Copy-Item -LiteralPath (Join-Path $source 'bin\Release\net48') -Destination (Join-Path $inputRoot $variant) -Recurse
    New-Item -ItemType Directory -Path (Join-Path $inputRoot "$variant\empty") | Out-Null
    'unchanged data' | Set-Content (Join-Path $inputRoot "$variant\data.txt")
    & (Join-Path $inputRoot "$variant\Fixture.exe") "$variant 中文"
    if ($LASTEXITCODE -ne 0) { throw 'Original satellite lookup failed.' }
}
$inputs = @('Current','Compatibility') | ForEach-Object { Join-Path $inputRoot "$_\Fixture.exe" }
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export @inputs
    if ($LASTEXITCODE -ne 0) { throw 'Export failed.' }
    $solution = Get-ChildItem -LiteralPath $export -Filter '*.sln' | Select-Object -First 1
    dotnet build $solution.FullName -c Release --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Rebuild failed.' }
    $staged = Join-Path $OutputDirectory "staged-$threads"
    & (Join-Path $PSScriptRoot '..\Build\Stage-RecompiledTree.ps1') -InputDirectory $inputRoot -ExportDirectory $export -OutputDirectory $staged
    foreach ($variant in @('Current','Compatibility')) {
        & (Join-Path $staged "$variant\Fixture.exe") "$variant 中文"
        if ($LASTEXITCODE -ne 0) { throw "Satellite lookup failed in $variant context." }
    }
    $satellite = Get-ChildItem -LiteralPath $export -Recurse -File -Filter 'Fixture.resources.dll' |
        Where-Object FullName -like '*\bin\Release\*' | Select-Object -First 1
    $savedSatellite = $satellite.FullName + '.saved'
    Move-Item -LiteralPath $satellite.FullName -Destination $savedSatellite
    $incompleteOutput = Join-Path $OutputDirectory "incomplete-$threads"
    try {
        $rejected = $false
        try {
            & (Join-Path $PSScriptRoot '..\Build\Stage-RecompiledTree.ps1') -InputDirectory $inputRoot -ExportDirectory $export -OutputDirectory $incompleteOutput
        } catch {
            if ($_.Exception.Message -notlike 'Missing rebuilt satellite:*') { throw }
            $rejected = $true
        }
        if (!$rejected -or (Test-Path -LiteralPath $incompleteOutput)) { throw 'Missing satellite was not rejected before staging.' }
    } finally { Move-Item -LiteralPath $savedSatellite -Destination $satellite.FullName }
}
Write-Output 'PASS: signed inputs, unsigned rebuilds, duplicate assembly identities, culture fallback and tree preservation.'
