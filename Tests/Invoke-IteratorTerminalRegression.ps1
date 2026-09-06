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
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'IteratorTerminalFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitIteratorTerminal.cs') -Destination $emitterDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $inputDirectory 'IteratorTerminalFixture.csproj')
$dnlib=[Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
dotnet build (Join-Path $inputDirectory 'IteratorTerminalFixture.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Iterator fixture build failed.'}
$compiled=Join-Path $inputDirectory 'bin\Release\net48\IteratorTerminalFixture.exe'
foreach($last in @(4,0,8,-1)) {
    $variant=Join-Path $OutputDirectory "last-$last"
    New-Item -ItemType Directory -Path $variant | Out-Null
    $original=Join-Path $variant 'IteratorTerminalFixture.exe'
    dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- $compiled $original $last
    if($LASTEXITCODE -ne 0){throw 'Iterator metadata emission failed.'}
    & $original
    if($LASTEXITCODE -ne 0){throw 'Original iterator behavior failed.'}
    foreach($threads in @(1,4)) {
        $export=Join-Path $variant "export-$threads"
        & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
        if($LASTEXITCODE -ne 0){throw 'Iterator export failed.'}
        $source=Get-ChildItem -LiteralPath $export -Recurse -Filter 'IteratorTerminalFixture.cs' | Select-Object -First 1
        if(!(Select-String -LiteralPath $source.FullName -Pattern 'yield return' -Quiet)){throw 'Iterator reconstruction unexpectedly fell back.'}
        $project=Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
        $rebuilt=Join-Path $variant "rebuilt-$threads"
        dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
        if($LASTEXITCODE -ne 0){throw 'Iterator source compilation failed.'}
        & (Join-Path $rebuilt 'IteratorTerminalFixture.exe')
        if($LASTEXITCODE -ne 0){throw 'Rebuilt iterator behavior changed.'}
    }
}
