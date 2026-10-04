param([Parameter(Mandatory)][string] $DnSpyConsole, [Parameter(Mandatory)][string] $OutputDirectory)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a fresh regression directory.'}
$inputDirectory=Join-Path $OutputDirectory 'input'
$emitterDirectory=Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory $inputDirectory,$emitterDirectory | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'IteratorMixedRegionFixture.cs') $inputDirectory
Copy-Item (Join-Path $PSScriptRoot 'EmitIteratorMixedRegion.cs') $emitterDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $inputDirectory 'Fixture.csproj')
$dnlib=[Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
dotnet build $inputDirectory -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Fixture build failed.'}
$baseline=Join-Path $inputDirectory 'bin\Release\net48\Fixture.exe'
$expected=@(& $baseline)
if($LASTEXITCODE -ne 0){throw 'Baseline behavior failed.'}
$expected | Set-Content (Join-Path $OutputDirectory 'expected.txt')
foreach($mode in @('plain','reverse','rotate')) {
    $variant=Join-Path $OutputDirectory $mode
    New-Item -ItemType Directory $variant | Out-Null
    $original=Join-Path $variant 'Fixture.exe'
    dotnet run --project $emitterDirectory -c Release -- $baseline $original $mode
    if($LASTEXITCODE -ne 0){throw 'Synthetic permutation failed.'}
    $hash=(Get-FileHash $original).Hash
    $actual=@(& $original)
    if($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive)){throw "Permutation changed behavior: $mode"}
    foreach($threads in @(1,4)) {
        $export=Join-Path $variant "export-$threads"
        & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
        if($LASTEXITCODE -ne 0){throw 'Export failed.'}
        $source=Get-Content (Join-Path $export 'Fixture\IteratorMixedRegionFixture.cs') -Raw
        if($source -notmatch 'yield return' -or $source -notmatch 'using \('){throw "Protected iterator not reconstructed: $mode"}
        $sources=@(Get-ChildItem $export -Recurse -Filter '*.cs' | Sort-Object FullName | Get-FileHash | ForEach-Object Hash)
        if($threads -eq 1){$firstSources=$sources}
        elseif(Compare-Object $firstSources $sources -SyncWindow 0 -CaseSensitive){throw "Source differs by worker count: $mode"}
        $project=Get-ChildItem $export -Recurse -Filter '*.csproj' | Select-Object -First 1
        $rebuilt=Join-Path $variant "rebuilt-$threads"
        dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
        if($LASTEXITCODE -ne 0){throw 'Exported source build failed.'}
        $actual=@(& (Join-Path $rebuilt 'Fixture.exe'))
        if($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive)){throw "Rebuilt behavior changed: $mode/$threads"}
        $actual | Set-Content (Join-Path $variant "actual-$threads.txt")
    }
    if((Get-FileHash $original).Hash -ne $hash){throw 'Input was modified.'}
}
$guards=Join-Path $OutputDirectory 'guards'
New-Item -ItemType Directory $guards | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'IteratorMixedRegionGuards.cs') $guards
$runtime=Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$references=('ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path=[Security.SecurityElement]::Escape((Join-Path $runtime ($_+'.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content "$guards\Guards.csproj"
dotnet run --project "$guards\Guards.csproj" -c Release
if($LASTEXITCODE -ne 0){throw 'Protected iterator region guards failed.'}
$expected
