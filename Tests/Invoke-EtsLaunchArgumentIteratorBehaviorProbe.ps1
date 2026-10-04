param([Parameter(Mandatory)][string] $OriginalDirectory,
      [Parameter(Mandatory)][string] $ExportDirectory,
      [Parameter(Mandatory)][string] $OutputDirectory)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a fresh probe directory.'}
New-Item -ItemType Directory $OutputDirectory | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'IteratorReturnCleanupFixture.cs') $OutputDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><PlatformTarget>x86</PlatformTarget><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $OutputDirectory 'Probe.csproj')
dotnet build $OutputDirectory -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Probe build failed.'}
$probe=Join-Path $OutputDirectory 'bin\Release\net48\Probe.exe'
foreach($pair in @(@('ETS6N.exe','ETS6N'),@('ETS6C.exe','ETS6N.2'))) {
    $original=Join-Path $OriginalDirectory $pair[0]
    $matches=@(Get-ChildItem (Join-Path $ExportDirectory ($pair[1]+'\bin')) -Recurse -Filter 'ETS6N.exe' | Where-Object {$_.FullName -match '\\Release\\net48\\ETS6N.exe$'})
    if($matches.Count -ne 1){throw 'Expected one physical rebuilt launcher per project.'}
    $rebuilt=$matches[0].FullName
    $originalHash=(Get-FileHash $original).Hash; $rebuiltHash=(Get-FileHash $rebuilt).Hash
    # Separate Framework processes retain each launcher's physical identity/context.
    $expected=@(& $probe $original $OriginalDirectory)
    if($LASTEXITCODE -ne 0){throw 'Original private-parser behavior failed.'}
    $actual=@(& $probe $rebuilt $OriginalDirectory)
    if($LASTEXITCODE -ne 0 -or (Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive)){throw 'Rebuilt private-parser behavior differs.'}
    $expected | Set-Content (Join-Path $OutputDirectory ($pair[0]+'.original.txt'))
    $actual | Set-Content (Join-Path $OutputDirectory ($pair[0]+'.rebuilt.txt'))
    if((Get-FileHash $original).Hash -ne $originalHash -or (Get-FileHash $rebuilt).Hash -ne $rebuiltHash){throw 'Launcher bytes changed.'}
    Write-Output ($pair[0]+': '+($actual -join ' '))
}
