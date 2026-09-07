param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory,
    [switch] $DispatchCalls
)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression output folder.'}
$inputDirectory=Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory -Path $inputDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'NestedAwaitFinallyFixture.cs') -Destination $inputDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $inputDirectory 'NestedAwaitFinallyFixture.csproj')
if ($DispatchCalls) {
    $fixtureProject=Join-Path $inputDirectory 'NestedAwaitFinallyFixture.csproj'
    (Get-Content $fixtureProject -Raw).Replace('</PropertyGroup>','<DefineConstants>DETACHED_DISPATCH</DefineConstants></PropertyGroup>') | Set-Content $fixtureProject
}
dotnet build $inputDirectory -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Cleanup fixture build failed.'}
$original=Join-Path $inputDirectory 'bin\Release\net48\NestedAwaitFinallyFixture.exe'
$hash=(Get-FileHash -LiteralPath $original).Hash
$expected=@(& $original)
if($LASTEXITCODE -ne 0){throw 'Original cleanup behavior failed.'}
$expected | Set-Content (Join-Path $OutputDirectory 'expected.txt')
$runtime=Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$emitter=Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $emitter | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitDetachedRethrows.cs') -Destination $emitter
$dnlib=[Security.SecurityElement]::Escape((Join-Path $runtime 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitter 'Emitter.csproj')
$variant=Join-Path $OutputDirectory 'detached'
Copy-Item -LiteralPath (Split-Path $original) -Destination $variant -Recurse
$inputAssembly=Join-Path $variant 'NestedAwaitFinallyFixture.exe'
$emitterArguments=@($original,$inputAssembly)
if ($DispatchCalls) { $emitterArguments+='dispatch' }
dotnet run --project (Join-Path $emitter 'Emitter.csproj') -c Release -- @emitterArguments
if($LASTEXITCODE -ne 0){throw 'Detached rethrow emission failed.'}
$variantHash=(Get-FileHash -LiteralPath $inputAssembly).Hash
$actual=@(& $inputAssembly)
if($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive)){throw 'Reordering changed input behavior.'}
foreach($threads in @(1,4)) {
    $export=Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $inputAssembly
    if($LASTEXITCODE -ne 0){throw 'Detached rethrow export failed.'}
    $source=Get-Content (Join-Path $export 'NestedAwaitFinallyFixture\NestedAwaitFinallyFixture.cs') -Raw
    if($source -match 'catch \(object' -or $source -match 'ExceptionDispatchInfo.Capture'){throw 'Captured cleanup rethrow was not recovered.'}
    $project=Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt=Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if($LASTEXITCODE -ne 0){throw 'Detached rethrow source compilation failed.'}
    $actual=@(& (Join-Path $rebuilt 'NestedAwaitFinallyFixture.exe'))
    if($LASTEXITCODE -ne 0){throw 'Rebuilt detached cleanup behavior failed.'}
    $actual | Set-Content (Join-Path $OutputDirectory "actual-$threads.txt")
    if(Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive){throw 'Detached cleanup behavior changed.'}
}
$debug=Join-Path $OutputDirectory 'debug'
New-Item -ItemType Directory -Path $debug | Out-Null
$debugFile=if ($DispatchCalls) { 'DetachedDispatchRethrowDebug.cs' } else { 'DetachedRethrowDebug.cs' }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot $debugFile) -Destination $debug
$references=('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path=[Security.SecurityElement]::Escape((Join-Path $runtime ($_+'.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
$debugArguments=@($original)
if ($DispatchCalls) {
    $normalized=Join-Path $OutputDirectory 'normalized'
    New-Item -ItemType Directory -Path $normalized | Out-Null
    $debugArguments+=(Join-Path $normalized 'Normalized.cs')
}
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- @debugArguments
if($LASTEXITCODE -ne 0){throw 'Detached rethrow safety/debug checks failed.'}
if ($DispatchCalls) {
    '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $normalized 'Normalized.csproj')
    dotnet build $normalized -c Release --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Normalized dispatch AST source did not compile.' }
    $actual=@(& (Join-Path $normalized 'bin\Release\net48\Normalized.exe'))
    if ($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive)) { throw 'Normalized dispatch AST changed behavior.' }
}
if((Get-FileHash -LiteralPath $original).Hash -ne $hash -or (Get-FileHash -LiteralPath $inputAssembly).Hash -ne $variantHash){throw 'Input assembly changed.'}
Write-Output $expected
