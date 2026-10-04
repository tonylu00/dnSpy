param(
    [Parameter(Mandatory)][string] $RuntimeDirectory,
    [Parameter(Mandatory)][string] $Inspector,
    [Parameter(Mandatory)][string] $Fixture,
    [Parameter(Mandatory)][string] $Observation,
    [Parameter(Mandatory)][string] $Producer,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression directory.'}
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
$pins=@{}
foreach($path in @($Fixture,$Observation,$Producer)){$pins[$path]=(Get-FileHash -LiteralPath $path).Hash}
$checks=0
function Invoke-Coverage([string]$inputPath,[string]$reportPath,[string]$producerPath,[string]$outputPath) {
    $result=& dotnet $Inspector $RuntimeDirectory $inputPath $outputPath 'state-coverage' $reportPath $producerPath 2>&1
    return [pscustomobject]@{ExitCode=$LASTEXITCODE;Text=($result|Out-String)}
}
function Reject([string]$name,[string]$inputPath,[string]$reportPath,[string]$producerPath,[string]$outputPath,[string]$expected) {
    $result=Invoke-Coverage $inputPath $reportPath $producerPath $outputPath
    if($result.ExitCode-eq0 -or $result.Text-notmatch[regex]::Escape($expected)){throw "Missing rejection $name`: $($result.Text)"}
    if($name-ne'replay' -and (Test-Path -LiteralPath $outputPath)){throw "Rejected $name published a coverage artifact."}
    $script:checks++
}
$positive=Join-Path $OutputDirectory 'positive.json'
$result=Invoke-Coverage $Fixture $Observation $Producer $positive
if($result.ExitCode-ne0){throw $result.Text}
$coverage=Get-Content -LiteralPath $positive -Raw|ConvertFrom-Json
if($coverage.Kind-ne'CompleteObservedRootStateSourceCoverage' -or $coverage.CandidatesRetired-ne0 -or $coverage.States.Count-eq0 -or
    @($coverage.States|Where-Object {$_.Status-notin@('MergedSourceObserved','MergedSourceInMultipleContextsObserved')}).Count-ne0){throw 'Positive fixture lost corroborated source coverage.'}
$checks++
Reject 'replay' $Fixture $Observation $Producer $positive 'fresh coverage output'
$twinDirectory=Join-Path $OutputDirectory 'twin-input'
New-Item -ItemType Directory -Path $twinDirectory | Out-Null
$twin=Join-Path $twinDirectory 'Twin.dll'
Copy-Item -LiteralPath $Fixture -Destination $twin
Reject 'physical-twin' $twin $Observation $Producer (Join-Path $OutputDirectory 'twin-coverage.json') 'physical input path mismatch'
$wrongProducer=Join-Path $OutputDirectory 'WrongProducer.dll'
[IO.File]::WriteAllBytes($wrongProducer,[byte[]](1,2,3,4))
Reject 'producer' $Fixture $Observation $wrongProducer (Join-Path $OutputDirectory 'producer-coverage.json') 'artifact hash mismatch'
$inside=Join-Path (Split-Path $Fixture -Parent) ('rejected-source-coverage-'+[guid]::NewGuid().ToString('N')+'.json')
Reject 'input-tree' $Fixture $Observation $Producer $inside 'fresh coverage output'
foreach($test in @('hash','mvid','partial','path')) {
    $report=Get-Content -LiteralPath $Observation -Raw|ConvertFrom-Json
    $expected=''
    switch($test) {
        'hash' {$report.InputSha256='0'*64;$expected='artifact hash mismatch'}
        'mvid' {$report.Mvid=[guid]::Empty.ToString();$expected='MVID/assembly identity mismatch'}
        'partial' {$report.Roots[0].CompleteTypeScope=$false;$expected='complete observed roots'}
        'path' {$witness=$report.Roots[0].BodyWitnesses|Where-Object {$_.SourceOwnerPath.Count-gt0}|Select-Object -First 1
            $witness.SourceOwnerPath=@($witness.SourceOwnerPath)+@(0x0600FFFF);$expected='Source occurrence path physical declaration mismatch'}
    }
    $changed=Join-Path $OutputDirectory ($test+'-observation.json')
    $report|ConvertTo-Json -Depth 100|Set-Content -LiteralPath $changed -Encoding utf8
    Reject $test $Fixture $changed $Producer (Join-Path $OutputDirectory ($test+'-coverage.json')) $expected
}
foreach($path in $pins.Keys){if((Get-FileHash -LiteralPath $path).Hash-ne$pins[$path]){throw "Input changed: $path"}}
$checks++
Write-Output "PASS: $checks focused native coverage, rejection and immutable-input checks."
