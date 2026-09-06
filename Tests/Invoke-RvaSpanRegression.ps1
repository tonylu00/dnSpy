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
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'RvaSpanFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitRvaSpan.cs') -Destination $emitterDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup><ItemGroup><PackageReference Include="System.Memory" Version="4.6.3"/></ItemGroup></Project>' | Set-Content (Join-Path $inputDirectory 'RvaSpanFixture.csproj')
$dnlib=[Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
dotnet build (Join-Path $inputDirectory 'RvaSpanFixture.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Span fixture build failed.'}
$compiled=Join-Path $inputDirectory 'bin\Release\net48'
Get-ChildItem -LiteralPath $compiled -File | Copy-Item -Destination $OutputDirectory
$original=Join-Path $OutputDirectory 'RvaSpanFixture.exe'
dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- (Join-Path $compiled 'RvaSpanFixture.exe') $original
if($LASTEXITCODE -ne 0){throw 'Span metadata emission failed.'}
& $original
if($LASTEXITCODE -ne 0){throw 'Original RVA span behavior failed.'}
foreach($threads in @(1,4)) {
    $export=Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
    if($LASTEXITCODE -ne 0){throw 'RVA span export failed.'}
    $project=Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt=Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if($LASTEXITCODE -ne 0){throw 'RVA span source compilation failed.'}
    & (Join-Path $rebuilt 'RvaSpanFixture.exe')
    if($LASTEXITCODE -ne 0){throw 'Rebuilt RVA span behavior changed.'}
}
$guards=Join-Path $OutputDirectory 'guards'
New-Item -ItemType Directory -Path $guards | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'RvaSpanGuards.cs') -Destination $guards
$runtime=Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$references=('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path=[Security.SecurityElement]::Escape((Join-Path $runtime ($_+'.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $guards 'Guards.csproj')
dotnet run --project (Join-Path $guards 'Guards.csproj') -c Release
if($LASTEXITCODE -ne 0){throw 'RVA span semantic guards failed.'}
