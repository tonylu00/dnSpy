param([Parameter(Mandatory)][string]$DnSpyConsole, [Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression output folder.'}
$source=Join-Path $OutputDirectory 'source'
New-Item -ItemType Directory -Path $source | Out-Null
'<Project />' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'OptionalOrderFixture.cs') -Destination $source
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' | Set-Content (Join-Path $source 'OptionalOrderFixture.csproj')
dotnet build $source -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Optional-order fixture compilation failed.'}
$original=Join-Path $source 'bin\Release\net48\OptionalOrderFixture.exe'
$hash=(Get-FileHash -LiteralPath $original).Hash
$expected=@(& $original)
if($LASTEXITCODE -ne 0){throw 'Original optional-order behavior failed.'}
foreach($threads in @(1,4)) {
    $export=Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
    if($LASTEXITCODE -ne 0){throw 'Optional-order export failed.'}
    $project=Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt=Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if($LASTEXITCODE -ne 0){throw 'Optional-order source compilation failed.'}
    $actual=@(& (Join-Path $rebuilt 'OptionalOrderFixture.exe'))
    if($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -CaseSensitive -SyncWindow 0)){throw 'Optional-order behavior changed.'}
    # Compile fresh callers against rebuilt metadata; exported calls already
    # contain their original default argument values in IL.
    $client=Join-Path $rebuilt 'Caller.cs'
    'class Caller { static int Main() { int state=3; if(OptionalOrderFixture.Ref(state:ref state)!=4) return 1; if(OptionalOrderFixture.Text(count:2)!="fallback2") return 2; if(OptionalOrderFixture.Enum(count:3)!=5) return 3; if(OptionalOrderFixture.Decimal(count:2)!=14.5m) return 4; if(!object.ReferenceEquals(OptionalOrderFixture.Missing(count:0),System.Type.Missing)) return 5; return 0; } }' | Set-Content $client
    $compiler=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
    & $compiler /nologo ('/r:'+(Join-Path $rebuilt 'OptionalOrderFixture.exe')) ('/out:'+(Join-Path $rebuilt 'Caller.exe')) $client
    if($LASTEXITCODE -ne 0){throw 'Rebuilt optional metadata could not compile a new caller.'}
    & (Join-Path $rebuilt 'Caller.exe')
    if($LASTEXITCODE -ne 0){throw 'New optional metadata caller behavior changed.'}
}
if((Get-FileHash -LiteralPath $original).Hash -ne $hash){throw 'Input assembly changed.'}
Write-Output $expected
