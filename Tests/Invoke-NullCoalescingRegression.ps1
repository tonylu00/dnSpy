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
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'NullCoalescingFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitNullCoalescing.cs') -Destination $emitterDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' |
    Set-Content (Join-Path $inputDirectory 'NullCoalescingFixture.csproj')
$dnlib = [Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" |
    Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
dotnet build (Join-Path $inputDirectory 'NullCoalescingFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Coalescing fixture build failed.' }
$original = Join-Path $OutputDirectory 'NullCoalescingFixture.exe'
dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- (Join-Path $inputDirectory 'bin\Release\net48\NullCoalescingFixture.exe') $original
if ($LASTEXITCODE -ne 0) { throw 'Coalescing IL emission failed.' }
& $original
if ($LASTEXITCODE -ne 0) { throw 'Original coalescing behavior failed.' }
$export = Join-Path $OutputDirectory 'export'
& $DnSpyConsole --no-color --sdk-project --threads 4 -o $export $original
if ($LASTEXITCODE -ne 0) { throw 'Coalescing source export failed.' }
$project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
$rebuilt = Join-Path $OutputDirectory 'rebuilt'
dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Exported coalescing compilation failed.' }
& (Join-Path $rebuilt 'NullCoalescingFixture.exe')
if ($LASTEXITCODE -ne 0) { throw 'Rebuilt coalescing behavior changed.' }
