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
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'MetadataFieldsFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitMetadataFields.cs') -Destination $emitterDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' |
    Set-Content (Join-Path $inputDirectory 'MetadataFieldsFixture.csproj')
$dnlib = [Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" |
    Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
dotnet build (Join-Path $inputDirectory 'MetadataFieldsFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Fixture build failed.' }
$inputExe = Join-Path $OutputDirectory 'MetadataFieldsFixture.exe'
dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- (Join-Path $inputDirectory 'bin\Release\net48\MetadataFieldsFixture.exe') $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Metadata fields metadata generation failed.' }
$hash = (Get-FileHash -LiteralPath $inputExe).Hash
& $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Original metadata fields state behavior failed.' }
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    $watch = [Diagnostics.Stopwatch]::StartNew()
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $inputExe
    if ($LASTEXITCODE -ne 0) { throw 'Metadata fields export failed.' }
    $watch.Stop()
    @{ Threads=$threads; ExportSeconds=$watch.Elapsed.TotalSeconds } | ConvertTo-Json |
        Set-Content (Join-Path $OutputDirectory "timing-$threads.json")
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Exported metadata fields source compilation failed.' }
    & (Join-Path $rebuilt 'MetadataFieldsFixture.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Rebuilt metadata fields state behavior changed.' }
    dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release --no-build -- --check (Join-Path $rebuilt 'MetadataFieldsFixture.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Raw field constant metadata changed.' }
    $before = @(Get-FileHash (Join-Path $rebuilt 'MetadataFieldsFixture.exe'),(Join-Path $rebuilt 'MetadataFieldsFixture.pdb') | ForEach-Object Hash)
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Incremental build failed.' }
    if (Compare-Object $before @(Get-FileHash (Join-Path $rebuilt 'MetadataFieldsFixture.exe'),(Join-Path $rebuilt 'MetadataFieldsFixture.pdb') | ForEach-Object Hash)) { throw 'Incremental build rewrote restored metadata or symbols.' }
}
if ((Get-FileHash -LiteralPath $inputExe).Hash -ne $hash) { throw 'Input assembly changed.' }





