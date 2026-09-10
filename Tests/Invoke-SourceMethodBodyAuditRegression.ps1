param([Parameter(Mandatory)][string]$NameCandidatesProject,
      [Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression directory.'}
$output=[IO.Path]::GetFullPath($OutputDirectory)
$dependency=[Security.SecurityElement]::Escape((Resolve-Path -LiteralPath $NameCandidatesProject).Path)
$generator=Join-Path $output 'generator'
New-Item -ItemType Directory -Path $generator | Out-Null
'<Project/>' | Set-Content (Join-Path $generator 'Directory.Build.props')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'SourceMethodBodyAuditFixture.cs') -Destination $generator
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><ImplicitUsings>enable</ImplicitUsings></PropertyGroup><ItemGroup><ProjectReference Include=`"$dependency`"/></ItemGroup></Project>" | Set-Content (Join-Path $generator 'Fixture.csproj')
dotnet run --project (Join-Path $generator 'Fixture.csproj') -c Release -- (Join-Path $output 'trees')
if($LASTEXITCODE){throw 'Fixture generation failed.'}
$hashes=@(Get-ChildItem -LiteralPath (Join-Path $output 'trees') -File -Recurse | Get-FileHash)
$audit=Join-Path $PSScriptRoot 'Invoke-SourceMethodBodyAudit.ps1'
& $audit -BeforeExport "$output\trees\before" -AfterExport "$output\trees\after" -NameCandidatesProject $NameCandidatesProject -OutputDirectory "$output\equal"
$equal=Get-Content "$output\equal\result.json" -Raw|ConvertFrom-Json
if($equal.Projects -ne 2 -or $equal.Methods -ne 2 -or $equal.Differences -ne 0){throw 'Duplicate physical assemblies were not checked separately.'}
try{& $audit -BeforeExport "$output\trees\before" -AfterExport "$output\trees\changed" -NameCandidatesProject $NameCandidatesProject -OutputDirectory "$output\changed"; throw 'Changed body accepted.'}
catch{if($_.Exception.Message -ne 'Method-body differences require review.'){throw}}
$changed=Get-Content "$output\changed\result.json" -Raw|ConvertFrom-Json
$difference=@($changed.Results|Where-Object Differences -NE 0)
if($changed.Differences -ne 1 -or $difference.Count -ne 1 -or $difference[0].Source -notlike '*\compat\Library.dll'){throw 'Changed compatibility assembly was not isolated.'}
try{& $audit -BeforeExport "$output\trees\before" -AfterExport "$output\trees\missing" -NameCandidatesProject $NameCandidatesProject -OutputDirectory "$output\missing"; throw 'Missing project accepted.'}
catch{if($_.Exception.Message -notlike 'Physical project sets differ: 1 removed, 0 added.*'){throw}}
foreach($hash in $hashes){if((Get-FileHash -LiteralPath $hash.Path).Hash -ne $hash.Hash){throw 'Audit modified an input.'}}
foreach($context in @('host','compat')){
    $split=Join-Path $output ('baseline-'+$context)
    Copy-Item -LiteralPath "$output\trees\before" -Destination $split -Recurse
    [xml]$map=Get-Content "$split\dnspy-export-map.xml" -Raw
    foreach($row in @($map.DnSpyExportMap.Project)){if($row.Project -notlike "$context\*"){$map.DnSpyExportMap.RemoveChild($row)|Out-Null}}
    $map.Save("$split\dnspy-export-map.xml")
}
& $audit -BeforeExport "$output\baseline-host" -AdditionalBeforeExports "$output\baseline-compat" -AfterExport "$output\trees\after" -NameCandidatesProject $NameCandidatesProject -OutputDirectory "$output\union"
$union=Get-Content "$output\union\result.json" -Raw|ConvertFrom-Json
if($union.Projects -ne 2 -or $union.Methods -ne 2 -or $union.Differences -ne 0 -or $union.BeforeExports.Count -ne 2){throw 'Baseline union lost physical coverage.'}
try{& $audit -BeforeExport "$output\trees\before" -AdditionalBeforeExports "$output\baseline-compat" -AfterExport "$output\trees\after" -NameCandidatesProject $NameCandidatesProject -OutputDirectory "$output\overlap";throw 'Overlapping baseline accepted.'}
catch{if($_.Exception.Message -notlike 'Overlapping baseline physical source:*'){throw}}
'PASS: disjoint baseline union and overlapping-source rejection.'
'PASS: complete physical coverage, distinct compatibility bodies, changed-body rejection, missing-project rejection and input preservation.'
