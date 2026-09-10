param([Parameter(Mandatory)][string]$DnSpyConsole,[Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new output directory.'}
foreach($dir in 'library','client','input'){New-Item -ItemType Directory -Path (Join-Path $OutputDirectory $dir) | Out-Null}
'<Project />' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
foreach($pair in @(@('TupleNamesLibrary.cs','library'),@('TupleNamesClient.cs','client'))){Copy-Item (Join-Path $PSScriptRoot $pair[0]) (Join-Path $OutputDirectory $pair[1])}
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><LangVersion>latest</LangVersion><Optimize>true</Optimize></PropertyGroup></Project>' | Set-Content (Join-Path $OutputDirectory 'library\TupleNamesLibrary.csproj')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><LangVersion>latest</LangVersion><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup><ItemGroup><ProjectReference Include="..\library\TupleNamesLibrary.csproj" /></ItemGroup></Project>' | Set-Content (Join-Path $OutputDirectory 'client\TupleNamesClient.csproj')
dotnet build (Join-Path $OutputDirectory 'client\TupleNamesClient.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Input build failed.'}
$inputDir=Join-Path $OutputDirectory 'input'
Copy-Item (Join-Path $OutputDirectory 'client\bin\Release\net48\TupleNamesClient.exe') $inputDir
Copy-Item (Join-Path $OutputDirectory 'library\bin\Release\net48\TupleNamesLibrary.dll') $inputDir
$exe=Join-Path $inputDir 'TupleNamesClient.exe'; $library=Join-Path $inputDir 'TupleNamesLibrary.dll'
$hashes=@(Get-FileHash $exe,$library | ForEach-Object Hash)
& $exe
if($LASTEXITCODE -ne 0){throw 'Original tuple caller failed.'}
Add-Type -Path (Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll')
foreach($threads in 1,4){
 $export=Join-Path $OutputDirectory "export-$threads"
 & $DnSpyConsole --no-color --sdk-project --threads $threads --asm-path $inputDir -o $export $library $exe
 if($LASTEXITCODE -ne 0){throw 'Export failed.'}
 $project=Get-ChildItem $export -Recurse -Filter TupleNamesClient.csproj | Select-Object -First 1
 $rebuilt=Join-Path $OutputDirectory "rebuilt-$threads"
 dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
 if($LASTEXITCODE -ne 0){throw 'Rebuilt source failed.'}
 & (Join-Path $rebuilt 'TupleNamesClient.exe')
 if($LASTEXITCODE -ne 0){throw 'Rebuilt references changed.'}
 $consumer=Join-Path $OutputDirectory "named-consumer-$threads"
 New-Item -ItemType Directory -Path $consumer | Out-Null
 Copy-Item (Join-Path $PSScriptRoot 'TupleNamesClient.cs') $consumer
 $reference=[Security.SecurityElement]::Escape((Join-Path $rebuilt 'TupleNamesLibrary.dll'))
 "<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net48</TargetFramework><LangVersion>latest</LangVersion><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"TupleNamesLibrary`"><HintPath>$reference</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $consumer 'NamedConsumer.csproj')
 dotnet build (Join-Path $consumer 'NamedConsumer.csproj') -c Release --nologo -v quiet
 if($LASTEXITCODE -ne 0){throw 'Named tuple caller failed to compile against runtime output.'}
 & (Join-Path $consumer 'bin\Release\net48\NamedConsumer.exe')
 if($LASTEXITCODE -ne 0){throw 'Named tuple caller failed.'}
 $runtimeFiles=@(Join-Path $rebuilt 'TupleNamesLibrary.dll'; Join-Path $rebuilt 'TupleNamesLibrary.pdb')
 $before=@(Get-FileHash -LiteralPath $runtimeFiles | ForEach-Object Hash)
 dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
 if($LASTEXITCODE -ne 0){throw 'Incremental build failed.'}
 if(Compare-Object $before @(Get-FileHash -LiteralPath $runtimeFiles | ForEach-Object Hash)){throw 'Incremental restoration changed library or symbols.'}
 Copy-Item -LiteralPath $exe -Destination (Join-Path $rebuilt 'TupleNamesClient.exe') -Force
 & (Join-Path $rebuilt 'TupleNamesClient.exe')
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







