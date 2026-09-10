param([Parameter(Mandatory)][string]$DnSpyConsole,[Parameter(Mandatory)][string]$OutputDirectory,[ValidateSet('b','Main')][string]$EntryPointName='b',[switch]$Wpf)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new output directory.'}
foreach($dir in 'library','client','emitter','input'){New-Item -ItemType Directory -Path (Join-Path $OutputDirectory $dir) | Out-Null}
'<Project />' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
foreach($pair in @(@('TypeNameCollisionLibrary.cs','library'),@('TypeNameCollisionClient.cs','client'),@('EmitTypeNameCollision.cs','emitter'))){Copy-Item (Join-Path $PSScriptRoot $pair[0]) (Join-Path $OutputDirectory $pair[1])}
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><Optimize>true</Optimize></PropertyGroup></Project>' | Set-Content (Join-Path $OutputDirectory 'library\TypeNameCollisionLibrary.csproj')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup><ItemGroup><ProjectReference Include="..\library\TypeNameCollisionLibrary.csproj" /></ItemGroup></Project>' | Set-Content (Join-Path $OutputDirectory 'client\TypeNameCollisionClient.csproj')
if($Wpf){
 $clientProject=Join-Path $OutputDirectory 'client\TypeNameCollisionClient.csproj'
 (Get-Content $clientProject -Raw).Replace('<Optimize>true</Optimize>','<Optimize>true</Optimize><UseWPF>true</UseWPF>') | Set-Content $clientProject
 foreach($file in 'WpfAliasProbe.cs','WpfAliasProbe.xaml'){Copy-Item (Join-Path $PSScriptRoot $file) (Join-Path $OutputDirectory 'client')}
 $clientSource=Join-Path $OutputDirectory 'client\TypeNameCollisionClient.cs'
 (Get-Content $clientSource -Raw).Replace('var alpha = new Alpha();','WpfAliasProbe.Check(); var alpha = new Alpha();') | Set-Content $clientSource
}
$dnlib=[Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $OutputDirectory 'emitter\Emitter.csproj')
dotnet build (Join-Path $OutputDirectory 'client\TypeNameCollisionClient.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Input build failed.'}
$inputDir=Join-Path $OutputDirectory 'input'
dotnet run --project (Join-Path $OutputDirectory 'emitter\Emitter.csproj') -c Release -- (Join-Path $OutputDirectory 'library\bin\Release\net48\TypeNameCollisionLibrary.dll') (Join-Path $OutputDirectory 'client\bin\Release\net48\TypeNameCollisionClient.exe') $inputDir $EntryPointName
if($LASTEXITCODE -ne 0){throw 'Metadata emission failed.'}
$exe=Join-Path $inputDir 'TypeNameCollisionClient.exe'; $library=Join-Path $inputDir 'TypeNameCollisionLibrary.dll'
$hashes=@(Get-FileHash $exe,$library | ForEach-Object Hash)
& $exe
if($LASTEXITCODE -ne 0){throw 'Original field references failed.'}
foreach($threads in 1,4){
 $export=Join-Path $OutputDirectory "export-$threads"
 & $DnSpyConsole --no-color --sdk-project --threads $threads --asm-path $inputDir -o $export $library $exe
 if($LASTEXITCODE -ne 0){throw 'Export failed.'}
 $project=Get-ChildItem $export -Recurse -Filter TypeNameCollisionClient.csproj | Select-Object -First 1
 $rebuilt=Join-Path $OutputDirectory "rebuilt-$threads"
 dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
 if($LASTEXITCODE -ne 0){throw 'Rebuilt source failed.'}
 & (Join-Path $rebuilt 'TypeNameCollisionClient.exe')
 if($LASTEXITCODE -ne 0){throw 'Rebuilt references changed.'}
 Copy-Item -LiteralPath $exe -Destination (Join-Path $rebuilt 'TypeNameCollisionClient.exe') -Force
 & (Join-Path $rebuilt 'TypeNameCollisionClient.exe')
 if($LASTEXITCODE -ne 0){throw 'Original binary caller compatibility changed.'}
}
if(Compare-Object $hashes @(Get-FileHash $exe,$library | ForEach-Object Hash)){throw 'Inputs changed.'}
