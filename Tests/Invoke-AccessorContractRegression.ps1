param([Parameter(Mandatory)][string]$DnSpyConsole,[Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new output directory.'}
foreach($dir in 'library','client','emitter','input'){New-Item -ItemType Directory -Path (Join-Path $OutputDirectory $dir) | Out-Null}
'<Project />' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
foreach($pair in @(@('AccessorContractLibrary.cs','library'),@('AccessorContractClient.cs','client'),@('EmitAccessorContract.cs','emitter'))){Copy-Item (Join-Path $PSScriptRoot $pair[0]) (Join-Path $OutputDirectory $pair[1])}
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><LangVersion>latest</LangVersion><Optimize>true</Optimize></PropertyGroup></Project>' | Set-Content (Join-Path $OutputDirectory 'library\AccessorContractLibrary.csproj')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><LangVersion>latest</LangVersion><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup><ItemGroup><ProjectReference Include="..\library\AccessorContractLibrary.csproj" /></ItemGroup></Project>' | Set-Content (Join-Path $OutputDirectory 'client\AccessorContractClient.csproj')
$dnlib=[Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $OutputDirectory 'emitter\Emitter.csproj')
dotnet build (Join-Path $OutputDirectory 'client\AccessorContractClient.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Input build failed.'}
$inputDir=Join-Path $OutputDirectory 'input'
dotnet run --project (Join-Path $OutputDirectory 'emitter\Emitter.csproj') -c Release -- (Join-Path $OutputDirectory 'library\bin\Release\net48\AccessorContractLibrary.dll') (Join-Path $OutputDirectory 'client\bin\Release\net48\AccessorContractClient.exe') $inputDir
if($LASTEXITCODE -ne 0){throw 'Metadata emission failed.'}
$exe=Join-Path $inputDir 'AccessorContractClient.exe'; $library=Join-Path $inputDir 'AccessorContractLibrary.dll'
$hashes=@(Get-FileHash $exe,$library | ForEach-Object Hash)
& $exe
if($LASTEXITCODE -ne 0){throw 'Original accessor references failed.'}
Add-Type -Path (Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll')
foreach($threads in 1,4){
 $export=Join-Path $OutputDirectory "export-$threads"
 & $DnSpyConsole --no-color --sdk-project --threads $threads --asm-path $inputDir -o $export $library $exe
 if($LASTEXITCODE -ne 0){throw 'Export failed.'}
 $project=Get-ChildItem $export -Recurse -Filter AccessorContractClient.csproj | Select-Object -First 1
 $rebuilt=Join-Path $OutputDirectory "rebuilt-$threads"
 dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
 if($LASTEXITCODE -ne 0){throw 'Rebuilt source failed.'}
 & (Join-Path $rebuilt 'AccessorContractClient.exe')
 if($LASTEXITCODE -ne 0){throw 'Rebuilt references changed.'}
 $runtimeFiles=@(Join-Path $rebuilt 'AccessorContractLibrary.dll'; Join-Path $rebuilt 'AccessorContractLibrary.pdb')
 $before=@(Get-FileHash -LiteralPath $runtimeFiles | ForEach-Object Hash)
 dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
 if($LASTEXITCODE -ne 0){throw 'Incremental build failed.'}
 if(Compare-Object $before @(Get-FileHash -LiteralPath $runtimeFiles | ForEach-Object Hash)){throw 'Incremental restoration changed library or symbols.'}
 Copy-Item -LiteralPath $exe -Destination (Join-Path $rebuilt 'AccessorContractClient.exe') -Force
 & (Join-Path $rebuilt 'AccessorContractClient.exe')
 if($LASTEXITCODE -ne 0){throw 'Original binary caller compatibility changed.'}
}
if(Compare-Object $hashes @(Get-FileHash $exe,$library | ForEach-Object Hash)){throw 'Inputs changed.'}
$one=Join-Path $OutputDirectory 'export-1'
$four=Join-Path $OutputDirectory 'export-4'
foreach($file in Get-ChildItem -LiteralPath $one -Recurse -File -Filter '*.cs' | Where-Object FullName -NotMatch '\\(obj|bin)\\'){
 $relative=$file.FullName.Substring($one.Length+1)
 $other=Join-Path $four $relative
 if(!(Test-Path -LiteralPath $other) -or (Get-FileHash -LiteralPath $file.FullName).Hash -ne (Get-FileHash -LiteralPath $other).Hash){throw "Worker-dependent source: $relative"}
}
Write-Output 'PASS: deterministic source, unchanged inputs and incremental library/PDB hashes'



