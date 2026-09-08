param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$source = Join-Path $OutputDirectory 'source'; $emitter = Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $source,$emitter | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'IteratorBaseWrapperFixture.cs') -Destination $source
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitIteratorBaseWrapper.cs') -Destination $emitter
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $source 'IteratorBaseWrapperFixture.csproj')
$runtime = Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$dnlib = [Security.SecurityElement]::Escape((Join-Path $runtime 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitter 'Emitter.csproj')
dotnet build (Join-Path $source 'IteratorBaseWrapperFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Iterator base wrapper fixture compilation failed.' }
$original = Join-Path $source 'bin\Release\net48\IteratorBaseWrapperFixture.exe'
$inputExe = Join-Path $OutputDirectory 'IteratorBaseWrapperFixture.exe'
$expected = @(& $original)
if ($LASTEXITCODE -ne 0) { throw 'Original iterator base wrapper behavior failed.' }
$expected | Set-Content (Join-Path $OutputDirectory 'expected.txt')
dotnet run --project (Join-Path $emitter 'Emitter.csproj') -c Release -- $original $inputExe
if ($LASTEXITCODE -ne 0) { throw 'Iterator base wrapper emission failed.' }
$emitted = @(& $inputExe)
if ($LASTEXITCODE -ne 0 -or (Compare-Object $expected $emitted -SyncWindow 0 -CaseSensitive)) { throw 'Renamed iterator base wrapper behavior differs.' }
$hash = (Get-FileHash -LiteralPath $inputExe).Hash
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $inputExe
    if ($LASTEXITCODE -ne 0) { throw 'Iterator base wrapper export failed.' }
    $derivedSource = Get-Content (Join-Path $export 'IteratorBaseWrapperFixture\IteratorDerived.cs') -Raw
    if ($derivedSource -notmatch 'class RetainedIterator\b') { throw 'Required iterator declaration was removed.' }
    $sources = @(Get-ChildItem -LiteralPath $export -Recurse -Filter '*.cs' | Sort-Object FullName | Get-FileHash | ForEach-Object Hash)
    if ($threads -eq 1) { $firstSources = $sources }
    elseif (Compare-Object $firstSources $sources -SyncWindow 0 -CaseSensitive) { throw 'Source differs by worker count.' }
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Iterator base wrapper source compilation failed.' }
    $actual = @(& (Join-Path $rebuilt 'IteratorBaseWrapperFixture.exe'))
    if ($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive)) { throw 'Iterator base wrapper source behavior differs.' }
    $actual | Set-Content (Join-Path $OutputDirectory "actual-$threads.txt")
}

if ((Get-FileHash -LiteralPath $inputExe).Hash -ne $hash) { throw 'Input assembly changed.' }
Write-Output 'PASS: iterator base wrapper source and runtime regression.'



