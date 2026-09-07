param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory,
    [switch] $ShareIntermediate
)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression output folder.'}
$inputDirectory=Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory -Path $inputDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'PendingCatchReuseFixture.cs') -Destination $inputDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $inputDirectory 'PendingCatchReuseFixture.csproj')
dotnet build $inputDirectory -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Catch fixture build failed.'}
$original=Join-Path $inputDirectory 'bin\Release\net48\PendingCatchReuseFixture.exe'
$hash=(Get-FileHash -LiteralPath $original).Hash
$expected=@(& $original)
if($LASTEXITCODE -ne 0){throw 'Original catch behavior failed.'}
$expected | Set-Content (Join-Path $OutputDirectory 'expected.txt')
$runtime=Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$inputAssembly=$original
if ($ShareIntermediate) {
    $emitter=Join-Path $OutputDirectory 'emitter'
    New-Item -ItemType Directory -Path $emitter | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitSharedCaptureFinally.cs') -Destination $emitter
    $dnlib=[Security.SecurityElement]::Escape((Join-Path $runtime 'dnlib.dll'))
    "<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitter 'Emitter.csproj')
    $variant=Join-Path $OutputDirectory 'shared'
    Copy-Item -LiteralPath (Split-Path $original) -Destination $variant -Recurse
    $inputAssembly=Join-Path $variant 'PendingCatchReuseFixture.exe'
    dotnet run --project (Join-Path $emitter 'Emitter.csproj') -c Release -- $original $inputAssembly 3 3 independent-catch
    if ($LASTEXITCODE -ne 0) { throw 'Independent intermediate capture emission failed.' }
    $actual=@(& $inputAssembly)
    if ($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive)) { throw 'Intermediate sharing changed input behavior.' }
}
$variantHash=(Get-FileHash -LiteralPath $inputAssembly).Hash
foreach($threads in @(1,4)) {
    $export=Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $inputAssembly
    if($LASTEXITCODE -ne 0){throw 'Independent pending catch rethrow export failed.'}
    $source=Get-Content (Join-Path $export 'PendingCatchReuseFixture\PendingCatchReuseFixture.cs') -Raw
    if($source -match 'catch \(object' -or $source -match 'ExceptionDispatchInfo.Capture'){throw 'Captured catch rethrow was not recovered.'}
    $project=Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt=Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if($LASTEXITCODE -ne 0){throw 'Independent pending catch rethrow source compilation failed.'}
    $actual=@(& (Join-Path $rebuilt 'PendingCatchReuseFixture.exe'))
    if($LASTEXITCODE -ne 0){throw 'Rebuilt independent pending catch behavior failed.'}
    $actual | Set-Content (Join-Path $OutputDirectory "actual-$threads.txt")
    if(Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive){throw 'Independent pending catch behavior changed.'}
}
$debug=Join-Path $OutputDirectory 'debug'
New-Item -ItemType Directory -Path $debug | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'PendingCatchReuseDebug.cs') -Destination $debug
$references=('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path=[Security.SecurityElement]::Escape((Join-Path $runtime ($_+'.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
$debugArguments=@($inputAssembly)
if ($ShareIntermediate) { $debugArguments+='shared' }
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- @debugArguments
if($LASTEXITCODE -ne 0){throw 'Independent pending catch rethrow safety/debug checks failed.'}
if((Get-FileHash -LiteralPath $original).Hash -ne $hash){throw 'Input assembly changed.'}
if((Get-FileHash -LiteralPath $inputAssembly).Hash -ne $variantHash){throw 'Variant assembly changed.'}
Write-Output $expected
