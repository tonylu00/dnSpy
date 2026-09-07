param([Parameter(Mandatory)][string] $DnSpyConsole, [Parameter(Mandatory)][string] $OutputDirectory)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$source = Join-Path $OutputDirectory 'source'; $debug = Join-Path $OutputDirectory 'debug'
New-Item -ItemType Directory -Path $source,$debug | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EscapedClosureFixture.cs') -Destination $source
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EscapedClosureDebug.cs') -Destination $debug
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $source 'EscapedClosureFixture.csproj')
dotnet build (Join-Path $source 'EscapedClosureFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Capture fixture build failed.' }
$original = Join-Path $source 'bin\Release\net48\EscapedClosureFixture.exe'
$expected = @(& $original)
if ($LASTEXITCODE -ne 0) { throw 'Original capture behavior failed.' }
$expected | Set-Content (Join-Path $OutputDirectory 'expected.txt')
$hash = (Get-FileHash -LiteralPath $original).Hash
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
    if ($LASTEXITCODE -ne 0) { throw 'Capture export failed.' }
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Capture source compilation failed.' }
    $actual = @(& (Join-Path $rebuilt 'EscapedClosureFixture.exe'))
    if ($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive)) { throw 'Rebuilt capture behavior differs.' }
    $actual | Set-Content (Join-Path $OutputDirectory "actual-$threads.txt")
}
$runtime = Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$references = ('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path = [Security.SecurityElement]::Escape((Join-Path $runtime ($_ + '.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- $original
if ($LASTEXITCODE -ne 0) { throw 'Capture AST validation failed.' }
if ((Get-FileHash -LiteralPath $original).Hash -ne $hash) { throw 'Capture input assembly changed.' }
Write-Output 'PASS: original and one/four-thread rebuilt captures preserve state beyond their allocation blocks.'
