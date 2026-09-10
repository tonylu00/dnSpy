param([Parameter(Mandatory)][string]$BeforeExport,
      [Parameter(Mandatory)][string]$AfterExport,
      [Parameter(Mandatory)][string]$NameCandidatesProject,
      [Parameter(Mandatory)][string]$OutputDirectory,
      [switch]$AlignStateOwners)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new audit output directory.'}
$before=(Resolve-Path -LiteralPath $BeforeExport).Path
$after=(Resolve-Path -LiteralPath $AfterExport).Path
$dependency=[Security.SecurityElement]::Escape((Resolve-Path -LiteralPath $NameCandidatesProject).Path)
$output=[IO.Path]::GetFullPath($OutputDirectory)
function Read-Map($root){
    [xml]$map=Get-Content -LiteralPath (Join-Path $root 'dnspy-export-map.xml') -Raw
    if($map.DnSpyExportMap.ExportErrors -ne '0'){throw "Export is incomplete: $root"}
    $rows=@($map.DnSpyExportMap.Project)
    if(!$rows.Count){throw "Empty export: $root"}
    $result=@{}
    foreach($row in $rows){
        $source=[IO.Path]::GetFullPath($row.Source)
        if($result.ContainsKey($source)){throw "Duplicate physical source: $source"}
        $result[$source]=$row
    }
    return $result
}
$beforeMap=Read-Map $before
$afterMap=Read-Map $after
# A missing project is a failure even when all remaining method bodies match.
$missing=@($beforeMap.Keys | Where-Object {-not $afterMap.ContainsKey($_)})
$added=@($afterMap.Keys | Where-Object {-not $beforeMap.ContainsKey($_)})
if($missing.Count -or $added.Count){throw "Physical project sets differ: $($missing.Count) removed, $($added.Count) added."}
function Binary($root,$row){
    $project=[IO.Path]::GetFullPath((Join-Path $root $row.Project))
    if(-not $project.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Project leaves export tree.'}
    [xml]$xml=Get-Content -LiteralPath $project -Raw
    $tfm=$xml.SelectSingleNode('//TargetFramework').InnerText
    $name=$xml.SelectSingleNode('//AssemblyName').InnerText
    $ext=if($xml.SelectSingleNode('//OutputType').InnerText -eq 'Library'){'.dll'}else{'.exe'}
    $suffix=[IO.Path]::Combine('Release',$tfm,$name+$ext)
    $candidates=@(Get-ChildItem -LiteralPath (Join-Path (Split-Path $project) 'bin') -Recurse -File -Filter "$name$ext" | Where-Object {$_.FullName.EndsWith($suffix,[StringComparison]::OrdinalIgnoreCase)})
    if($candidates.Count -ne 1){throw "Expected one Release output for $project; found $($candidates.Count)"}
    return $candidates[0].FullName
}
New-Item -ItemType Directory -Path $output | Out-Null
'<Project/>' | Set-Content (Join-Path $output 'Directory.Build.props')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'SourceMethodBodies.cs') -Destination $output
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><ImplicitUsings>enable</ImplicitUsings></PropertyGroup><ItemGroup><ProjectReference Include=`"$dependency`"/></ItemGroup></Project>" | Set-Content (Join-Path $output 'Audit.csproj')
dotnet build (Join-Path $output 'Audit.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'Method-body audit build failed.'}
$results=@()
foreach($source in @($afterMap.Keys | Sort-Object)){
    $report=Join-Path $output ('module-{0:D4}.json' -f $results.Count)
    $arguments=@((Binary $before $beforeMap[$source]),(Binary $after $afterMap[$source]))
    if($AlignStateOwners){$arguments+='--align-state-owners'}
    & dotnet (Join-Path $output 'bin\Release\net8.0\Audit.dll') @arguments > $report
    $code=$LASTEXITCODE
    if($code -notin 0,1){throw "Comparator failed for $source (exit $code)"}
    $row=Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    if($null -eq $row.Methods -or $null -eq $row.Differences){throw "Comparator did not return a complete report: $source"}
    $results += [pscustomobject][ordered]@{Source=$source;Methods=$row.Methods;Differences=@($row.Differences).Count;OwnerNameChanges=@($row.OwnerNameChanges).Count;Exit=$code;Report=$report}
}
$summary=[pscustomobject][ordered]@{Before=$before;After=$after;AlignStateOwners=[bool]$AlignStateOwners;Projects=$results.Count;Methods=($results|Measure-Object Methods -Sum).Sum;Differences=($results|Measure-Object Differences -Sum).Sum;OwnerNameChanges=($results|Measure-Object OwnerNameChanges -Sum).Sum;Results=$results}
$summary | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $output 'result.json')
$summary | Select-Object Before,After,Projects,Methods,Differences,OwnerNameChanges | ConvertTo-Json
if(@($results|Where-Object Exit -NE 0).Count){throw 'Method-body differences require review.'}
