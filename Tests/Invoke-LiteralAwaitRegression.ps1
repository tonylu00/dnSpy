param([Parameter(Mandatory)][string] $DnSpyConsole, [Parameter(Mandatory)][string] $OutputDirectory)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a fresh regression directory.'}
$inputDirectory=Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory $inputDirectory | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'LiteralAwaitFixture.cs') $inputDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content "$inputDirectory\Fixture.csproj"
dotnet build $inputDirectory -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Literal await fixture build failed.'}
$original="$inputDirectory\bin\Release\net48\Fixture.exe"
$hash=(Get-FileHash $original).Hash
$expected=@(& $original)
if($LASTEXITCODE -ne 0){throw 'Original literal await behavior failed.'}
$expected | Set-Content "$OutputDirectory\expected.txt"
foreach($threads in @(1,4)) {
    $export=Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
    if($LASTEXITCODE -ne 0){throw 'Literal await source export failed.'}
    $source=Get-Content "$export\Fixture\LiteralAwaitFixture.cs" -Raw
    foreach($name in @('FormatLiteral','FormatVersions')) {if($source -notmatch ("async (?:global::System.Threading.Tasks\.)?Task<string> $name\(")){throw "Literal await owner not reconstructed: $name"}}
    $sources=@(Get-ChildItem $export -Recurse -Filter '*.cs' | Sort-Object FullName | Get-FileHash | ForEach-Object Hash)
    if($threads -eq 1){$firstSources=$sources}
    elseif(Compare-Object $firstSources $sources -SyncWindow 0 -CaseSensitive){throw 'Literal await source changed by worker count.'}
    $project=Get-ChildItem $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt=Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if($LASTEXITCODE -ne 0){throw 'Literal await source compilation failed.'}
    $actual=@(& "$rebuilt\Fixture.exe")
    if($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive)){throw 'Literal await behavior changed.'}
    $actual | Set-Content "$OutputDirectory\actual-$threads.txt"
}
if((Get-FileHash $original).Hash -ne $hash){throw 'Original fixture changed.'}
$guards=Join-Path $OutputDirectory 'guards'
New-Item -ItemType Directory $guards | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'LiteralAwaitGuards.cs') $guards
$runtime=Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$references=('ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path=[Security.SecurityElement]::Escape((Join-Path $runtime ($_+'.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content "$guards\Guards.csproj"
dotnet run --project "$guards\Guards.csproj" -c Release
if($LASTEXITCODE -ne 0){throw 'Literal await evaluation-order guards failed.'}
Write-Output $expected
