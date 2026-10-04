param(
    [Parameter(Mandatory)][string] $OriginalModule,
    [Parameter(Mandatory)][string] $RebuiltModule,
    [Parameter(Mandatory)][string] $DependencyDirectory,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new probe output folder.'}
New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
$pins=@{}
foreach($path in @($OriginalModule,$RebuiltModule)){$pins[$path]=(Get-FileHash -LiteralPath $path).Hash}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'IteratorSplitDispatchFixture.cs'),(Join-Path $PSScriptRoot 'IteratorSplitDispatchBehaviorProbe.cs') -Destination $OutputDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><StartupObject>IteratorSplitDispatchBehaviorProbe</StartupObject><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content -LiteralPath "$OutputDirectory\Probe.csproj"
dotnet build "$OutputDirectory\Probe.csproj" -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Behavior probe compilation failed.'}
$probe="$OutputDirectory\bin\Release\net48\Probe.exe"
& $probe $OriginalModule $DependencyDirectory *> "$OutputDirectory\original.log"
if($LASTEXITCODE -ne 0){Get-Content "$OutputDirectory\original.log"; throw 'Original module probe failed.'}
& $probe $RebuiltModule $DependencyDirectory *> "$OutputDirectory\rebuilt.log"
if($LASTEXITCODE -ne 0){Get-Content "$OutputDirectory\rebuilt.log"; throw 'Rebuilt module probe failed.'}
if((Get-Content "$OutputDirectory\original.log" -Raw) -cne (Get-Content "$OutputDirectory\rebuilt.log" -Raw)){throw 'Observed original/rebuilt behavior differs.'}
foreach($path in $pins.Keys){if((Get-FileHash -LiteralPath $path).Hash -ne $pins[$path]){throw 'Input module changed.'}}
Get-Content "$OutputDirectory\rebuilt.log"
