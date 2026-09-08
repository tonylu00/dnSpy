param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$deployment = Join-Path $OutputDirectory 'deployment'
$inputs = @()
foreach ($variant in @(@{Name='Root';Value=17;Directory=$deployment},@{Name='Compat';Value=23;Directory=(Join-Path $deployment 'compat\v1')},@{Name='Backup';Value=99;Directory=$deployment})) {
    $compile = Join-Path $OutputDirectory ('compile-' + $variant.Name)
    $library = Join-Path $compile 'library'
    $plugin = Join-Path $compile 'plugin'
    $runner = Join-Path $compile 'runner'
    New-Item -ItemType Directory -Force -Path $library,$plugin,$runner,$variant.Directory,(Join-Path $variant.Directory 'plugins') | Out-Null
    $payload = $variant.Name + 'Payload'
    '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><AssemblyName>Library</AssemblyName></PropertyGroup></Project>' | Set-Content (Join-Path $library 'Library.csproj')
    "public sealed class $payload<T> { public T Value; public $payload(T value) { Value=value; } } public static class Library { public static int Read($payload<int> value) { return value.Value + $($variant.Value); } }" | Set-Content (Join-Path $library 'Library.cs')
    if ($variant.Name -eq 'Backup') {
        dotnet build (Join-Path $library 'Library.csproj') -c Release --nologo -v quiet
        if ($LASTEXITCODE -ne 0) { throw 'Backup fixture build failed.' }
        $backup = Join-Path $deployment 'Library_orig.dll'
        Copy-Item -LiteralPath (Join-Path $library 'bin\Release\net48\Library.dll') -Destination $backup
        $inputs = @($backup) + $inputs
        continue
    }
    '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><AssemblyName>Plugin</AssemblyName></PropertyGroup><ItemGroup><ProjectReference Include="..\library\Library.csproj" /></ItemGroup></Project>' | Set-Content (Join-Path $plugin 'Plugin.csproj')
    "public static class PluginApi { public static int Read() { return Library.Read(new $payload<int>(0)); } }" | Set-Content (Join-Path $plugin 'Plugin.cs')
    '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><AssemblyName>Runner</AssemblyName><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><ProjectReference Include="..\plugin\Plugin.csproj" /></ItemGroup></Project>' | Set-Content (Join-Path $runner 'Runner.csproj')
    "public static class $($variant.Name)Entry { public static int Main() { return PluginApi.Read(); } }" | Set-Content (Join-Path $runner 'Runner.cs')
    dotnet build (Join-Path $runner 'Runner.csproj') -c Release --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Compatibility fixture build failed.' }
    $bin = Join-Path $runner 'bin\Release\net48'
    Copy-Item -LiteralPath (Join-Path $bin 'Runner.exe'),(Join-Path $bin 'Library.dll') -Destination $variant.Directory
    Copy-Item -LiteralPath (Join-Path $bin 'Plugin.dll') -Destination (Join-Path $variant.Directory 'plugins')
    '<configuration><startup><supportedRuntime version="v4.0" sku=".NETFramework,Version=v4.8" /></startup><runtime><assemblyBinding xmlns="urn:schemas-microsoft-com:asm.v1"><probing privatePath="plugins" /></assemblyBinding></runtime></configuration>' | Set-Content (Join-Path $variant.Directory 'Runner.exe.config')
    & (Join-Path $variant.Directory 'Runner.exe')
    if ($LASTEXITCODE -ne $variant.Value) { throw 'Original compatibility layout behaved incorrectly.' }
    $inputs += @((Join-Path $variant.Directory 'Runner.exe'),(Join-Path $variant.Directory 'plugins\Plugin.dll'),(Join-Path $variant.Directory 'Library.dll'))
}
$before = $inputs | Get-FileHash | Select-Object Path,Hash
foreach ($case in @(@{Name='sdk-1';Threads=1;Options=@('--sdk-project')},@{Name='sdk-4';Threads=4;Options=@('--sdk-project')},@{Name='legacy-4';Threads=4;Options=@()})) {
    $export = Join-Path $OutputDirectory ('export-' + $case.Name)
    $options = $case.Options
    $files = [string[]]$inputs.Clone()
    if ($case.Name -eq 'sdk-4') { [Array]::Reverse($files) }
    & $DnSpyConsole --no-color @options --threads $case.Threads -o $export @files
    if ($LASTEXITCODE -ne 0) { throw 'Duplicate assembly export failed.' }
    $projects = @(Get-ChildItem -LiteralPath $export -Filter '*.csproj' -Recurse)
    if ($projects.Count -ne 7) { throw 'A compatibility or backup assembly was dropped.' }
    [xml]$map = Get-Content -LiteralPath (Join-Path $export 'dnspy-export-map.xml')
    $entries = @($map.DnSpyExportMap.Project)
    if ($entries.Count -ne 7 -or $map.DnSpyExportMap.ExportErrors -ne '0') { throw 'Export map is incomplete.' }
    if (Compare-Object ($inputs | Sort-Object) ($entries.Source | Sort-Object)) { throw 'Export map lost source identity.' }
    $mapping = @($entries | ForEach-Object { $_.Source + '|' + $_.Project })
    if ($case.Name -eq 'sdk-1') { $expectedMapping = $mapping }
    elseif (Compare-Object $expectedMapping $mapping -SyncWindow 0) { throw 'Project paths depend on workers or input order.' }
    $solution = Get-ChildItem -LiteralPath $export -Filter '*.sln' | Select-Object -First 1
    dotnet build $solution.FullName -c Release --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Duplicate assembly source build failed.' }
    $restaged = Join-Path $OutputDirectory ('restaged-' + $case.Name)
    Copy-Item -LiteralPath $deployment -Destination $restaged -Recurse
    foreach ($entry in $entries) {
        $prefix = [IO.Path]::GetFullPath($deployment).TrimEnd('\') + '\'
        $sourcePath = [IO.Path]::GetFullPath($entry.Source)
        if (!$sourcePath.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Map source left the fixture tree.' }
        $project = Join-Path $export $entry.Project
        $binaryName = $entry.AssemblyName + [IO.Path]::GetExtension($sourcePath)
        $binary = @(Get-ChildItem -LiteralPath (Join-Path (Split-Path $project) 'bin') -Recurse -File | Where-Object { $_.Name -eq $binaryName })
        if ($binary.Count -ne 1) { throw 'Build output is ambiguous.' }
        Copy-Item -LiteralPath $binary[0].FullName -Destination (Join-Path $restaged $sourcePath.Substring($prefix.Length))
    }
    foreach ($location in @(@{Path='Runner.exe';Value=17},@{Path='compat\v1\Runner.exe';Value=23})) {
        & (Join-Path $restaged $location.Path)
        if ($LASTEXITCODE -ne $location.Value) { throw 'Mapped rebuilt deployment changed compatibility binding.' }
    }
    foreach ($variant in @(@{Name='Root';Value=17},@{Name='Compat';Value=23})) {
        $entry = Get-ChildItem -LiteralPath $export -Recurse -Filter ($variant.Name + 'Entry.cs') | Select-Object -First 1
        $rebuilt = Get-ChildItem -LiteralPath (Join-Path $entry.Directory.FullName 'bin') -Recurse -Filter 'Runner.exe' | Select-Object -First 1
        & $rebuilt.FullName
        if ($LASTEXITCODE -ne $variant.Value) { throw "Rebuilt $($variant.Name) chose another deployment's dependency." }
    }
    Write-Output "PASS: $($case.Name) rebuilt both distinct compatibility graphs and retained the backup."
}
$guards = Join-Path $OutputDirectory 'guards'
New-Item -ItemType Directory -Path $guards | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'DuplicateAssemblyGuards.cs') -Destination $guards
$runtime = Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$dnlib = [Security.SecurityElement]::Escape((Join-Path $runtime 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net48</TargetFramework><LangVersion>latest</LangVersion><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $guards 'Guards.csproj')
dotnet build (Join-Path $guards 'Guards.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Duplicate identity guard build failed.' }
& (Join-Path $guards 'bin\Release\net48\Guards.exe') $runtime $deployment
if ($LASTEXITCODE -ne 0) { throw 'Duplicate identity guards failed.' }
$after = $inputs | Get-FileHash | Select-Object Path,Hash
if (Compare-Object $before $after -Property Path,Hash) { throw 'Duplicate export modified inputs.' }
