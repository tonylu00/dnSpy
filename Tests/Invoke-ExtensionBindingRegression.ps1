param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression output folder.'}
$inputDirectory=Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory -Path $inputDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ExtensionBindingFixture.cs') -Destination $inputDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup><ItemGroup><PackageReference Include="System.Memory" Version="4.6.3"/></ItemGroup></Project>' | Set-Content (Join-Path $inputDirectory 'ExtensionBindingFixture.csproj')
dotnet build (Join-Path $inputDirectory 'ExtensionBindingFixture.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Extension fixture build failed.'}
$original=Join-Path $inputDirectory 'bin\Release\net48\ExtensionBindingFixture.exe'
$expected=@(& $original)
if($LASTEXITCODE -ne 0){throw 'Original extension behavior failed.'}
$expected | Set-Content (Join-Path $OutputDirectory 'expected.txt')
foreach($threads in @(1,4)) {
    $export=Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
    if($LASTEXITCODE -ne 0){throw 'Extension export failed.'}
    $project=Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    # Span extensions participate in the rebuild's C# overload lookup even if
    # the original IL calls only Enumerable and has no System.Memory reference.
    [xml]$xml=Get-Content -LiteralPath $project.FullName
    $group=$xml.Project.AppendChild($xml.CreateElement('ItemGroup'))
    $package=$group.AppendChild($xml.CreateElement('PackageReference'))
    $package.SetAttribute('Include','System.Memory'); $package.SetAttribute('Version','4.6.3')
    $xml.Save($project.FullName)
    $rebuilt=Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if($LASTEXITCODE -ne 0){throw 'Exported extension source compilation failed.'}
    $actual=@(& (Join-Path $rebuilt 'ExtensionBindingFixture.exe'))
    if($LASTEXITCODE -ne 0){throw 'Rebuilt extension behavior changed.'}
    $actual | Set-Content (Join-Path $OutputDirectory "actual-$threads.txt")
    if(Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive){throw 'Extension behavior differs.'}
}
$debug=Join-Path $OutputDirectory 'debug'
New-Item -ItemType Directory -Path $debug | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ExtensionBindingDebug.cs') -Destination $debug
$runtime=Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$references=('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path=[Security.SecurityElement]::Escape((Join-Path $runtime ($_+'.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- $original (Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319')
if($LASTEXITCODE -ne 0){throw 'Extension debug validation failed.'}
Write-Output $expected
