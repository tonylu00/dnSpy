param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$inputDirectory = Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory -Path $inputDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'InheritedPropertyFixture.cs') -Destination $inputDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' |
    Set-Content (Join-Path $inputDirectory 'InheritedPropertyFixture.csproj')
dotnet build (Join-Path $inputDirectory 'InheritedPropertyFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Inherited property fixture compilation failed.' }
$original = Join-Path $inputDirectory 'bin\Release\net48\InheritedPropertyFixture.exe'
$emitterDirectory = Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $emitterDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitInheritedProperty.cs') -Destination $emitterDirectory
$dnlib = [Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" |
    Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
$rewritten = Join-Path $OutputDirectory 'InheritedPropertyFixture.exe'
dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- $original $rewritten
if ($LASTEXITCODE -ne 0) { throw 'Inherited property bridge emission failed.' }
$original = $rewritten
& $original
if ($LASTEXITCODE -ne 0) { throw 'Original inherited property behavior failed.' }
$export = Join-Path $OutputDirectory 'export'
& $DnSpyConsole --no-color --sdk-project --threads 4 -o $export $original
if ($LASTEXITCODE -ne 0) { throw 'Inherited property source export failed.' }
$project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
$rebuilt = Join-Path $OutputDirectory 'rebuilt'
dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Exported inherited property compilation failed.' }
& (Join-Path $rebuilt 'InheritedPropertyFixture.exe')
if ($LASTEXITCODE -ne 0) { throw 'Rebuilt inherited property behavior changed.' }

$guard = Join-Path $OutputDirectory 'DirectReferenceFixture.exe'
dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- (Join-Path $inputDirectory 'bin\Release\net48\InheritedPropertyFixture.exe') $guard direct-reference
if ($LASTEXITCODE -ne 0) { throw 'Direct-reference fixture emission failed.' }
$guardExport = Join-Path $OutputDirectory 'guard-export'
& $DnSpyConsole --no-color --sdk-project --threads 4 -o $guardExport $guard
if ($LASTEXITCODE -ne 0) { throw 'Direct-reference source export failed.' }
$guardSource = Get-ChildItem -LiteralPath $guardExport -Recurse -Filter 'ValueDerived.cs' | Select-Object -First 1 | Get-Content -Raw
if ($guardSource -notmatch 'IValueContract\.ReadValue\(' -or $guardSource -notmatch 'ReadBridge\(') {
    throw 'Directly referenced orphan methods must remain available until their callers can be reconstructed.'
}
Write-Output 'PASS: direct-reference guard preserves the unsupported method representation.'

