param([Parameter(Mandatory)][string]$DnSpyConsole,[Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
if(Test-Path $OutputDirectory){throw 'Choose a new folder.'}
$source=Join-Path $OutputDirectory 'source'
New-Item -ItemType Directory $source | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'TryEntryFixture.cs') $source
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' | Set-Content (Join-Path $source 'Fixture.csproj')
dotnet build (Join-Path $source 'Fixture.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'Fixture build failed.'}
$inputFile=Join-Path $source 'bin\Release\net48\Fixture.exe'
& $inputFile
if($LASTEXITCODE){throw 'Original runtime failed.'}
$hash=(Get-FileHash $inputFile).Hash
foreach($threads in 1,4){
 $export=Join-Path $OutputDirectory "export-$threads"
 & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $inputFile
 if($LASTEXITCODE){throw 'Export failed.'}
 $project=Get-ChildItem $export -Recurse -Filter '*.csproj' | Select-Object -First 1
 $rebuilt=Join-Path $OutputDirectory "rebuilt-$threads"
 dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
 if($LASTEXITCODE){throw 'Rebuild failed.'}
 & (Join-Path $rebuilt 'Fixture.exe')
 if($LASTEXITCODE){throw 'Rebuilt runtime failed.'}
}
if((Get-FileHash $inputFile).Hash -ne $hash){throw 'Input changed.'}
$one=@(Get-ChildItem (Join-Path $OutputDirectory 'export-1') -Recurse -Filter '*.cs' | Sort-Object FullName | Get-FileHash | ForEach-Object Hash)
$four=@(Get-ChildItem (Join-Path $OutputDirectory 'export-4') -Recurse -Filter '*.cs' | Sort-Object FullName | Get-FileHash | ForEach-Object Hash)
if(Compare-Object $one $four -SyncWindow 0){throw 'Worker count changed source.'}
$debug=Join-Path $OutputDirectory 'debug'
New-Item -ItemType Directory $debug | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'TryEntryDebug.cs') $debug
$runtime=Split-Path $DnSpyConsole
$refs=('dnlib','ICSharpCode.Decompiler','ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','dnSpy.Contracts.Logic' | ForEach-Object {
 $path=[Security.SecurityElement]::Escape((Join-Path $runtime ($_+'.dll')))
 "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$refs</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- $inputFile
if($LASTEXITCODE){throw 'Try entry boundary validation failed.'}
