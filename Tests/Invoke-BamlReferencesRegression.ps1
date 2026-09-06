param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$inputDirectory = Join-Path $OutputDirectory 'input'
$libraryDirectory = Join-Path $OutputDirectory 'library'
New-Item -ItemType Directory -Path $inputDirectory,$libraryDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'BamlReferencesFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'BamlReferencesDictionary.xaml') -Destination (Join-Path $inputDirectory 'Dictionary.xaml')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework></PropertyGroup></Project>' |
    Set-Content (Join-Path $libraryDirectory 'XamlValues.csproj')
'namespace OnlyBaml { public static class Provider { public static string Text { get { return "compiled through BAML"; } } } }' |
    Set-Content (Join-Path $libraryDirectory 'Provider.cs')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><UseWPF>true</UseWPF><Optimize>true</Optimize></PropertyGroup><ItemGroup><ProjectReference Include="..\library\XamlValues.csproj" /></ItemGroup></Project>' |
    Set-Content (Join-Path $inputDirectory 'BamlReferencesFixture.csproj')
dotnet build (Join-Path $inputDirectory 'BamlReferencesFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'BAML reference fixture build failed.' }
$bin = Join-Path $inputDirectory 'bin\Release\net48'
$inputExe = Join-Path $bin 'BamlReferencesFixture.exe'
& $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Original BAML-only resource behavior failed.' }
foreach ($format in @('sdk','traditional')) {
    foreach ($mode in @('single','batch')) {
        $export = Join-Path $OutputDirectory ($format + '-' + $mode)
        $arguments = @('--no-color','--threads','4','-o',$export)
        if ($format -eq 'sdk') { $arguments += '--sdk-project' }
        $arguments += $inputExe
        if ($mode -eq 'batch') { $arguments += Join-Path $bin 'XamlValues.dll' }
        & $DnSpyConsole @arguments
        if ($LASTEXITCODE -ne 0) { throw 'BAML reference export failed.' }
        $project = Get-ChildItem -LiteralPath $export -Recurse -Filter 'BamlReferencesFixture.csproj' | Select-Object -First 1
        [xml]$xml = Get-Content -LiteralPath $project.FullName -Raw
        $references = $xml.SelectNodes('//*[local-name()="Reference" and @Include="XamlValues"]')
        $projectReferences = $xml.SelectNodes('//*[local-name()="ProjectReference"]') | Where-Object { $_.Include -match 'XamlValues' }
        if ($mode -eq 'batch') {
            if (@($projectReferences).Count -ne 1 -or $references.Count -ne 0) { throw 'BAML-only batch dependency must have exactly one project reference.' }
        } else {
            if ($references.Count -ne 1 -or !$references[0].HintPath) { throw 'BAML-only binary dependency must have a resolved hint path.' }
        }
        if ($format -eq 'sdk') {
            $rebuilt = Join-Path $export 'rebuilt'
            dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
            if ($LASTEXITCODE -ne 0) { throw 'Exported BAML-only source compilation failed.' }
            & (Join-Path $rebuilt 'BamlReferencesFixture.exe')
            if ($LASTEXITCODE -ne 0) { throw 'Rebuilt BAML-only resource behavior changed.' }
        }
    }
}
Write-Output 'PASS: SDK and traditional single/batch exports retain BAML-only reference identities; both SDK outputs rebuild and execute.'
