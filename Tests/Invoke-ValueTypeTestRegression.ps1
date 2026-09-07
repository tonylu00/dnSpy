param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression output folder.'}
$inputDirectory=Join-Path $OutputDirectory 'input'; $emitter=Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $inputDirectory,$emitter | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ValueTypeTestFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitValueTypeTests.cs') -Destination $emitter
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $inputDirectory 'ValueTypeTestFixture.csproj')
$runtime=Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$dnlib=[Security.SecurityElement]::Escape((Join-Path $runtime 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitter 'Emitter.csproj')
dotnet build (Join-Path $inputDirectory 'ValueTypeTestFixture.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Value type test fixture compilation failed.'}
$original=Join-Path $OutputDirectory 'ValueTypeTestFixture.exe'
dotnet run --project (Join-Path $emitter 'Emitter.csproj') -c Release -- (Join-Path $inputDirectory 'bin\Release\net48\ValueTypeTestFixture.exe') $original
if($LASTEXITCODE -ne 0){throw 'Value type test emission failed.'}
$expected=@(& $original)
if($LASTEXITCODE -ne 0){throw 'Emitted type-test behavior failed.'}
$expected | Set-Content (Join-Path $OutputDirectory 'expected.txt')
foreach($threads in @(1,4)) {
    $export=Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
    if($LASTEXITCODE -ne 0){throw 'Value type test export failed.'}
    $project=Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt=Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if($LASTEXITCODE -ne 0){throw 'Value type test source compilation failed.'}
    $actual=@(& (Join-Path $rebuilt 'ValueTypeTestFixture.exe'))
    if($LASTEXITCODE -ne 0){throw 'Value type test source behavior failed.'}
    $actual | Set-Content (Join-Path $OutputDirectory "actual-$threads.txt")
    if(Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive){throw 'Value type test results differ.'}
}
$debug=Join-Path $OutputDirectory 'debug'
New-Item -ItemType Directory -Path $debug | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ValueTypeTestDebug.cs') -Destination $debug
$references=('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path=[Security.SecurityElement]::Escape((Join-Path $runtime ($_+'.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- $original (Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319')
if($LASTEXITCODE -ne 0){throw 'Type test debug validation failed.'}
Write-Output $expected
