param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression output folder.'}
$debug=Join-Path $OutputDirectory 'debug'
$original=Join-Path $OutputDirectory 'original'
$transformed=Join-Path $OutputDirectory 'transformed'
New-Item -ItemType Directory -Path $debug,$original,$transformed | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'SingleIterationTryLoopDebug.cs') -Destination $debug
$runtime=Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$references=('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path=[Security.SecurityElement]::Escape((Join-Path $runtime ($_+'.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- (Join-Path $original 'Program.cs') (Join-Path $transformed 'Program.cs')
if($LASTEXITCODE -ne 0){throw 'Single-iteration loop guards failed.'}
foreach($directory in @($original,$transformed)) {
    '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><LangVersion>latest</LangVersion><AssemblyName>Fixture</AssemblyName></PropertyGroup></Project>' | Set-Content (Join-Path $directory 'Fixture.csproj')
    dotnet build (Join-Path $directory 'Fixture.csproj') -c Release --nologo -v quiet
    if($LASTEXITCODE -ne 0){throw 'Loop fixture compilation failed.'}
    & (Join-Path $directory 'bin\Release\net48\Fixture.exe') | Set-Content (Join-Path $directory 'records.txt')
    if($LASTEXITCODE -ne 0){throw 'Loop fixture execution failed.'}
}
$before=Get-Content (Join-Path $original 'records.txt')
$after=Get-Content (Join-Path $transformed 'records.txt')
if($before.Count -ne 36 -or $after.Count -ne 36 -or (Compare-Object $before $after -SyncWindow 0 -CaseSensitive)){throw 'Loop transformation changed control flow or cleanup.'}
Write-Output 'PASS: 36 original/transformed traces match, including nested breaks, repeated iterations, caught errors and throwing finally blocks.'
