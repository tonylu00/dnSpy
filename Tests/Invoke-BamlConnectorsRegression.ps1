param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory,
    [switch] $SourceAliases
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$inputDirectory = Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory -Path (Join-Path $inputDirectory 'Legacy.Controls') | Out-Null
'<Project />' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'BamlConnectorsFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'BamlConnectorsView.xaml') -Destination (Join-Path $inputDirectory 'Legacy.Controls\OldView.xaml')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><UseWPF>true</UseWPF><Optimize>true</Optimize></PropertyGroup></Project>' |
    Set-Content (Join-Path $inputDirectory 'BamlConnectorsFixture.csproj')
dotnet build (Join-Path $inputDirectory 'BamlConnectorsFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'BAML connector fixture compilation failed.' }
$original = Join-Path $inputDirectory 'bin\Release\net48\BamlConnectorsFixture.exe'
& $original
if ($LASTEXITCODE -ne 0) { throw 'Original BAML connector behavior failed.' }
$hash = (Get-FileHash -LiteralPath $original).Hash
$mapArguments = @()
if ($SourceAliases) {
    Add-Type -Path (Join-Path (Split-Path $DnSpyConsole) 'dnlib.dll')
    $module = [dnlib.DotNet.ModuleDefMD]::Load($original)
    try {
        [xml]$map = '<SourceNameMap Version="1"><Module /></SourceNameMap>'
        $map.DocumentElement.SetAttribute('InputDirectory', (Split-Path $original))
        $row = $map.DocumentElement.SelectSingleNode('Module')
        $row.SetAttribute('Path', (Split-Path $original -Leaf))
        $row.SetAttribute('Mvid', $module.Mvid.ToString())
        $row.SetAttribute('Sha256', $hash)
        $type = $module.GetTypes() | Where-Object FullName -EQ 'ConnectorFixture.View'
        foreach ($name in 'OnClick','OnStyledClick','OnAttachedClick') {
            $method = $type.Methods | Where-Object {$_.Name.String -ceq $name}
            $entry = $map.CreateElement('Method')
            $entry.SetAttribute('Token', ('0x{0:X8}' -f $method.MDToken.Raw))
            $entry.SetAttribute('ExpectedName', $name)
            $entry.SetAttribute('Signature', $method.FullName)
            $entry.SetAttribute('NewName', 'Mapped' + $name)
            $null = $row.AppendChild($entry)
        }
        $map.Save((Join-Path $OutputDirectory 'names.xml'))
        $mapArguments = @('--source-name-map', (Join-Path $OutputDirectory 'names.xml'))
    } finally { $module.Dispose() }
}
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads @mapArguments -o $export $original
    if ($LASTEXITCODE -ne 0) { throw 'BAML connector source export failed.' }
    if ($SourceAliases) {
        $xaml = (Get-ChildItem -LiteralPath $export -Recurse -Filter '*.xaml' | Get-Content) -join "`n"
        foreach ($name in 'OnClick','OnStyledClick','OnAttachedClick') {
            if (!$xaml.Contains('="Mapped' + $name + '"')) { throw "XAML handler alias missing: $name" }
        }
    }
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Exported BAML connector compilation failed.' }
    & (Join-Path $rebuilt 'BamlConnectorsFixture.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Rebuilt BAML connector behavior changed.' }
}
if ((Get-FileHash -LiteralPath $original).Hash -ne $hash) { throw 'Original assembly changed.' }
