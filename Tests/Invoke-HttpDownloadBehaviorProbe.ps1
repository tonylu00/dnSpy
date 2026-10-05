param([Parameter(Mandatory)][string] $OriginalModule, [Parameter(Mandatory)][string] $RebuiltModule,
      [Parameter(Mandatory)][string] $DependencyDirectory, [Parameter(Mandatory)][string] $OutputDirectory)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a fresh HTTP behavior-probe directory.'}
New-Item -ItemType Directory $OutputDirectory | Out-Null
$pins=@{}
foreach($path in @($OriginalModule,$RebuiltModule)){$pins[[IO.Path]::GetFullPath($path)]=(Get-FileHash $path).Hash}
Copy-Item (Join-Path $PSScriptRoot 'HttpDownloadBehaviorProbe.cs') $OutputDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup><ItemGroup><Reference Include="System.Net.Http"/></ItemGroup></Project>' | Set-Content "$OutputDirectory\Probe.csproj"
dotnet build "$OutputDirectory\Probe.csproj" -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Unchanged HTTP caller compilation failed.'}
$probe="$OutputDirectory\bin\Release\net48\Probe.exe"
$hostConfig=Join-Path $DependencyDirectory 'ETS6N.exe.config'
$pins[$hostConfig]=(Get-FileHash $hostConfig).Hash
Copy-Item -LiteralPath $hostConfig -Destination ($probe+'.config')
$identity=[Reflection.AssemblyName]::GetAssemblyName([IO.Path]::GetFullPath($OriginalModule)).FullName
if([Reflection.AssemblyName]::GetAssemblyName([IO.Path]::GetFullPath($RebuiltModule)).FullName -cne $identity){throw 'Original/rebuilt HTTP assembly identity mismatch.'}
foreach($kind in @('original','rebuilt')) {
    $module=if($kind -eq 'original'){$OriginalModule}else{$RebuiltModule}
    & $probe $module $DependencyDirectory $identity "$OutputDirectory\$kind" *> "$OutputDirectory\$kind.log"
    if($LASTEXITCODE -ne 0){Get-Content "$OutputDirectory\$kind.log" -Tail 12; throw "$kind HTTP probe failed."}
    foreach($row in Get-Content "$OutputDirectory\$kind\loaded.tsv") {
        $columns=$row -split "`t"
        if($columns.Count -ne 3 -or (Get-FileHash $columns[1]).Hash -cne $columns[2] -or
           [Reflection.AssemblyName]::GetAssemblyName($columns[1]).FullName -cne $columns[0]){throw 'Loaded HTTP caller dependency provenance differs.'}
        $pins[$columns[1]]=$columns[2]
    }
}
if((Get-Content "$OutputDirectory\original.log" -Raw) -cne (Get-Content "$OutputDirectory\rebuilt.log" -Raw)){throw 'Original/rebuilt HTTP observations differ.'}
foreach($path in $pins.Keys){if((Get-FileHash $path).Hash -ne $pins[$path]){throw 'Input dependency changed.'}}
@{Kind='HttpDownloadOriginalContractBehavior';Cases=144;OriginalRebuiltObservationsEqual=$true;Pins=$pins;
    Limits='Real original/rebuilt download owners with substituted HTTP transport. No network, live ETS, App, server, progress-callback, pooled-client or whole-application compatibility claim.'} |
    ConvertTo-Json -Depth 5 | Set-Content "$OutputDirectory\proof.json"
Get-Content "$OutputDirectory\rebuilt.log" -Tail 1
