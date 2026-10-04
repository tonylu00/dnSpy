param(
    [Parameter(Mandatory)][string] $RuntimeDirectory,
    [Parameter(Mandatory)][string] $Inspector,
    [Parameter(Mandatory)][string] $ReferenceManifest,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference='Stop'
$RuntimeDirectory=[IO.Path]::GetFullPath($RuntimeDirectory)
$Inspector=[IO.Path]::GetFullPath($Inspector)
$ReferenceManifest=[IO.Path]::GetFullPath($ReferenceManifest)
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression folder.'}
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
function Run([string]$exe,[string[]]$arguments) {
    $result=& $exe @arguments 2>&1
    $result | Out-Host
    if($LASTEXITCODE -ne 0){throw "Command failed: $exe"}
    return ($result | Out-String)
}
foreach($folder in @('fixture','states','emitter','original-probe','rebuilt','rebuilt-states')) {
    New-Item -ItemType Directory -Path (Join-Path $OutputDirectory $folder) | Out-Null
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Fixture.cs') -Destination "$OutputDirectory\fixture\Fixture.cs"
Copy-Item -LiteralPath (Join-Path $PSScriptRoot '..\StateMachineDeclarationFixture.cs') -Destination "$OutputDirectory\states\Fixture.cs"
Copy-Item -LiteralPath (Join-Path $PSScriptRoot '..\EmitStateMachineNames.cs') -Destination "$OutputDirectory\emitter\Program.cs"
foreach($folder in @('fixture','states')) {
    $kind=if($folder -eq 'states'){'Exe'}else{'Library'}
    "<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>$kind</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>" | Set-Content "$OutputDirectory\$folder\Fixture.csproj"
    Run 'dotnet' @('build',"$OutputDirectory\$folder\Fixture.csproj",'-c','Release','--nologo','-v','quiet') | Out-Null
}
$dnlib=[Security.SecurityElement]::Escape((Join-Path $RuntimeDirectory 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content "$OutputDirectory\emitter\Emitter.csproj"
$fixture="$OutputDirectory\fixture\bin\Release\net48\Fixture.dll"
$states="$OutputDirectory\states\StateMachineDeclarationFixture.exe"
Run 'dotnet' @('run','--project',"$OutputDirectory\emitter\Emitter.csproj",'-c','Release','--',"$OutputDirectory\states\bin\Release\net48\Fixture.exe",$states) | Out-Null
$hashes=@{}
foreach($input in @($fixture,$states)){$hashes[$input]=(Get-FileHash -LiteralPath $input -Algorithm SHA256).Hash}
Run 'dotnet' @($Inspector,$RuntimeDirectory,$fixture,"$OutputDirectory\fixture-proof.json",'self-test',"--references=$ReferenceManifest","--source=$OutputDirectory\rebuilt\GeneratedSourceFixture.cs") | Out-Null
Run 'dotnet' @($Inspector,$RuntimeDirectory,$states,"$OutputDirectory\states-proof.json",'self-test',"--references=$ReferenceManifest","--source=$OutputDirectory\rebuilt-states\StateMachineDeclarationFixture.cs") | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'BehaviorProbe.cs') -Destination "$OutputDirectory\original-probe\BehaviorProbe.cs"
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'BehaviorProbe.cs') -Destination "$OutputDirectory\rebuilt\BehaviorProbe.cs"
$escaped=[Security.SecurityElement]::Escape($fixture)
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup><ItemGroup><Reference Include=`"Fixture`"><HintPath>$escaped</HintPath></Reference></ItemGroup></Project>" | Set-Content "$OutputDirectory\original-probe\Probe.csproj"
foreach($folder in @('rebuilt','rebuilt-states')) {
    '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content "$OutputDirectory\$folder\Probe.csproj"
}
foreach($folder in @('original-probe','rebuilt','rebuilt-states')){Run 'dotnet' @('build',"$OutputDirectory\$folder\Probe.csproj",'-c','Release','--nologo','-v','quiet') | Out-Null}
$original=Run "$OutputDirectory\original-probe\bin\Release\net48\Probe.exe" @()
$rebuilt=Run "$OutputDirectory\rebuilt\bin\Release\net48\Probe.exe" @()
if($original -ne $rebuilt){throw 'Generated-source behavior differs.'}
$originalStates=Run $states @()
$rebuiltStates=Run "$OutputDirectory\rebuilt-states\bin\Release\net48\Probe.exe" @()
if($originalStates -ne $rebuiltStates){throw 'Retained implementation behavior differs.'}
foreach($input in @($fixture,$states)){if((Get-FileHash -LiteralPath $input -Algorithm SHA256).Hash -ne $hashes[$input]){throw 'Fixture input changed.'}}
function Reject([string[]]$arguments,[string]$message) {
    $text=& dotnet @arguments 2>&1 | Out-String
    if($LASTEXITCODE -eq 0 -or $text -notmatch [regex]::Escape($message)){throw "Missing guard: $message`n$text"}
}
Reject @($Inspector,$RuntimeDirectory,$fixture,"$OutputDirectory\fixture-proof.json",'inspect') 'Choose a new report path'
$forbidden=Join-Path (Split-Path $fixture) 'forbidden.cs'
Reject @($Inspector,$RuntimeDirectory,$fixture,"$OutputDirectory\guard-source.json",'inspect',"--source=$forbidden") 'outside the inspected application tree'
Reject @($Inspector,$RuntimeDirectory,$fixture,"$OutputDirectory\guard-options.json",'inspect','--unvalidated-map=ignored') 'Unknown option'
Reject @($Inspector,$RuntimeDirectory,$fixture,"$OutputDirectory\guard-scope.json",'inspect','--root=0x02000004','--method=0x06000005') 'Choose type or member scope'
$manifest=Get-Content -LiteralPath $ReferenceManifest -Raw | ConvertFrom-Json
$manifest.Assemblies[0].Sha256='0'*64
$stale="$OutputDirectory\stale-reference.json"
$manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $stale
Reject @($Inspector,$RuntimeDirectory,$fixture,"$OutputDirectory\guard-reference.json",'inspect',"--references=$stale") 'Stale reference hash'
$manifest=Get-Content -LiteralPath $ReferenceManifest -Raw | ConvertFrom-Json
$manifest.Assemblies[0].Mvid='00000000-0000-0000-0000-000000000000'
$wrongIdentity="$OutputDirectory\wrong-reference.json"
$manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $wrongIdentity
Reject @($Inspector,$RuntimeDirectory,$fixture,"$OutputDirectory\guard-identity.json",'inspect',"--references=$wrongIdentity") 'Invalid/duplicate reference identity'
foreach($name in @('guard-source.json','guard-options.json','guard-scope.json','guard-reference.json','guard-identity.json')) {
    if(Test-Path -LiteralPath (Join-Path $OutputDirectory $name)){throw 'Rejected operation published a report.'}
}
'PASS: final AST evidence, original/rebuilt behavior and input preservation.'
