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
'<Project />' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'InvalidTypeNamesFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitInvalidTypeNames.cs') -Destination $emitterDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' |
    Set-Content (Join-Path $inputDirectory 'InvalidTypeNamesFixture.csproj')
$dnlib = [Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" |
    Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
dotnet build (Join-Path $inputDirectory 'InvalidTypeNamesFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Fixture build failed.' }
$inputExe = Join-Path $OutputDirectory 'InvalidTypeNamesFixture.exe'
dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- (Join-Path $inputDirectory 'bin\Release\net48\InvalidTypeNamesFixture.exe') $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Collision IL generation failed.' }
$hash = (Get-FileHash -LiteralPath $inputExe).Hash
& $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Original positional binding behavior failed.' }
foreach ($threads in @(1,4)) {
$export = Join-Path $OutputDirectory "export-$threads"
& $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Collision export failed.' }
$project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
$rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Exported collision source compilation failed.' }
& (Join-Path $rebuilt 'InvalidTypeNamesFixture.exe')
if ($LASTEXITCODE -ne 0) { throw 'Rebuilt positional binding behavior changed.' }


}
if ((Get-FileHash -LiteralPath $inputExe).Hash -ne $hash) { throw 'Input assembly changed.' }
