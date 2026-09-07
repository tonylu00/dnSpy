param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression output folder.'}
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
'<Project />' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
foreach($part in @('Support','Bridge','Fixture')) {
    $directory=Join-Path $OutputDirectory $part
    New-Item -ItemType Directory -Path $directory | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "TransitiveNamespace$part.cs") -Destination $directory
    $reference=if($part -eq 'Support'){''}else {
        $dependency=if($part -eq 'Bridge'){'Support'}else{'Bridge'}
        "<ItemGroup><ProjectReference Include=`"..\$dependency\$dependency.csproj`" /></ItemGroup>"
    }
    $kind=if($part -eq 'Fixture'){'Exe'}else{'Library'}
    "<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>$kind</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup>$reference</Project>" | Set-Content (Join-Path $directory "$part.csproj")
}
dotnet build (Join-Path $OutputDirectory 'Fixture\Fixture.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Transitive namespace fixture build failed.'}
$inputDirectory=Join-Path $OutputDirectory 'Fixture\bin\Release\net48'
$original=Join-Path $inputDirectory 'Fixture.exe'
$hashes=@('Fixture.exe','Bridge.dll','Support.dll' | ForEach-Object { (Get-FileHash -LiteralPath (Join-Path $inputDirectory $_)).Hash })
$expected=@(& $original)
if($LASTEXITCODE -ne 0){throw 'Original transitive namespace bindings failed.'}
$expected | Set-Content (Join-Path $OutputDirectory 'expected.txt')
foreach($threads in @(1,4)) {
    $export=Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original (Join-Path $inputDirectory 'Bridge.dll') (Join-Path $inputDirectory 'Support.dll')
    if($LASTEXITCODE -ne 0){throw 'Transitive namespace export failed.'}
    $project=Join-Path $export 'Fixture\Fixture.csproj'
    $rebuilt=Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project -c Release -o $rebuilt --nologo -v quiet
    if($LASTEXITCODE -ne 0){throw 'Transitive namespace source compilation failed.'}
    $actual=@(& (Join-Path $rebuilt 'Fixture.exe'))
    if($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive)){throw 'Transitive namespace behavior changed.'}
}
$debug=Join-Path $OutputDirectory 'debug'
New-Item -ItemType Directory -Path $debug | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'TransitiveNamespaceDebug.cs') -Destination $debug
$runtime=Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$references=('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path=[Security.SecurityElement]::Escape((Join-Path $runtime ($_+'.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- $original
if($LASTEXITCODE -ne 0){throw 'Transitive namespace scope/cache checks failed.'}
$after=@('Fixture.exe','Bridge.dll','Support.dll' | ForEach-Object { (Get-FileHash -LiteralPath (Join-Path $inputDirectory $_)).Hash })
if(Compare-Object $hashes $after -SyncWindow 0 -CaseSensitive){throw 'Input assemblies changed.'}
Write-Output $expected
