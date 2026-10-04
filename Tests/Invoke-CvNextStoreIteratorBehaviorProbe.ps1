param([Parameter(Mandatory)][string] $OriginalModule, [Parameter(Mandatory)][string] $RebuiltModule,
      [Parameter(Mandatory)][string] $DependencyDirectory, [Parameter(Mandatory)][string] $OutputDirectory)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a fresh behavior-probe directory.'}
New-Item -ItemType Directory $OutputDirectory | Out-Null
$pins=@{}
foreach($path in @($OriginalModule,$RebuiltModule)){$pins[$path]=(Get-FileHash $path).Hash}
Copy-Item (Join-Path $PSScriptRoot 'CvNextStoreIteratorBehaviorProbe.cs') $OutputDirectory
$reference=[Security.SecurityElement]::Escape([IO.Path]::GetFullPath($OriginalModule))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup><ItemGroup><Reference Include=`"Knx.Ets.CvNext`"><HintPath>$reference</HintPath><Private>false</Private></Reference></ItemGroup></Project>" | Set-Content "$OutputDirectory\Probe.csproj"
$store=Join-Path $OutputDirectory 'store'
New-Item -ItemType Directory $store,"$store\M-00FA","$store\M-0002","$store\P-0001","$store\P-0002","$store\empty" | Out-Null
foreach($name in @('M-00FA\Baggages.xml','M-00FA\Catalog.xml','M-00FA\Hardware.xml','M-00FA\M-00FA_A-0001.xml','M-00FA\M-00FA_A-0002.xml','P-0001\0.xml','P-0001\project.xml','P-0002\project.xml','Device.xml','info.xml')) {
    [IO.File]::WriteAllText((Join-Path $store $name),'<fixture/>')
}
dotnet build "$OutputDirectory\Probe.csproj" -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Unchanged caller compilation failed.'}
$probe="$OutputDirectory\bin\Release\net48\Probe.exe"
& $probe $OriginalModule $DependencyDirectory $store *> "$OutputDirectory\original.log"
if($LASTEXITCODE -ne 0){Get-Content "$OutputDirectory\original.log"; throw 'Original CvNext probe failed.'}
& $probe $RebuiltModule $DependencyDirectory $store *> "$OutputDirectory\rebuilt.log"
if($LASTEXITCODE -ne 0){Get-Content "$OutputDirectory\rebuilt.log"; throw 'Rebuilt CvNext probe failed.'}
if((Get-Content "$OutputDirectory\original.log" -Raw) -cne (Get-Content "$OutputDirectory\rebuilt.log" -Raw)){throw 'Original/rebuilt observations differ.'}
foreach($path in $pins.Keys){if((Get-FileHash $path).Hash -ne $pins[$path]){throw 'Input module changed.'}}
Get-Content "$OutputDirectory\rebuilt.log"
