param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$source = Join-Path $OutputDirectory 'source'
$hostSource = Join-Path $source 'host'
$pluginSource = Join-Path $source 'plugin'
New-Item -ItemType Directory -Path $hostSource,$pluginSource | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'SubdirectoryHost.cs') -Destination $hostSource
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'SubdirectoryPlugin.cs') -Destination $pluginSource
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $hostSource 'HostApp.csproj')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><AssemblyName>Plugin</AssemblyName><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $pluginSource 'Plugin.csproj')
dotnet build (Join-Path $hostSource 'HostApp.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Host fixture compilation failed.' }
dotnet build (Join-Path $pluginSource 'Plugin.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Plugin fixture compilation failed.' }
# The input tree holds the host and its private assembly in a subdirectory.
$input = Join-Path $OutputDirectory 'input'
$inputPlugins = Join-Path $input 'Plugins'
New-Item -ItemType Directory -Path $inputPlugins | Out-Null
Copy-Item -LiteralPath (Join-Path $hostSource 'bin\Release\net48\HostApp.exe') -Destination $input
Copy-Item -LiteralPath (Join-Path $pluginSource 'bin\Release\net48\Plugin.dll') -Destination $inputPlugins
$inputExe = Join-Path $input 'HostApp.exe'
$expected = @(& $inputExe)
if ($LASTEXITCODE -ne 21) { throw 'Original host did not load its private assembly.' }
$expected | Set-Content (Join-Path $OutputDirectory 'expected.txt')
$export = Join-Path $OutputDirectory 'export'
& $DnSpyConsole --no-color --sdk-project --app-layout -o $export $inputExe (Join-Path $inputPlugins 'Plugin.dll')
if ($LASTEXITCODE -ne 0) { throw 'Source export failed.' }
$pluginProject = Join-Path $export 'Plugins\Plugin\Plugin.csproj'
if (-not (Test-Path -LiteralPath $pluginProject)) { throw 'The subdirectory project lost its relative path.' }
$solution = Get-ChildItem -LiteralPath $export -Filter '*.sln' | Select-Object -First 1
if (-not (Select-String -LiteralPath $solution.FullName -Pattern 'Plugins\\Plugin\\Plugin.csproj' -Quiet)) {
    throw 'The solution does not reference the subdirectory project.'
}
dotnet build $solution.FullName -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Exported source did not compile without changes.' }
$rebuiltExe = Join-Path $export 'bin\HostApp.exe'
$rebuiltPlugin = Join-Path $export 'bin\Plugins\Plugin.dll'
if (-not (Test-Path -LiteralPath $rebuiltExe)) { throw 'The host output is not in the layout root.' }
if (-not (Test-Path -LiteralPath $rebuiltPlugin)) { throw 'The plug-in output is not in its subdirectory.' }
$actual = @(& $rebuiltExe)
if ($LASTEXITCODE -ne 21) { throw 'Rebuilt host did not find its private assembly in the subdirectory.' }
if (Compare-Object $expected $actual -SyncWindow 0 -CaseSensitive) { throw 'Rebuilt behavior differs from the original.' }
Write-Output 'PASS: subdirectory assembly keeps its path and is found by the rebuilt host.'
