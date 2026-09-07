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
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'RepeatedInitializerFixture.cs') -Destination $inputDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $inputDirectory 'RepeatedInitializerFixture.csproj')
dotnet build (Join-Path $inputDirectory 'RepeatedInitializerFixture.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Repeated initializer fixture build failed.'}
$original=Join-Path $inputDirectory 'bin\Release\net48\RepeatedInitializerFixture.exe'
$originalHash=(Get-FileHash -LiteralPath $original).Hash
$expected=@(& $original)
if($LASTEXITCODE -ne 0){throw 'Repeated initializer reference behavior failed.'}
$expected | Set-Content (Join-Path $OutputDirectory 'expected.txt')
$runtime=Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$emitter=Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $emitter | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitRepeatedInitializer.cs') -Destination $emitter
$dnlib=[Security.SecurityElement]::Escape((Join-Path $runtime 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitter 'Emitter.csproj')
$variantDirectory=Join-Path $OutputDirectory 'renamed'
Copy-Item -LiteralPath (Split-Path $original) -Destination $variantDirectory -Recurse
$variant=Join-Path $variantDirectory 'RepeatedInitializerFixture.exe'
dotnet run --project (Join-Path $emitter 'Emitter.csproj') -c Release -- $original $variant
if($LASTEXITCODE -ne 0){throw 'Renamed accessor emission failed.'}
$variantHash=(Get-FileHash -LiteralPath $variant).Hash
$actual=@(& $variant)
if($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive)){throw 'Accessor renaming changed input behavior.'}
foreach($inputAssembly in @($original,$variant)) { foreach($threads in @(1,4)) {
    $name=if($inputAssembly -eq $original){'original'}else{'renamed'}
    $export=Join-Path $OutputDirectory "export-$name-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $inputAssembly
    if($LASTEXITCODE -ne 0){throw 'Repeated initializer export failed.'}
    $project=Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt=Join-Path $OutputDirectory "rebuilt-$name-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if($LASTEXITCODE -ne 0){throw 'Repeated initializer compilation failed.'}
    $actual=@(& (Join-Path $rebuilt 'RepeatedInitializerFixture.exe'))
    if($LASTEXITCODE -ne 0){throw 'Rebuilt repeated initializer source execution failed.'}
    $actual | Set-Content (Join-Path $OutputDirectory "actual-$name-$threads.txt")
    if(Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive){throw 'Rebuilt repeated initializer source values, aliases or side effects changed.'}
} }
$debug=Join-Path $OutputDirectory 'debug'
New-Item -ItemType Directory -Path $debug | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'RepeatedInitializerDebug.cs') -Destination $debug
$references=('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path=[Security.SecurityElement]::Escape((Join-Path $runtime ($_+'.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
foreach($inputAssembly in @($original,$variant)) {
    dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- $inputAssembly
    if($LASTEXITCODE -ne 0){throw 'Repeated initializer debug validation failed.'}
}
if((Get-FileHash -LiteralPath $original).Hash -ne $originalHash -or (Get-FileHash -LiteralPath $variant).Hash -ne $variantHash){throw 'Input assembly changed.'}
Write-Output ($expected[-1] + ' Original and renamed accessor exports match.')
