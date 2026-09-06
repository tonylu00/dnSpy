param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$inputDirectory = Join-Path $OutputDirectory 'input'
$emitterDirectory = Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $inputDirectory,$emitterDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'StateMachineDeclarationFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitStateMachineNames.cs') -Destination $emitterDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' |
    Set-Content (Join-Path $inputDirectory 'StateMachineDeclarationFixture.csproj')
$dnlib = [Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" |
    Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
dotnet build (Join-Path $inputDirectory 'StateMachineDeclarationFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'State-machine fixture build failed.' }
$original = Join-Path $OutputDirectory 'StateMachineDeclarationFixture.exe'
dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- (Join-Path $inputDirectory 'bin\Release\net48\StateMachineDeclarationFixture.exe') $original
if ($LASTEXITCODE -ne 0) { throw 'State-machine metadata emission failed.' }
& $original
if ($LASTEXITCODE -ne 0) { throw 'Original state-machine behavior failed.' }
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
    if ($LASTEXITCODE -ne 0) { throw 'State-machine source export failed.' }
    $source = Get-Content (Join-Path $export 'StateMachineDeclarationFixture\StateMachineDeclarationFixture.cs') -Raw
    if ($source -match '(struct|class) State_(Remove|RemoveGeneric|Anonymous)') { throw 'Redundant reconstructed state machine was emitted.' }
    foreach ($name in @('KeepType','KeepMember','KeepSignature','KeepShared','KeepPublic')) {
        if ($source -notmatch ('(struct|class) State_' + $name + '\b')) { throw "Required state machine was removed: $name" }
    }
    if ($source -notmatch 'async Task<int> KeepShared\(' -or $source -match 'async Task<int> SharedFallback\(') { throw 'Shared state-machine fixture did not cover successful and fallback reconstruction.' }
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Exported state-machine source compilation failed.' }
    & (Join-Path $rebuilt 'StateMachineDeclarationFixture.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Rebuilt state-machine behavior changed.' }
}
foreach ($option in @('--declare-state-machines','--show-all','--no-async')) {
    $source = & $DnSpyConsole --no-color $option --type StateMachineDeclarationFixture $original | Out-String
    if ($LASTEXITCODE -ne 0 -or $source -notmatch '(struct|class) State_Remove\b') { throw "Explicit state-machine display failed: $option" }
}
$source = & $DnSpyConsole --no-color --type 'StateMachineDeclarationFixture/State_Remove' $original | Out-String
if ($LASTEXITCODE -ne 0 -or $source -notmatch '(struct|class) State_Remove\b') { throw 'Direct state-machine type display failed.' }
