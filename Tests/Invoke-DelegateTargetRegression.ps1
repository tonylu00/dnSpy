param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$source = Join-Path $OutputDirectory 'source'; $emitter = Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $source,$emitter | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'DelegateTargetFixture.cs') -Destination $source
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitDelegateTarget.cs') -Destination $emitter
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $source 'DelegateTargetFixture.csproj')
$runtime = Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$dnlib = [Security.SecurityElement]::Escape((Join-Path $runtime 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitter 'Emitter.csproj')
dotnet build (Join-Path $source 'DelegateTargetFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Delegate target fixture compilation failed.' }
$original = Join-Path $source 'bin\Release\net48\DelegateTargetFixture.exe'
$inputExe = Join-Path $OutputDirectory 'DelegateTargetFixture.exe'
$expected = @(& $original)
if ($LASTEXITCODE -ne 0) { throw 'Original delegate target behavior failed.' }
$expected | Set-Content (Join-Path $OutputDirectory 'expected.txt')
dotnet run --project (Join-Path $emitter 'Emitter.csproj') -c Release -- $original $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Delegate target emission failed.' }
$emitted = @(& $inputExe)
if ($LASTEXITCODE -ne 0 -or (Compare-Object $expected $emitted -SyncWindow 0 -CaseSensitive)) { throw 'Erased delegate target behavior differs.' }
$hash = (Get-FileHash -LiteralPath $inputExe).Hash
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $inputExe
    if ($LASTEXITCODE -ne 0) { throw 'Delegate target export failed.' }
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Delegate target source compilation failed.' }
    $actual = @(& (Join-Path $rebuilt 'DelegateTargetFixture.exe'))
    if ($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive)) { throw 'Delegate target source behavior differs.' }
    $actual | Set-Content (Join-Path $OutputDirectory "actual-$threads.txt")
}
$debug = Join-Path $OutputDirectory 'debug'
New-Item -ItemType Directory -Path $debug | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'DelegateTargetDebug.cs') -Destination $debug
$references = ('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path = [Security.SecurityElement]::Escape((Join-Path $runtime ($_ + '.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- $inputExe (Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319')
if ($LASTEXITCODE -ne 0) { throw 'Delegate target debug validation failed.' }
if ((Get-FileHash -LiteralPath $inputExe).Hash -ne $hash) { throw 'Input assembly changed.' }
Write-Output 'PASS: original, erased and one/four-thread rebuilt delegate targets preserve receiver identity, results, dispatch, evaluation counts and null failures.'
