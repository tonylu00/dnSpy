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
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'IteratorSplitDispatchFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitIteratorSplitDispatch.cs') -Destination $emitterDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $inputDirectory 'IteratorSplitDispatchFixture.csproj')
$dnlib=[Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
dotnet build (Join-Path $inputDirectory 'IteratorSplitDispatchFixture.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Iterator fixture build failed.'}
$compiled=Join-Path $inputDirectory 'bin\Release\net48\IteratorSplitDispatchFixture.exe'
foreach($mode in @('plain','side-effect','terminal-dispose')) {
    $variant=Join-Path $OutputDirectory $mode
    New-Item -ItemType Directory -Path $variant | Out-Null
    $original=Join-Path $variant 'IteratorSplitDispatchFixture.exe'
    dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- $compiled $original $mode
    if($LASTEXITCODE -ne 0){throw 'Iterator metadata emission failed.'}
    & $original $mode
    if($LASTEXITCODE -ne 0){throw 'Original iterator behavior failed.'}
	$expectedResumption = @(& $original resume-after-dispose)
	if($LASTEXITCODE -ne 0){throw 'Original disposal-resumption probe failed.'}
    foreach($threads in @(1,4)) {
        $export=Join-Path $variant "export-$threads"
        & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
        if($LASTEXITCODE -ne 0){throw 'Iterator export failed.'}
        $source=Get-ChildItem -LiteralPath $export -Recurse -Filter 'IteratorSplitDispatchFixture.cs' | Select-Object -First 1
        $reconstructed=Select-String -LiteralPath $source.FullName -Pattern 'yield return' -Quiet
        if($reconstructed -ne ($mode -ne 'side-effect')){throw "Incorrect reconstruction/fallback for $mode"}
		$hasDisposalMarker=Select-String -LiteralPath $source.FullName -Pattern 'dnSpy.metadata.iterator-dispose.v1' -Quiet
		if($hasDisposalMarker -ne ($mode -eq 'plain')){throw "Incorrect disposal restoration marker for $mode"}
        $project=Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
        $rebuilt=Join-Path $variant "rebuilt-$threads"
        dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
        if($LASTEXITCODE -ne 0){throw 'Iterator source compilation failed.'}
        & (Join-Path $rebuilt 'IteratorSplitDispatchFixture.exe') $mode
        if($LASTEXITCODE -ne 0){throw 'Rebuilt iterator behavior changed.'}
		$actualResumption = @(& (Join-Path $rebuilt 'IteratorSplitDispatchFixture.exe') resume-after-dispose)
		if($LASTEXITCODE -ne 0 -or (Compare-Object $expectedResumption $actualResumption -SyncWindow 0 -CaseSensitive)){
			throw "Iterator resumption after Dispose changed: original=$expectedResumption rebuilt=$actualResumption"
		}
    }
}
