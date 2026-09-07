param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$interop = Join-Path $OutputDirectory 'interop'
$inputDirectory = Join-Path $OutputDirectory 'input'
$verifier = Join-Path $OutputDirectory 'verifier'
$debug = Join-Path $OutputDirectory 'debug'
$baseline = Join-Path $OutputDirectory 'baseline'
New-Item -ItemType Directory -Path $interop,$inputDirectory,$verifier,$debug,$baseline | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmbeddedEventInterop.cs') -Destination $interop
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmbeddedEventFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmbeddedEventVerifier.cs') -Destination $verifier
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmbeddedEventDebug.cs') -Destination $debug
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework></PropertyGroup></Project>' | Set-Content (Join-Path $interop 'Interop.csproj')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><Optimize>true</Optimize></PropertyGroup><ItemGroup><ProjectReference Include="..\interop\Interop.csproj"><EmbedInteropTypes>true</EmbedInteropTypes><Private>false</Private></ProjectReference></ItemGroup></Project>' | Set-Content (Join-Path $inputDirectory 'EmbeddedEventFixture.csproj')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType></PropertyGroup></Project>' | Set-Content (Join-Path $verifier 'Verifier.csproj')
dotnet build (Join-Path $inputDirectory 'EmbeddedEventFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Embedded interop fixture build failed.' }
dotnet build (Join-Path $verifier 'Verifier.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Embedded interop verifier build failed.' }
$inputDll = Join-Path $inputDirectory 'bin\Release\net48\EmbeddedEventFixture.dll'
$inputHash = (Get-FileHash -LiteralPath $inputDll).Hash
$verifyExe = Join-Path $verifier 'bin\Release\net48\Verifier.exe'
Copy-Item -LiteralPath $inputDll -Destination $baseline
& $verifyExe $inputDll (Join-Path $baseline 'EmbeddedEventFixture.dll') --original
if ($LASTEXITCODE -ne 0) { throw 'Original embedded interop behavior failed.' }
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $inputDll
    if ($LASTEXITCODE -ne 0) { throw 'Embedded interop export failed.' }
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Embedded interop source build failed.' }
    & $verifyExe $inputDll (Join-Path $rebuilt 'EmbeddedEventFixture.dll')
    if ($LASTEXITCODE -ne 0) { throw 'Rebuilt embedded interop behavior changed.' }
}
$runtime = Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$references = ('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path = [Security.SecurityElement]::Escape((Join-Path $runtime ($_ + '.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- $inputDll
if ($LASTEXITCODE -ne 0) { throw 'Embedded event source guard checks failed.' }
if ((Get-FileHash -LiteralPath $inputDll).Hash -ne $inputHash) { throw 'Embedded input was modified.' }
