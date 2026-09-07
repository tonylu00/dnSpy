param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression output folder.'}
$inputDirectory=Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory -Path $inputDirectory | Out-Null
'<Project />' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'SplitCatchFixture.cs') -Destination $inputDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $inputDirectory 'SplitCatchFixture.csproj')
dotnet build $inputDirectory -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Split catch fixture build failed.'}
$original=Join-Path $inputDirectory 'bin\Release\net48\SplitCatchFixture.exe'
$hash=(Get-FileHash -LiteralPath $original).Hash
$expected=@(& $original)
if($LASTEXITCODE -ne 0){throw 'Original split catch behavior failed.'}
$expected | Set-Content (Join-Path $OutputDirectory 'expected.txt')
$runtime=Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$emitter=Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $emitter | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitSplitCatch.cs') -Destination $emitter
$dnlib=[Security.SecurityElement]::Escape((Join-Path $runtime 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitter 'Emitter.csproj')
$variant=Join-Path $OutputDirectory 'split'
Copy-Item -LiteralPath (Split-Path $original) -Destination $variant -Recurse
$inputAssembly=Join-Path $variant 'SplitCatchFixture.exe'
dotnet run --project (Join-Path $emitter 'Emitter.csproj') -c Release -- $original $inputAssembly
if($LASTEXITCODE -ne 0){throw 'Split rethrow emission failed.'}
$variantHash=(Get-FileHash -LiteralPath $inputAssembly).Hash
$actual=@(& $inputAssembly)
if($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive)){throw 'Raw throw emission changed input behavior.'}
foreach($threads in @(1,4)) {
    $export=Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $inputAssembly
    if($LASTEXITCODE -ne 0){throw 'Split rethrow export failed.'}
    $source=Get-Content (Join-Path $export 'SplitCatchFixture\SplitCatchFixture.cs') -Raw
    $project=Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt=Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if($LASTEXITCODE -ne 0){throw 'Split rethrow source compilation failed.'}
    if($source -match 'catch \(object' -or $source -match 'ExceptionDispatchInfo.Capture'){throw 'Captured split catch rethrow was not recovered.'}
    $actual=@(& (Join-Path $rebuilt 'SplitCatchFixture.exe'))
    if($LASTEXITCODE -ne 0){throw 'Rebuilt split catch behavior failed.'}
    $actual | Set-Content (Join-Path $OutputDirectory "actual-$threads.txt")
    if(Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive){throw 'Split catch behavior changed.'}
}
$debug=Join-Path $OutputDirectory 'debug'
New-Item -ItemType Directory -Path $debug | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'SplitCatchDebug.cs') -Destination $debug
$references=('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path=[Security.SecurityElement]::Escape((Join-Path $runtime ($_+'.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- $inputAssembly
if($LASTEXITCODE -ne 0){throw 'Split rethrow safety/debug checks failed.'}
if((Get-FileHash -LiteralPath $original).Hash -ne $hash -or (Get-FileHash -LiteralPath $inputAssembly).Hash -ne $variantHash){throw 'Input assembly changed.'}
Write-Output $expected

