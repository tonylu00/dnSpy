param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory,
    [string] $FrameworkMSBuild
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
'<Project />' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$source = Join-Path $PSScriptRoot 'SerializedResourcesFixture.cs'
$emitter = Join-Path $OutputDirectory 'Emitter.exe'
$resource = Join-Path $OutputDirectory 'Data.resources'
$original = Join-Path $OutputDirectory 'SerializedResourcesFixture.exe'
$raw = Join-Path $OutputDirectory 'Raw.bin'
[IO.File]::WriteAllBytes($raw, [byte[]]@(29,31))
& $compiler /nologo /optimize+ /define:EMIT /r:System.Drawing.dll "/out:$emitter" $source
if ($LASTEXITCODE -ne 0) { throw 'Resource emitter compilation failed.' }
& $emitter $resource
if ($LASTEXITCODE -ne 0) { throw 'Legacy resource emission failed.' }
& $compiler /nologo /optimize+ /r:System.Drawing.dll "/resource:$resource,Fixture.Data.resources" "/resource:$raw,Other.Raw.payload" "/out:$original" $source
if ($LASTEXITCODE -ne 0) { throw 'Resource fixture compilation failed.' }
$expected = @(& $original)
if ($LASTEXITCODE -ne 0) { throw 'Original resource behavior failed.' }
$hash = (Get-FileHash -LiteralPath $original).Hash
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
    if ($LASTEXITCODE -ne 0) { throw 'Resource export failed.' }
    $relocated = Join-Path $OutputDirectory "relocated-$threads"
    Copy-Item -LiteralPath $export -Destination $relocated -Recurse
    $project = Get-ChildItem -LiteralPath $relocated -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Resource source build failed.' }
    $actual = @(& (Join-Path $rebuilt 'SerializedResourcesFixture.exe'))
    if ($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -CaseSensitive -SyncWindow 0)) { throw 'Rebuilt resource behavior changed.' }
}
if ($FrameworkMSBuild) {
    $export = Join-Path $OutputDirectory 'traditional'
    & $DnSpyConsole --no-color --threads 4 -o $export $original
    if ($LASTEXITCODE -ne 0) { throw 'Traditional resource export failed.' }
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory 'traditional-rebuilt'
    & $FrameworkMSBuild $project.FullName /nologo /v:quiet /p:Configuration=Release "/p:OutputPath=$rebuilt"
    if ($LASTEXITCODE -ne 0) { throw 'Traditional resource build failed.' }
    $actual = @(& (Join-Path $rebuilt 'SerializedResourcesFixture.exe'))
    if ($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -CaseSensitive -SyncWindow 0)) { throw 'Traditional resource behavior changed.' }
}
if ((Get-FileHash -LiteralPath $original).Hash -ne $hash) { throw 'Input assembly changed.' }
Write-Output $expected
