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
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'PropertyRowNamesFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitPropertyRowNames.cs') -Destination $emitterDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' |
    Set-Content (Join-Path $inputDirectory 'PropertyRowNamesFixture.csproj')
$dnlib = [Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" |
    Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
dotnet build (Join-Path $inputDirectory 'PropertyRowNamesFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Property-method fixture build failed.' }
$original = Join-Path $OutputDirectory 'PropertyRowNamesFixture.exe'
dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- (Join-Path $inputDirectory 'bin\Release\net48\PropertyRowNamesFixture.exe') $original
if ($LASTEXITCODE -ne 0) { throw 'Property-method metadata emission failed.' }
& $original
if ($LASTEXITCODE -ne 0) { throw 'Original property-method behavior failed.' }
$client = Join-Path $OutputDirectory 'client'
New-Item -ItemType Directory -Path $client | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'PropertyRowNamesClient.cs') $client
$reference = [Security.SecurityElement]::Escape($original)
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"PropertyRowNamesFixture`"><HintPath>$reference</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $client 'Client.csproj')
dotnet build (Join-Path $client 'Client.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE) { throw 'Original-contract client build failed' }
$clientExe = Join-Path $client 'bin\Release\net48\Client.exe'
& $clientExe
if ($LASTEXITCODE) { throw 'Original-contract client failed' }
$clientHash = (Get-FileHash $clientExe).Hash
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
    if ($LASTEXITCODE -ne 0) { throw 'Property-method export failed.' }
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Property-method source compilation failed.' }
    & (Join-Path $rebuilt 'PropertyRowNamesFixture.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Rebuilt property-method behavior changed.' }
    Copy-Item $clientExe $rebuilt
    $rebuiltClient = Join-Path $rebuilt 'Client.exe'
    & $rebuiltClient
    if ($LASTEXITCODE -or (Get-FileHash $rebuiltClient).Hash -ne $clientHash) { throw 'Unchanged external client failed' }
}

