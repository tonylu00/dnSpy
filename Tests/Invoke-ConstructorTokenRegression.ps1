param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$source = Join-Path $OutputDirectory 'source'
New-Item -ItemType Directory -Path $source | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ConstructorTokenFixture.cs') -Destination $source
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><Optimize>true</Optimize><AllowUnsafeBlocks>true</AllowUnsafeBlocks><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $source 'ConstructorTokenFixture.csproj')
dotnet build (Join-Path $source 'ConstructorTokenFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Constructor token fixture compilation failed.' }
$original = Join-Path $source 'bin\Release\net48\ConstructorTokenFixture.dll'
# Keep the behavioral harness outside the export and run the same binary
# against the original, token-emitted and rebuilt fixture implementations.
$runner = Join-Path $OutputDirectory 'runner'
New-Item -ItemType Directory -Path $runner | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ConstructorTokenRunner.cs') -Destination $runner
$reference = [Security.SecurityElement]::Escape($original)
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><AllowUnsafeBlocks>true</AllowUnsafeBlocks><LangVersion>latest</LangVersion></PropertyGroup><ItemGroup><Reference Include=`"ConstructorTokenFixture`"><HintPath>$reference</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $runner 'Runner.csproj')
dotnet build (Join-Path $runner 'Runner.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Constructor token runner compilation failed.' }
$runnerExe = Join-Path $runner 'bin\Release\net48\Runner.exe'
$expected = @(& $runnerExe)
if ($LASTEXITCODE -ne 0) { throw 'Original constructor token behavior failed.' }
$expected | Set-Content (Join-Path $OutputDirectory 'expected.txt')
$emitter = Join-Path $OutputDirectory 'emitter'; $inputDirectory = Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory -Path $emitter,$inputDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitConstructorToken.cs') -Destination $emitter
$runtime = Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$dnlib = [Security.SecurityElement]::Escape((Join-Path $runtime 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitter 'Emitter.csproj')
$emitted = Join-Path $inputDirectory 'ConstructorTokenFixture.dll'
dotnet run --project (Join-Path $emitter 'Emitter.csproj') -c Release -- $original $emitted
if ($LASTEXITCODE -ne 0) { throw 'Constructor token emission failed.' }
Copy-Item -LiteralPath $runnerExe -Destination $inputDirectory
$actual = @(& (Join-Path $inputDirectory 'Runner.exe'))
if ($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive)) { throw 'Emitted constructor token behavior differs.' }
$original = $emitted
$hash = (Get-FileHash -LiteralPath $original).Hash
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
    if ($LASTEXITCODE -ne 0) { throw 'Constructor token export failed.' }
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Constructor token source compilation failed.' }
    Copy-Item -LiteralPath $runnerExe -Destination $rebuilt
    $actual = @(& (Join-Path $rebuilt 'Runner.exe'))
    if ($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive)) { throw 'Constructor token source behavior differs.' }
    $actual | Set-Content (Join-Path $OutputDirectory "actual-$threads.txt")
}
$debug = Join-Path $OutputDirectory 'debug'
New-Item -ItemType Directory -Path $debug | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ConstructorTokenDebug.cs') -Destination $debug
$runtime = Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$references = ('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path = [Security.SecurityElement]::Escape((Join-Path $runtime ($_ + '.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- $original (Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319')
if ($LASTEXITCODE -ne 0) { throw 'Constructor token debug validation failed.' }
if ((Get-FileHash -LiteralPath $original).Hash -ne $hash) { throw 'Input assembly changed.' }
Write-Output $expected

