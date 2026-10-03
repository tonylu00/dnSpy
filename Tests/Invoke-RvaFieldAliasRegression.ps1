param(
    [Parameter(Mandatory)][string]$DnSpyConsole,
    [Parameter(Mandatory)][string]$FixtureTool,
    [Parameter(Mandatory)][string]$OutputDirectory
)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $root){throw 'Choose a fresh regression output folder.'}
foreach($name in 'library','client','emitter','input'){New-Item -ItemType Directory -Path (Join-Path $root $name) | Out-Null}
'<Project />' | Set-Content (Join-Path $root 'Directory.Build.props')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'FieldDataLibrary.cs') -Destination (Join-Path $root 'library')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'RvaFieldAliasClient.cs') -Destination (Join-Path $root 'client')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitFieldData.cs') -Destination (Join-Path $root 'emitter')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $root 'library/FieldDataLibrary.csproj')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup><ItemGroup><ProjectReference Include="../library/FieldDataLibrary.csproj"/></ItemGroup></Project>' | Set-Content (Join-Path $root 'client/RvaFieldAliasClient.csproj')
$dnlib=[Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $root 'emitter/Emitter.csproj')
dotnet build (Join-Path $root 'client/RvaFieldAliasClient.csproj') -c Release -v quiet
if($LASTEXITCODE){throw 'Synthetic input build failed.'}
$library=Join-Path $root 'input/FieldDataLibrary.dll'; $client=Join-Path $root 'input/RvaFieldAliasClient.exe'
dotnet run --project (Join-Path $root 'emitter/Emitter.csproj') -c Release -- (Join-Path $root 'library/bin/Release/net48/FieldDataLibrary.dll') (Join-Path $root 'client/bin/Release/net48/RvaFieldAliasClient.exe') (Join-Path $root 'input')
if($LASTEXITCODE){throw 'Synthetic RVA emission failed.'}
& $client
if($LASTEXITCODE){throw 'Original behavior failed.'}
$hashes=@(Get-FileHash -LiteralPath $library,$client|ForEach-Object Hash)
$maps=Join-Path $root 'maps'
dotnet $FixtureTool (Join-Path $root 'input') $maps
if($LASTEXITCODE){throw 'Native/map parser guards failed.'}
foreach($workers in 1,4){
    $export=Join-Path $root "export-$workers"
    & $DnSpyConsole --no-color --sdk-project --threads $workers --source-name-map (Join-Path $maps 'names.xml') --asm-path (Join-Path $root 'input') -o $export $library $client
    if($LASTEXITCODE){throw 'Mapped export failed.'}
    $source=(Get-ChildItem -LiteralPath $export -Recurse -Filter '*.cs' | Where-Object FullName -NotMatch '\\(obj|bin)\\' | Get-Content) -join "`n"
    if($source -notmatch 'StoredNumber' -or $source -notmatch 'EnumValues' -or $source -notmatch 'EnumValueStorage'){throw 'Accepted readable aliases are absent.'}
    $project=Get-ChildItem -LiteralPath $export -Recurse -Filter 'RvaFieldAliasClient.csproj' | Select-Object -First 1
    $rebuilt=Join-Path $root "rebuilt-$workers"
    dotnet build $project.FullName -c Release -o $rebuilt -v quiet
    if($LASTEXITCODE){throw 'Mapped source build failed.'}
    & (Join-Path $rebuilt 'RvaFieldAliasClient.exe')
    if($LASTEXITCODE){throw 'Rebuilt behavior/reflection failed.'}
    dotnet run --project (Join-Path $root 'emitter/Emitter.csproj') -c Release -- $library (Join-Path $rebuilt 'FieldDataLibrary.dll')
    if($LASTEXITCODE){throw 'Original field metadata or RVA bytes changed.'}
    $outputs=@(Join-Path $rebuilt 'FieldDataLibrary.dll'; Join-Path $rebuilt 'FieldDataLibrary.pdb')
    $before=@(Get-FileHash -LiteralPath $outputs | ForEach-Object Hash)
    dotnet build $project.FullName -c Release -o $rebuilt -v quiet
    if($LASTEXITCODE){throw 'Incremental build failed.'}
    if(Compare-Object $before @(Get-FileHash -LiteralPath $outputs|ForEach-Object Hash)){throw 'Incremental restoration changed runtime or PDB.'}
    Copy-Item -LiteralPath $client -Destination (Join-Path $rebuilt 'RvaFieldAliasClient.exe') -Force
    & (Join-Path $rebuilt 'RvaFieldAliasClient.exe')
    if($LASTEXITCODE){throw 'Unchanged binary caller failed.'}
}
if(Compare-Object $hashes @(Get-FileHash -LiteralPath $library,$client|ForEach-Object Hash)){throw 'Input binaries changed.'}
$one=Join-Path $root 'export-1'; $four=Join-Path $root 'export-4'
foreach($file in Get-ChildItem -LiteralPath $one -Recurse -Filter '*.cs' -File | Where-Object FullName -NotMatch '\\(obj|bin)\\'){
    $other=Join-Path $four $file.FullName.Substring($one.Length+1)
    if(!(Test-Path -LiteralPath $other) -or (Get-FileHash -LiteralPath $file.FullName).Hash -ne (Get-FileHash -LiteralPath $other).Hash){throw 'Worker-dependent source output.'}
}
'PASS mapped RVA primitive/blob storage, source aliases, original metadata/bytes, unchanged caller, deterministic workers and stable incremental library/PDB.'
