param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression output folder.'}
$inputDirectory=Join-Path $OutputDirectory 'input'
$emitterDirectory=Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $inputDirectory,$emitterDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'LoopExitFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitLoopExit.cs') -Destination $emitterDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' | Set-Content (Join-Path $inputDirectory 'LoopExitFixture.csproj')
$runtime=Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$dnlib=[Security.SecurityElement]::Escape((Join-Path $runtime 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
dotnet build (Join-Path $inputDirectory 'LoopExitFixture.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Loop exit fixture build failed.'}
$source=Join-Path $inputDirectory 'bin\Release\net48\LoopExitFixture.exe'
$original=Join-Path $OutputDirectory 'LoopExitFixture.exe'
dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- $source $original
if($LASTEXITCODE -ne 0){throw 'Loop exit layout modification failed.'}
$expected=@(& $source)
if($LASTEXITCODE -ne 0){throw 'Loop exit reference behavior failed.'}
$modified=@(& $original)
if($LASTEXITCODE -ne 0 -or (Compare-Object $expected $modified -SyncWindow 0)){throw 'Loop exit layout changed input behavior.'}
$expected | Set-Content (Join-Path $OutputDirectory 'expected.txt')
foreach($threads in @(1,4)) {
    $export=Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
    if($LASTEXITCODE -ne 0){throw 'Loop exit export failed.'}
    $project=Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt=Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if($LASTEXITCODE -ne 0){throw 'Loop exit source compilation failed.'}
    $actual=@(& (Join-Path $rebuilt 'LoopExitFixture.exe'))
    if($LASTEXITCODE -ne 0){throw 'Rebuilt loop exit execution failed.'}
    $actual | Set-Content (Join-Path $OutputDirectory "actual-$threads.txt")
    if(Compare-Object $expected $actual -SyncWindow 0){throw 'Rebuilt loop exit values, side effects or cleanup changed.'}
}
$debug=Join-Path $OutputDirectory 'debug'
New-Item -ItemType Directory -Path $debug | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'LoopExitDebug.cs') -Destination $debug
$references=('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path=[Security.SecurityElement]::Escape((Join-Path $runtime ($_+'.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- $original
if($LASTEXITCODE -ne 0){throw 'Loop exit control-flow or debug transformation failed.'}
Write-Output ('PASS: ' + $expected[-1] + ', source and modified IL match both rebuilt exports.')
