param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression output folder.'}
$emitter=Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $emitter | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitCatchWrapping.cs') -Destination $emitter
$dnlib=[Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitter 'Emitter.csproj')
foreach($variant in @('wrapped','unwrapped','absent','default')) {
    $inputDirectory=Join-Path $OutputDirectory $variant
    New-Item -ItemType Directory -Path $inputDirectory | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'TypedAwaitCatchFixture.cs') -Destination $inputDirectory
    $constants=if($variant -eq 'wrapped'){'WRAP'}else{''}
    "<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion><DefineConstants>$constants</DefineConstants></PropertyGroup></Project>" | Set-Content (Join-Path $inputDirectory 'TypedAwaitCatchFixture.csproj')
    dotnet build (Join-Path $inputDirectory 'TypedAwaitCatchFixture.csproj') -c Release --nologo -v quiet
    if($LASTEXITCODE -ne 0){throw 'Typed catch fixture build failed.'}
    $original=Join-Path $inputDirectory 'bin\Release\net48\TypedAwaitCatchFixture.exe'
    if($variant -eq 'absent' -or $variant -eq 'default') {
        $modified=Join-Path $inputDirectory 'TypedAwaitCatchFixture.exe'
        dotnet run --project (Join-Path $emitter 'Emitter.csproj') -c Release -- $original $modified $variant
        if($LASTEXITCODE -ne 0){throw 'Wrapping metadata emission failed.'}
        $original=$modified
    }
    & $original
    if($LASTEXITCODE -ne 0){throw "Original typed catch behavior failed: $variant"}
    foreach($threads in @(1,4)) {
        $export=Join-Path $OutputDirectory "export-$variant-$threads"
        & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
        if($LASTEXITCODE -ne 0){throw 'Typed catch export failed.'}
        $project=Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
        $rebuilt=Join-Path $OutputDirectory "rebuilt-$variant-$threads"
        dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
        if($LASTEXITCODE -ne 0){throw 'Typed catch source compilation failed.'}
        & (Join-Path $rebuilt 'TypedAwaitCatchFixture.exe')
        if($LASTEXITCODE -ne 0){throw 'Rebuilt typed catch behavior changed.'}
    }
}
$debug=Join-Path $OutputDirectory 'debug'
New-Item -ItemType Directory -Path $debug | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'TypedAwaitCatchDebug.cs') -Destination $debug
$runtime=Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$references=('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path=[Security.SecurityElement]::Escape((Join-Path $runtime ($_+'.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- $original
if($LASTEXITCODE -ne 0){throw 'Typed catch debug transformation failed.'}
