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
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'StructuredFilterFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitStructuredFilter.cs') -Destination $emitterDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $inputDirectory 'StructuredFilterFixture.csproj')
$dnlib=[Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
dotnet build (Join-Path $inputDirectory 'StructuredFilterFixture.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Structured filter fixture build failed.'}
$source=Join-Path $inputDirectory 'bin\Release\net48\StructuredFilterFixture.exe'
$original=Join-Path $OutputDirectory 'StructuredFilterFixture.exe'
& $source
if($LASTEXITCODE -ne 0){throw 'Compiler-produced structured filter behavior failed.'}
dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- $source $original
if($LASTEXITCODE -ne 0){throw 'Structured filter emission failed.'}
& $original
if($LASTEXITCODE -ne 0){throw 'Original structured filter behavior failed.'}
foreach($variant in @('compiler','reordered')) {
  $assembly=if($variant -eq 'compiler'){$source}else{$original}
  foreach($threads in @(1,4)) {
    $export=Join-Path $OutputDirectory "export-$variant-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $assembly
    if($LASTEXITCODE -ne 0){throw 'Structured filter export failed.'}
    $project=Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt=Join-Path $OutputDirectory "rebuilt-$variant-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if($LASTEXITCODE -ne 0){throw 'Structured filter source compilation failed.'}
    & (Join-Path $rebuilt 'StructuredFilterFixture.exe')
    if($LASTEXITCODE -ne 0){throw 'Rebuilt structured filter behavior changed.'}
  }
}

$debug=Join-Path $OutputDirectory 'debug'
New-Item -ItemType Directory -Path $debug | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'StructuredFilterDebug.cs') -Destination $debug
$runtime=Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$references=('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path=[Security.SecurityElement]::Escape((Join-Path $runtime ($_+'.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- $original
if($LASTEXITCODE -ne 0){throw 'Structured filter debug transformation failed.'}
