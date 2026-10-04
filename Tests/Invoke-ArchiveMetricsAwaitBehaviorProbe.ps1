param([Parameter(Mandatory)][string] $OriginalModule, [Parameter(Mandatory)][string] $RebuiltModule,
      [Parameter(Mandatory)][string] $DependencyDirectory, [Parameter(Mandatory)][string] $OutputDirectory)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a fresh behavior-probe directory.'}
New-Item -ItemType Directory $OutputDirectory | Out-Null
$pins=@{}
foreach($path in @($OriginalModule,$RebuiltModule)){$pins[$path]=(Get-FileHash $path).Hash}
Copy-Item (Join-Path $PSScriptRoot 'ArchiveMetricsAwaitBehaviorProbe.cs') $OutputDirectory
$references=@($OriginalModule,(Join-Path $DependencyDirectory 'Knx.Ets.Common.dll'),(Join-Path $DependencyDirectory 'Knx.Ets.ObjectModel.dll'),(Join-Path $DependencyDirectory 'Knx.Ets.Telemetry.Abstractions.dll'),(Join-Path $DependencyDirectory 'FluentResults.dll'),(Join-Path $DependencyDirectory 'System.Reactive.dll'),(Join-Path $DependencyDirectory 'log4net.dll')) | ForEach-Object {
    $reference=[Security.SecurityElement]::Escape([IO.Path]::GetFullPath($_))
    $pins[$_] = (Get-FileHash $_).Hash
    "<Reference Include=`"$([IO.Path]::GetFileNameWithoutExtension($_))`"><HintPath>$reference</HintPath><Private>false</Private></Reference>"
}
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup><ItemGroup>$($references -join '')<Reference Include=`"WindowsBase`"/><Reference Include=`"PresentationFramework`"/><Reference Include=`"PresentationCore`"/></ItemGroup></Project>" | Set-Content "$OutputDirectory\Probe.csproj"
dotnet build "$OutputDirectory\Probe.csproj" -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Unchanged archive metrics caller compilation failed.'}
$probe="$OutputDirectory\bin\Release\net48\Probe.exe"
$identity=[Reflection.AssemblyName]::GetAssemblyName([IO.Path]::GetFullPath($OriginalModule)).FullName
if([Reflection.AssemblyName]::GetAssemblyName([IO.Path]::GetFullPath($RebuiltModule)).FullName -cne $identity){throw 'Original/rebuilt archive metrics identity mismatch.'}
foreach($kind in @('original','rebuilt')) {
    $module=if($kind -eq 'original'){$OriginalModule}else{$RebuiltModule}
    & $probe $module $DependencyDirectory $identity "$OutputDirectory\$kind-loaded.tsv" *> "$OutputDirectory\$kind.log"
    if($LASTEXITCODE -ne 0){Get-Content "$OutputDirectory\$kind.log"; throw "$kind archive metrics probe failed."}
    foreach($row in Get-Content "$OutputDirectory\$kind-loaded.tsv") {
        $columns=$row -split "`t"
        if($columns.Count -ne 3 -or (Get-FileHash $columns[1]).Hash -cne $columns[2] -or
           [Reflection.AssemblyName]::GetAssemblyName($columns[1]).FullName -cne $columns[0]){throw 'Loaded caller dependency provenance differs.'}
        $pins[$columns[1]]=$columns[2]
    }
}
if((Get-Content "$OutputDirectory\original.log" -Raw) -cne (Get-Content "$OutputDirectory\rebuilt.log" -Raw)){throw 'Original/rebuilt archive metrics observations differ.'}
foreach($path in $pins.Keys){if((Get-FileHash $path).Hash -ne $pins[$path]){throw 'Input module changed.'}}
Get-Content "$OutputDirectory\rebuilt.log"
