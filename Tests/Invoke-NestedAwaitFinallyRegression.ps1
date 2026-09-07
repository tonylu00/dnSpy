param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression output folder.'}
$inputDirectory=Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory -Path $inputDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'NestedAwaitFinallyFixture.cs') -Destination $inputDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $inputDirectory 'NestedAwaitFinallyFixture.csproj')
dotnet build (Join-Path $inputDirectory 'NestedAwaitFinallyFixture.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Nested await-finally fixture build failed.'}
$original=Join-Path $inputDirectory 'bin\Release\net48\NestedAwaitFinallyFixture.exe'
$expected=@(& $original)
if($LASTEXITCODE -ne 0){throw 'Nested await-finally reference behavior failed.'}
$expected | Set-Content (Join-Path $OutputDirectory 'expected.txt')
foreach($threads in @(1,4)) {
    $export=Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
    if($LASTEXITCODE -ne 0){throw 'Nested await-finally export failed.'}
    $project=Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt=Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if($LASTEXITCODE -ne 0){throw 'Nested await-finally source compilation failed.'}
    $actual=@(& (Join-Path $rebuilt 'NestedAwaitFinallyFixture.exe'))
    if($LASTEXITCODE -ne 0){throw 'Rebuilt nested await-finally execution failed.'}
    $actual | Set-Content (Join-Path $OutputDirectory "actual-$threads.txt")
    if(Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive){throw 'Nested await-finally behavior changed.'}
}
$debug=Join-Path $OutputDirectory 'debug'
New-Item -ItemType Directory -Path $debug | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'NestedAwaitFinallyDebug.cs') -Destination $debug
$runtime=Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$references=('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path=[Security.SecurityElement]::Escape((Join-Path $runtime ($_+'.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- $original (Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319')
if($LASTEXITCODE -ne 0){throw 'Nested await-finally reuse guards failed.'}
Write-Output $expected
