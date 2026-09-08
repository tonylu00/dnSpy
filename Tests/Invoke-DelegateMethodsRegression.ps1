param([Parameter(Mandatory)][string]$DnSpyConsole,[Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new output folder.'}
$library=Join-Path $OutputDirectory 'library'; $client=Join-Path $OutputDirectory 'client'; $emitter=Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $library,$client,$emitter | Out-Null
'<Project/>' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
Copy-Item (Join-Path $PSScriptRoot 'DelegateMethodsLibrary.cs') $library
Copy-Item (Join-Path $PSScriptRoot 'DelegateMethodsClient.cs') $client
Copy-Item (Join-Path $PSScriptRoot 'EmitDelegateMethods.cs') $emitter
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><Optimize>true</Optimize></PropertyGroup></Project>' | Set-Content (Join-Path $library 'DelegateMethodsLibrary.csproj')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup><ItemGroup><ProjectReference Include="..\library\DelegateMethodsLibrary.csproj"/></ItemGroup></Project>' | Set-Content (Join-Path $client 'DelegateMethodsClient.csproj')
$dnlib=[Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitter 'Emitter.csproj')
dotnet build (Join-Path $client 'DelegateMethodsClient.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Fixture build failed.'}
$inputFolder=Join-Path $OutputDirectory 'input'
dotnet run --project (Join-Path $emitter 'Emitter.csproj') -c Release -- (Join-Path $library 'bin\Release\net48\DelegateMethodsLibrary.dll') (Join-Path $client 'bin\Release\net48\DelegateMethodsClient.exe') $inputFolder
if($LASTEXITCODE -ne 0){throw 'Delegate method emission failed.'}
$inputs=@((Join-Path $inputFolder 'DelegateMethodsLibrary.dll'),(Join-Path $inputFolder 'DelegateMethodsClient.exe'))
$hashes=@($inputs | Get-FileHash | ForEach-Object Hash)
& $inputs[1]
if($LASTEXITCODE -ne 0){throw 'Original delegate method behavior failed.'}
foreach($threads in 1,4){
 $export=Join-Path $OutputDirectory "export-$threads"
 & $DnSpyConsole --no-color --sdk-project --threads $threads --asm-path $inputFolder -o $export @inputs
 if($LASTEXITCODE -ne 0){throw 'Export failed.'}
 $sources=@(Get-ChildItem $export -Recurse -Filter '*.cs' | Sort-Object FullName | Get-FileHash | ForEach-Object Hash)
 if($threads -eq 1){$firstSources=$sources}else{if(Compare-Object $firstSources $sources -SyncWindow 0){throw 'Source varies by worker count.'}}
 $project=Get-ChildItem $export -Recurse -Filter 'DelegateMethodsClient.csproj' | Select-Object -First 1
 dotnet build $project.FullName -c Release --nologo -v quiet
 if($LASTEXITCODE -ne 0){throw 'Delegate method source compilation failed.'}
 $exe=Join-Path $project.DirectoryName 'bin\Release\net48\DelegateMethodsClient.exe'
 & $exe
 if($LASTEXITCODE -ne 0){throw 'Rebuilt delegate method behavior failed.'}
 $outputs=@(Get-ChildItem (Split-Path $exe) -File | Where-Object Extension -in '.exe','.dll','.pdb' | Sort-Object Name | Get-FileHash | ForEach-Object Hash)
 dotnet build $project.FullName -c Release --nologo -v quiet
 if($LASTEXITCODE -ne 0){throw 'Incremental build failed.'}
 if(Compare-Object $outputs @(Get-ChildItem (Split-Path $exe) -File | Where-Object Extension -in '.exe','.dll','.pdb' | Sort-Object Name | Get-FileHash | ForEach-Object Hash) -SyncWindow 0){throw 'Incremental build changed restored output.'}
}
if(Compare-Object $hashes @($inputs | Get-FileHash | ForEach-Object Hash) -SyncWindow 0){throw 'Input changed.'}
