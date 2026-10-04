param([Parameter(Mandatory)][string] $OriginalModule, [Parameter(Mandatory)][string] $RebuiltModule,
      [Parameter(Mandatory)][string] $DependencyDirectory, [Parameter(Mandatory)][string] $OutputDirectory)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a fresh behavior-probe directory.'}
New-Item -ItemType Directory $OutputDirectory | Out-Null
$pins=@{}
foreach($path in @($OriginalModule,$RebuiltModule)){$pins[$path]=(Get-FileHash $path).Hash}
Copy-Item (Join-Path $PSScriptRoot 'XmlDescendantsBehaviorProbe.cs') $OutputDirectory
$reference=[Security.SecurityElement]::Escape([IO.Path]::GetFullPath($OriginalModule))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup><ItemGroup><Reference Include=`"Knx.Ets.Xml.ObjectModel`"><HintPath>$reference</HintPath><Private>false</Private></Reference></ItemGroup></Project>" | Set-Content "$OutputDirectory\Probe.csproj"
dotnet build "$OutputDirectory\Probe.csproj" -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Unchanged caller compilation failed.'}
$probe="$OutputDirectory\bin\Release\net48\Probe.exe"
foreach($kind in @('original','rebuilt')) {
    $module=if($kind -eq 'original'){$OriginalModule}else{$RebuiltModule}
    & $probe $module $DependencyDirectory *> "$OutputDirectory\$kind.log"
    if($LASTEXITCODE -ne 0){Get-Content "$OutputDirectory\$kind.log"; throw "$kind XML probe failed."}
}
if((Get-Content "$OutputDirectory\original.log" -Raw) -cne (Get-Content "$OutputDirectory\rebuilt.log" -Raw)){throw 'Original/rebuilt descendants observations differ.'}
foreach($path in $pins.Keys){if((Get-FileHash $path).Hash -ne $pins[$path]){throw 'Input module changed.'}}
Get-Content "$OutputDirectory\rebuilt.log"
