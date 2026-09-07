param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory,
    [string] $CompilerEnvironment
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
if (!$CompilerEnvironment) {
    $locator = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
    $installation = @(& $locator -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath)[0]
    if (!$installation) { throw 'A Visual C++ installation with C++/CLI support is required.' }
    $CompilerEnvironment = Join-Path $installation 'Common7\Tools\VsDevCmd.bat'
}
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
'<Project><PropertyGroup><BaseIntermediateOutputPath>obj\$(MSBuildProjectName)\</BaseIntermediateOutputPath></PropertyGroup></Project>' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
$key = Join-Path $OutputDirectory 'fixture.snk'
$keyParameters = [Security.Cryptography.CspParameters]::new()
$keyParameters.KeyNumber = 2
$rsa = [Security.Cryptography.RSACryptoServiceProvider]::new(2048, $keyParameters)
try { $rsa.PersistKeyInCsp = $false; [IO.File]::WriteAllBytes($key, $rsa.ExportCspBlob($true)) }
finally { $rsa.Dispose() }
$keyHolder = Join-Path $OutputDirectory 'key-holder'
New-Item -ItemType Directory -Path $keyHolder | Out-Null
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><SignAssembly>true</SignAssembly><AssemblyOriginatorKeyFile>..\fixture.snk</AssemblyOriginatorKeyFile></PropertyGroup></Project>' | Set-Content (Join-Path $keyHolder 'KeyHolder.csproj')
'internal class KeyHolder {}' | Set-Content (Join-Path $keyHolder 'KeyHolder.cs')
dotnet build (Join-Path $keyHolder 'KeyHolder.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Signing-key fixture compilation failed.' }
$publicKey = [BitConverter]::ToString([Reflection.AssemblyName]::GetAssemblyName((Join-Path $keyHolder 'bin\Release\net48\KeyHolder.dll')).GetPublicKey()).Replace('-', '')
$inputs = @(); $expectedBySource = @{}; $inputHashes = @{}
foreach ($layout in @('root', 'compat')) {
    $native = Join-Path $OutputDirectory "native-$layout"
    $source = Join-Path $OutputDirectory "source-$layout"
    $inputDirectory = Join-Path (Join-Path $OutputDirectory 'input') $layout
    New-Item -ItemType Directory -Path $native,$source,$inputDirectory | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'NativeBridgeFixture.cpp') -Destination (Join-Path $native 'NativeBridge.cpp')
    Copy-Item -LiteralPath $key -Destination (Join-Path $native 'fixture.snk')
    $buildNative = Join-Path $native 'Build.cmd'
    @"
