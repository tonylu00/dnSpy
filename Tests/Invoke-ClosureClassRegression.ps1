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
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ClosureClassFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitClosureClass.cs') -Destination $emitterDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' |
    Set-Content (Join-Path $inputDirectory 'ClosureClassFixture.csproj')
$dnlib = [Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" |
    Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
dotnet build (Join-Path $inputDirectory 'ClosureClassFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Fixture build failed.' }
$inputExe = Join-Path $OutputDirectory 'ClosureClassFixture.exe'
dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- (Join-Path $inputDirectory 'bin\Release\net48\ClosureClassFixture.exe') $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Closure metadata generation failed.' }
$hash = (Get-FileHash -LiteralPath $inputExe).Hash
& $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Original closure state behavior failed.' }
foreach ($threads in @(1,4)) {
$export = Join-Path $OutputDirectory "export-$threads"
& $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Closure export failed.' }
$project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
$rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Exported closure source compilation failed.' }
& (Join-Path $rebuilt 'ClosureClassFixture.exe')
if ($LASTEXITCODE -ne 0) { throw 'Rebuilt closure state behavior changed.' }


}
if ((Get-FileHash -LiteralPath $inputExe).Hash -ne $hash) { throw 'Input assembly changed.' }
