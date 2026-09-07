param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$inputDirectory = Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory -Path $inputDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'GuardedAwaitFixture.cs') -Destination $inputDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' |
    Set-Content -LiteralPath (Join-Path $inputDirectory 'GuardedAwaitFixture.csproj')
dotnet build (Join-Path $inputDirectory 'GuardedAwaitFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Fixture compilation failed.' }
$inputExe = Join-Path $inputDirectory 'bin\Release\net48\GuardedAwaitFixture.exe'
$inputHash = (Get-FileHash -LiteralPath $inputExe).Hash
& $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Original guarded async behavior failed.' }
foreach ($threads in @(1,4)) {
    $exportDirectory = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $exportDirectory $inputExe
    if ($LASTEXITCODE -ne 0) { throw 'dnSpy export failed.' }
    $source = Get-Content (Join-Path $exportDirectory 'GuardedAwaitFixture\GuardedAwaitFixture.cs') -Raw
    if ($source -notmatch 'async Task<int> Read\(') { throw 'Guarded detached await was not reconstructed.' }
    $project = Get-ChildItem -LiteralPath $exportDirectory -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Exported guarded async source compilation failed.' }
    & (Join-Path $rebuilt 'GuardedAwaitFixture.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Rebuilt guarded async behavior changed.' }
}
$debug = Join-Path $OutputDirectory 'debug'
New-Item -ItemType Directory -Path $debug | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'GuardedAwaitDebug.cs') -Destination $debug
$runtime = Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$references = ('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path = [Security.SecurityElement]::Escape((Join-Path $runtime ($_ + '.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Guarded await debug validation failed.' }
if ((Get-FileHash -LiteralPath $inputExe).Hash -ne $inputHash) { throw 'Input assembly changed.' }