@echo off
call "$CompilerEnvironment" -no_logo -arch=x64
if errorlevel 1 exit /b %errorlevel%
cl.exe /nologo /LD /clr /MD /EHa /Od /DNATIVE_RESULT=%1 "%~dp0NativeBridge.cpp" /Fo"%~dp0NativeBridge.obj" /Fe"%~dp0NativeBridge.dll" /link /INCREMENTAL:NO /KEYFILE:"%~dp0fixture.snk"
"@ | Set-Content -LiteralPath $buildNative -Encoding ascii
    $nativeValue = if ($layout -eq 'root') { 42 } else { 67 }
    & $buildNative $nativeValue
    if ($LASTEXITCODE -ne 0) { throw 'Native C++/CLI fixture compilation failed.' }
    $nativeReference = [Security.SecurityElement]::Escape((Join-Path $native 'NativeBridge.dll'))
    '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><SignAssembly>true</SignAssembly><AssemblyOriginatorKeyFile>..\fixture.snk</AssemblyOriginatorKeyFile><GenerateTargetFrameworkAttribute>false</GenerateTargetFrameworkAttribute><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup><Compile Include="ManagedHelper.cs" /></ItemGroup></Project>' |
        Set-Content (Join-Path $source 'ManagedHelper.csproj')
    "[assembly: System.Runtime.CompilerServices.InternalsVisibleTo(`"App, PublicKey=$publicKey`")] [assembly: System.Runtime.CompilerServices.InternalsVisibleTo(`"NativeBridge, PublicKey=$publicKey`")] public static class ManagedHelper { [System.Runtime.InteropServices.DllImport(`"kernel32.dll`")] static extern uint GetCurrentProcessId(); internal static int Read() { return GetCurrentProcessId() != 0 ? 2 : 0; } }" |
        Set-Content (Join-Path $source 'ManagedHelper.cs')
    "<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net48</TargetFramework><SignAssembly>true</SignAssembly><AssemblyOriginatorKeyFile>..\fixture.snk</AssemblyOriginatorKeyFile><OutputType>Exe</OutputType><PlatformTarget>x64</PlatformTarget><GenerateTargetFrameworkAttribute>false</GenerateTargetFrameworkAttribute><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup><Compile Include=`"App.cs`" /><ProjectReference Include=`"ManagedHelper.csproj`" /><Reference Include=`"NativeBridge`"><HintPath>$nativeReference</HintPath></Reference></ItemGroup></Project>" |
        Set-Content (Join-Path $source 'App.csproj')
    'public static class App { public static int Main() { return NativeBridge.Read() + ManagedHelper.Read(); } }' |
        Set-Content (Join-Path $source 'App.cs')
    dotnet build (Join-Path $source 'App.csproj') -c Release -p:UseArtifactsOutput=false -o $inputDirectory --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Managed consumer fixture compilation failed.' }
    & (Join-Path $inputDirectory 'App.exe')
    if ($LASTEXITCODE -ne ($nativeValue + 2)) { throw 'Original native fixture behavior failed.' }
    $expectedBySource[(Join-Path $inputDirectory 'NativeBridge.dll')] = $nativeValue + 2
    foreach ($name in @('App.exe', 'NativeBridge.dll', 'ManagedHelper.dll')) {
        $file = Join-Path $inputDirectory $name
        $inputs += $file; $inputHashes[$file] = (Get-FileHash -LiteralPath $file).Hash
    }
}
foreach ($sdk in @($true, $false)) { foreach ($threads in @(1, 4)) {
    $export = Join-Path $OutputDirectory "export-$sdk-$threads"
    $options = @('--no-color', '--threads', $threads, '-o', $export)
    if ($sdk) { $options += '--sdk-project' }
    & $DnSpyConsole @options @inputs
    if ($LASTEXITCODE -ne 0) { throw 'Native-reference export failed.' }
    $manifests = @(Get-ChildItem -LiteralPath $export -Recurse -Filter '*.reference.xml')
    if ($manifests.Count -ne 2) { throw 'Each native compatibility copy must be preserved separately.' }
    $expectedByCopy = @{}
    foreach ($file in $manifests) {
        [xml]$manifest = Get-Content -LiteralPath $file.FullName -Raw
        $nativeCopy = Join-Path $file.DirectoryName $manifest.NativeAssemblyReference.Binary
        $original = $manifest.NativeAssemblyReference.Source
        if (!$expectedBySource.ContainsKey($original)) { throw 'Native source mapping is incorrect.' }
        if ((Get-FileHash -LiteralPath $nativeCopy).Hash -ne $inputHashes[$original]) { throw 'Native implementation was changed.' }
        $expectedByCopy[[IO.Path]::GetFullPath($nativeCopy)] = $expectedBySource[$original]
    }
    $projects = @(Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj')
    if ($projects.Count -ne 4) { throw 'Only the four managed consumer/helper projects should compile.' }
    $solution = Get-ChildItem -LiteralPath $export -Filter '*.sln' | Select-Object -First 1
    dotnet build $solution.FullName -c Release -p:UseArtifactsOutput=false --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Native-reference source compilation failed.' }
    $executed = 0
    foreach ($project in $projects) {
        [xml]$document = Get-Content -LiteralPath $project.FullName -Raw
        $name = $document.SelectSingleNode('//*[local-name()="AssemblyName"]').InnerText
        if ($name -eq 'ManagedHelper') {
            $info = Get-Content (Join-Path $project.DirectoryName 'Properties\AssemblyInfo.cs') -Raw
            if ($info -notmatch [regex]::Escape("NativeBridge, PublicKey=$publicKey") -or $info -notmatch 'InternalsVisibleTo\("App"\)') {
                throw 'Native friend keys must remain while recompiled managed friend names adapt.'
            }
        }
        $reference = $document.SelectSingleNode('//*[local-name()="Reference" and @Include="NativeBridge"]')
        if (!$reference) { continue }
        $hint = $reference.SelectSingleNode('*[local-name()="HintPath"]').InnerText
        $nativeCopy = [IO.Path]::GetFullPath((Join-Path $project.DirectoryName $hint))
        if (!$expectedByCopy.ContainsKey($nativeCopy)) { throw 'Project still references an original native input.' }
        $target = $document.SelectSingleNode('//*[local-name()="TargetFramework" or local-name()="TargetFrameworkVersion"]').InnerText
        if ($target -notin @('net48', 'v4.8')) { throw 'Framework inference did not follow the native dependency.' }
        $exe = Get-ChildItem -LiteralPath (Join-Path $project.DirectoryName 'bin') -Recurse -Filter App.exe | Select-Object -First 1
        & $exe.FullName
        if ($LASTEXITCODE -ne $expectedByCopy[$nativeCopy]) { throw 'Rebuilt compatibility consumer used the wrong native implementation.' }
        $executed++
    }
    if ($executed -ne 2) { throw 'Both native compatibility consumers must execute.' }
} }
foreach ($file in $inputHashes.Keys) {
    if ((Get-FileHash -LiteralPath $file).Hash -ne $inputHashes[$file]) { throw 'Input file changed.' }
}
Write-Output 'PASS: signed native implementations, compatibility bindings, friend grants, managed P/Invoke source and inferred framework targets survive four export/rebuild variants.'
