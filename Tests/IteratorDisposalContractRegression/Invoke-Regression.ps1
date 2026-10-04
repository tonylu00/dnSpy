param(
    [Parameter(Mandatory)][string] $RuntimeDirectory,
    [Parameter(Mandatory)][string] $RestoreTaskSource,
    [Parameter(Mandatory)][string] $Fixture,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression folder.'}
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
$initial=(Get-FileHash -LiteralPath $Fixture).Hash
dotnet build (Join-Path $PSScriptRoot 'IteratorDisposalContractRegression.csproj') -c Release "-p:RuntimeDirectory=$RuntimeDirectory" "-p:RestoreTaskSource=$RestoreTaskSource" "-p:BaseIntermediateOutputPath=$OutputDirectory\obj\" -o "$OutputDirectory\bin\" --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Disposal contract harness failed to compile.'}
dotnet "$OutputDirectory\bin\IteratorDisposalContractRegression.dll" $Fixture
if($LASTEXITCODE -ne 0){throw 'Disposal contract regression failed.'}
if((Get-FileHash -LiteralPath $Fixture).Hash -ne $initial){throw 'Input fixture changed.'}
