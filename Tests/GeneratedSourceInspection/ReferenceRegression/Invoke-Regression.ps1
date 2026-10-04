param(
    [Parameter(Mandatory)][string] $RuntimeDirectory,
    [Parameter(Mandatory)][string] $Inspector,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference='Stop'
$RuntimeDirectory=[IO.Path]::GetFullPath($RuntimeDirectory)
$Inspector=[IO.Path]::GetFullPath($Inspector)
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a fresh reference regression directory.'}
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
function Run([string[]]$arguments) {
    & dotnet @arguments | Out-Host
    if($LASTEXITCODE -ne 0){throw 'Native reference regression command failed.'}
}
Run @('build',(Join-Path $PSScriptRoot 'ReferenceRegression.csproj'),'-c','Release',"-p:RuntimeDirectory=$RuntimeDirectory","-p:BaseOutputPath=$OutputDirectory/bin/","-p:BaseIntermediateOutputPath=$OutputDirectory/obj/",'-v:q')
Run @("$OutputDirectory/bin/Release/net10.0/ReferenceRegression.dll","$OutputDirectory/fixture")
$fixture=Get-Content -Raw -LiteralPath "$OutputDirectory/fixture/fixture.json" | ConvertFrom-Json
$scenarios=@(@('first','First.dll','bound.json'),@('second','Second.dll','bound.json'),@('missing','First.dll','missing.json'),@('ambiguous','First.dll','ambiguous.json'),@('repeat','First.dll','bound.json'))
foreach($scenario in $scenarios) {
    Run @($Inspector,$RuntimeDirectory,"$OutputDirectory/fixture/$($scenario[1])","$OutputDirectory/$($scenario[0]).json",'inspect',"--references=$OutputDirectory/fixture/$($scenario[2])","--source=$OutputDirectory/$($scenario[0]).cs")
}
$checks=0
function Check([bool]$condition,[string]$message) { $script:checks++; if(!$condition){throw $message} }
$proofs=@{}
foreach($name in @('first','second','missing','ambiguous','repeat')) { $proofs[$name]=Get-Content -Raw -LiteralPath "$OutputDirectory/$name.json" | ConvertFrom-Json }
foreach($name in @('first','second')) {
    $proof=$proofs[$name]
    $target=if($name -eq 'first'){$fixture.Left}else{$fixture.Right}
    $uses=@($proof.Roots[0].NonlocalReferences | Where-Object RequestedAssemblyIdentity -EQ $fixture.Identity)
    Check ($uses.Count -gt 0) "$name has emitted external reference evidence"
    foreach($kind in @('Type','Method','Field')) { Check (@($uses | Where-Object Kind -EQ $kind).Count -gt 0) "$name retains $kind references" }
    Check (@($uses | Where-Object { $_.DefinitionModulePath -ne $target }).Count -eq 0) "$name binds only its own physical twin"
    Check (@($uses | Where-Object { $_.DefinitionModuleMvid -ne $fixture.TwinMvid -or $_.DefinitionToken -eq 0 -or $_.DefinitionAssemblyIdentity -ne $fixture.Identity }).Count -eq 0) "$name retains exact definition identity/MVID/token"
    Check (@($uses | Where-Object OwnerToken -NE 100663297).Count -eq 0) "$name binds uses to local Read owner"
    Check ($proof.NonlocalReferenceAudit.PinnedDefinitions -eq $uses.Count -and $proof.NonlocalReferenceAudit.UnpinnedDefinitions.Count -eq 0) "$name native physical definition audit"
    Check (@($proof.Roots[0].ReferenceTokens | Where-Object { $_ -notin $proof.Roots[0].DeclarationTokens }).Count -eq 0 -and 67108865 -notin $proof.Roots[0].ReferenceTokens) "$name retains local declarations without importing the external field token"
    $printed=@($proof.Roots[0].PrintedReferences | Where-Object RequestedAssemblyIdentity -EQ $fixture.Identity)
    Check ($proof.Roots[0].PrintedReferenceCoverage -and $proof.Roots[0].PrintedReferenceTokens.Count -eq 0) "$name printed coverage excludes declaration names and external tokens"
    foreach($kind in @('Type','Method','Field')) { Check (@($printed | Where-Object { $_.Kind -eq $kind -and !$_.IsDefinition -and !$_.IsImplementationAnnotation }).Count -gt 0) "$name writes actual $kind bindings" }
    Check (@($printed | Where-Object { $_.DefinitionModulePath -ne $target -or $_.DefinitionModuleMvid -ne $fixture.TwinMvid }).Count -eq 0) "$name printed references preserve physical twins"
}
foreach($name in @('missing','ambiguous')) {
    $proof=$proofs[$name]
    $uses=@($proof.Roots[0].NonlocalReferences | Where-Object RequestedAssemblyIdentity -EQ $fixture.Identity)
    Check ($uses.Count -gt 0 -and @($uses | Where-Object DefinitionToken -NE 0).Count -eq 0) "$name keeps unavailable physical definitions unresolved"
    Check ($proof.NonlocalReferenceAudit.PinnedDefinitions -eq 0) "$name has no invented pinned targets"
    Check (@($proof.Roots[0].PrintedReferences | Where-Object { $_.RequestedAssemblyIdentity -eq $fixture.Identity -and $_.DefinitionToken -ne 0 }).Count -eq 0) "$name printed references remain unresolved"
    foreach($kind in @('Type','Method','Field')) { Check (@($uses | Where-Object Kind -EQ $kind).Count -gt 0) "$name retains unresolved $kind signature"
    }
}
Check (($proofs.first.Roots | ConvertTo-Json -Depth 20 -Compress) -eq ($proofs.repeat.Roots | ConvertTo-Json -Depth 20 -Compress)) 'repeated physical reference evidence is deterministic'
Check ((Get-FileHash -LiteralPath "$OutputDirectory/first.cs").Hash -eq (Get-FileHash -LiteralPath "$OutputDirectory/repeat.cs").Hash) 'repeated observation preserves source'
Check ((Get-FileHash -LiteralPath "$OutputDirectory/first.cs").Hash -eq (Get-FileHash -LiteralPath "$OutputDirectory/second.cs").Hash) 'twin callers emit identical source while targets remain distinct'
foreach($property in $fixture.Inputs.PSObject.Properties) { Check ((Get-FileHash -LiteralPath $property.Name).Hash -eq $property.Value) 'fixture binary is unchanged' }
$reports=@{}
foreach($name in $proofs.Keys) { $reports[$name]=@{Path="$OutputDirectory/$name.json";Sha256=(Get-FileHash -LiteralPath "$OutputDirectory/$name.json").Hash} }
@{Checks=$checks;Reports=$reports;Fixture=$fixture;InspectorSha256=(Get-FileHash -LiteralPath $Inspector).Hash;Limits='Synthetic physical-reference observations; no naming, source merging or application compatibility verdict.'} | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath "$OutputDirectory/proof.json"
Write-Output "PASS: $checks exact physical nonlocal reference guards."
