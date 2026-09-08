param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$inputDirectory = Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory -Path $inputDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'FinalizerFixture.cs') -Destination $inputDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' |
    Set-Content (Join-Path $inputDirectory 'FinalizerFixture.csproj')
dotnet build (Join-Path $inputDirectory 'FinalizerFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Finalizer fixture compilation failed.' }
$original = Join-Path $inputDirectory 'bin\Release\net48\FinalizerFixture.exe'
& $original
if ($LASTEXITCODE -ne 0) { throw 'Original finalizer behavior failed.' }
$emitter = Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $emitter | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'EmitFinalizer.cs') $emitter
$dnlib = [Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitter 'Emitter.csproj')
$modified = Join-Path $OutputDirectory 'FinalizerFixture.exe'
dotnet run --project (Join-Path $emitter 'Emitter.csproj') -c Release -- $original $modified
if ($LASTEXITCODE -ne 0) { throw 'Finalizer emission failed.' }
& $modified
if ($LASTEXITCODE -ne 0) { throw 'Emitted finalizer behavior failed.' }
$hash = (Get-FileHash $modified).Hash
foreach ($threads in @(1,4)) {
$export = Join-Path $OutputDirectory "export-$threads"
& $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $modified
if ($LASTEXITCODE -ne 0) { throw 'Finalizer source export failed.' }
$project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
$rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Exported finalizer compilation failed.' }
& (Join-Path $rebuilt 'FinalizerFixture.exe')
if ($LASTEXITCODE -ne 0) { throw 'Rebuilt finalizer behavior changed.' }
}
if ((Get-FileHash $modified).Hash -ne $hash) { throw 'Input changed.' }
$one = @(Get-ChildItem (Join-Path $OutputDirectory 'export-1') -Recurse -Filter '*.cs' | Sort-Object FullName | Get-FileHash | ForEach-Object Hash)
$four = @(Get-ChildItem (Join-Path $OutputDirectory 'export-4') -Recurse -Filter '*.cs' | Sort-Object FullName | Get-FileHash | ForEach-Object Hash)
if (Compare-Object $one $four -SyncWindow 0) { throw 'Worker count changed source.' }
$unsafeInput = Join-Path $OutputDirectory 'throwing-prefix\FinalizerFixture.exe'
New-Item -ItemType Directory -Path (Split-Path $unsafeInput) | Out-Null
dotnet run --project (Join-Path $emitter 'Emitter.csproj') -c Release --no-build -- $original $unsafeInput throwing
if ($LASTEXITCODE -ne 0) { throw 'Throwing prefix emission failed.' }
& $unsafeInput throwing
if ($LASTEXITCODE -ne 0) { throw 'Original throwing prefix cleanup changed.' }
$unsafeExport = Join-Path $OutputDirectory 'throwing-prefix-export'
& $DnSpyConsole --no-color --sdk-project --threads 1 -o $unsafeExport $unsafeInput
if ($LASTEXITCODE -ne 0) { throw 'Throwing prefix export failed.' }
$unsafeSource = Get-Content (Join-Path $unsafeExport 'FinalizerFixture\FinalizerCase.cs') -Raw
if ($unsafeSource -notmatch 'override void Finalize\(' -or $unsafeSource -match '~FinalizerCase\(') { throw 'Throwing prefix was moved into implicit base cleanup.' }
Write-Output 'PASS: nonthrowing finalizer preparation, cleanup order and throwing-prefix boundary.'

