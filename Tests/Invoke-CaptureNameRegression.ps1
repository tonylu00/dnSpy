param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$source = Join-Path $OutputDirectory 'source'; $emitter = Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $source,$emitter | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'CaptureNameFixture.cs') -Destination $source
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitCaptureName.cs') -Destination $emitter
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $source 'CaptureNameFixture.csproj')
$runtime = Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$dnlib = [Security.SecurityElement]::Escape((Join-Path $runtime 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitter 'Emitter.csproj')
dotnet build (Join-Path $source 'CaptureNameFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Capture name fixture compilation failed.' }
$original = Join-Path $source 'bin\Release\net48\CaptureNameFixture.exe'
$inputExe = Join-Path $OutputDirectory 'CaptureNameFixture.exe'
$expected = @(& $original)
if ($LASTEXITCODE -ne 0) { throw 'Original capture name behavior failed.' }
$expected | Set-Content (Join-Path $OutputDirectory 'expected.txt')
dotnet run --project (Join-Path $emitter 'Emitter.csproj') -c Release -- $original $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Capture name emission failed.' }
$emitted = @(& $inputExe)
if ($LASTEXITCODE -ne 0 -or (Compare-Object $expected $emitted -SyncWindow 0 -CaseSensitive)) { throw 'Renamed capture name behavior differs.' }
$hash = (Get-FileHash -LiteralPath $inputExe).Hash
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $inputExe
    if ($LASTEXITCODE -ne 0) { throw 'Capture name export failed.' }
    $sources = @(Get-ChildItem -LiteralPath $export -Recurse -Filter '*.cs' | Sort-Object FullName | Get-FileHash | ForEach-Object Hash)
    if ($threads -eq 1) { $firstSources = $sources }
    elseif (Compare-Object $firstSources $sources -SyncWindow 0 -CaseSensitive) { throw 'Source differs by worker count.' }
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Capture name source compilation failed.' }
    $actual = @(& (Join-Path $rebuilt 'CaptureNameFixture.exe'))
    if ($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive)) { throw 'Capture name source behavior differs.' }
    $actual | Set-Content (Join-Path $OutputDirectory "actual-$threads.txt")
}

if ((Get-FileHash -LiteralPath $inputExe).Hash -ne $hash) { throw 'Input assembly changed.' }
Write-Output 'PASS: capture name source and runtime regression.'



