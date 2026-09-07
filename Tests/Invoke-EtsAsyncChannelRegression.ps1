param(
    [Parameter(Mandatory)][string] $OriginalAssembly,
    [Parameter(Mandatory)][string] $ProcessedAssembly,
    [Parameter(Mandatory)][string] $ExportedSourceFile,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression output folder.'}
$original=(Resolve-Path -LiteralPath $OriginalAssembly).Path
$processed=(Resolve-Path -LiteralPath $ProcessedAssembly).Path
$source=(Resolve-Path -LiteralPath $ExportedSourceFile).Path
$component=Join-Path $OutputDirectory 'component'
$probe=Join-Path $OutputDirectory 'probe'
New-Item -ItemType Directory -Path $component,$probe | Out-Null
Copy-Item -LiteralPath $source -Destination (Join-Path $component 'Async.cs')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EtsAsyncChannelProbe.cs') -Destination $probe
$references=('Microsoft.Bcl.AsyncInterfaces','System.Threading.Tasks.Extensions','System.Threading.Channels','System.Runtime.CompilerServices.Unsafe' | ForEach-Object {
    $path=[Security.SecurityElement]::Escape((Join-Path (Split-Path $processed) ($_+'.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
foreach($build in @(@{Path=$component;Name='AsyncComponent';Kind='Library'},@{Path=$probe;Name='EtsAsyncChannelProbe';Kind='Exe'})) {
    $project=Join-Path $build.Path 'Probe.csproj'
    "<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net48</TargetFramework><LangVersion>latest</LangVersion><AssemblyName>$($build.Name)</AssemblyName><OutputType>$($build.Kind)</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content -LiteralPath $project
    dotnet build $project -c Release --nologo -v quiet
    if($LASTEXITCODE -ne 0){throw 'Channel component or probe build failed.'}
}
$componentSourceHash=(Get-FileHash -LiteralPath (Join-Path $component 'Async.cs')).Hash
if($componentSourceHash -ne (Get-FileHash -LiteralPath $source).Hash){throw 'Exported component source changed.'}
$results=foreach($target in @(@{Name='original';Path=$original},@{Name='processed';Path=$processed},@{Name='rebuilt';Path=(Join-Path $component 'bin\Release\net48\AsyncComponent.dll')})) {
    $runtime=Join-Path $OutputDirectory $target.Name
    Copy-Item -LiteralPath (Join-Path $probe 'bin\Release\net48') -Destination $runtime -Recurse
    $assembly=Join-Path $runtime ([IO.Path]::GetFileName($target.Path))
    Copy-Item -LiteralPath $target.Path -Destination $assembly
    $inputHash=(Get-FileHash -LiteralPath $target.Path).Hash
    $copyHash=(Get-FileHash -LiteralPath $assembly).Hash
    if($inputHash -ne $copyHash){throw 'Test assembly copy changed.'}
    $records=Join-Path $runtime 'records.txt'
    & (Join-Path $runtime 'EtsAsyncChannelProbe.exe') $assembly $records | Tee-Object -FilePath (Join-Path $runtime 'result.log') | Out-Host
    if($LASTEXITCODE -ne 0){throw "Channel behavior failed: $($target.Name)"}
    @{Name=$target.Name;Input=$target.Path;LoadedCopy=$assembly;InputHash=$inputHash;CopyHash=$copyHash;RecordsHash=(Get-FileHash -LiteralPath $records).Hash;Cases=(Get-Content -LiteralPath $records).Count}
}
if(@($results.RecordsHash | Select-Object -Unique).Count -ne 1){throw 'Original, processed and rebuilt channel behavior differ.'}
@{ExportedSource=$source;SourceHash=$componentSourceHash;Results=$results} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'results.json')
