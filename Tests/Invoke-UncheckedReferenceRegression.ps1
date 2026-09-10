param([Parameter(Mandatory)][string]$DnSpyConsole,[Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new output folder.'}
$library=Join-Path $OutputDirectory 'library'; $client=Join-Path $OutputDirectory 'client'; $emitter=Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $library,$client,$emitter | Out-Null
'<Project/>' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
Copy-Item (Join-Path $PSScriptRoot 'UncheckedReferenceLibrary.cs') $library
Copy-Item (Join-Path $PSScriptRoot 'UncheckedReferenceClient.cs') $client
Copy-Item (Join-Path $PSScriptRoot 'EmitUncheckedReference.cs') $emitter
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><Optimize>true</Optimize></PropertyGroup><ItemGroup><Reference Include="System.Configuration"/></ItemGroup></Project>' | Set-Content (Join-Path $library 'UncheckedReferenceLibrary.csproj')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup><ItemGroup><ProjectReference Include="..\library\UncheckedReferenceLibrary.csproj"/></ItemGroup></Project>' | Set-Content (Join-Path $client 'UncheckedReferenceClient.csproj')
$dnlib=[Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitter 'Emitter.csproj')
dotnet build (Join-Path $client 'UncheckedReferenceClient.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Fixture build failed.'}
$inputFolder=Join-Path $OutputDirectory 'input'
dotnet run --project (Join-Path $emitter 'Emitter.csproj') -c Release -- (Join-Path $library 'bin\Release\net48\UncheckedReferenceLibrary.dll') (Join-Path $client 'bin\Release\net48\UncheckedReferenceClient.exe') $inputFolder
if($LASTEXITCODE -ne 0){throw 'Unchecked reference emission failed.'}
$inputs=@((Join-Path $inputFolder 'UncheckedReferenceLibrary.dll'),(Join-Path $inputFolder 'UncheckedReferenceClient.exe'))
$hashes=@($inputs | Get-FileHash | ForEach-Object Hash)
$originalOutput = @(& $inputs[1])
$originalOutput | Write-Output
if($LASTEXITCODE -ne 0){throw 'Original unchecked reference behavior failed.'}
foreach($threads in 1,4){
 $export=Join-Path $OutputDirectory "export-$threads"
 & $DnSpyConsole --no-color --sdk-project --threads $threads --asm-path $inputFolder -o $export @inputs
 if($LASTEXITCODE -ne 0){throw 'Export failed.'}
 $sources=@(Get-ChildItem $export -Recurse -Filter '*.cs' | Sort-Object FullName | Get-FileHash | ForEach-Object Hash)
 if($threads -eq 1){$firstSources=$sources}else{if(Compare-Object $firstSources $sources -SyncWindow 0){throw 'Source varies by worker count.'}}
 $project=Get-ChildItem $export -Recurse -Filter 'UncheckedReferenceClient.csproj' | Select-Object -First 1
 dotnet build $project.FullName -c Release --nologo -v quiet
 if($LASTEXITCODE -ne 0){throw 'Unchecked reference source compilation failed.'}
 $exe=Join-Path $project.DirectoryName 'bin\Release\net48\UncheckedReferenceClient.exe'
 $rebuiltOutput = @(& $exe)
 $rebuiltOutput | Write-Output
 if($LASTEXITCODE -ne 0){throw 'Rebuilt unchecked reference behavior failed.'}
 if(Compare-Object $originalOutput $rebuiltOutput -SyncWindow 0){throw 'Rebuilt runtime type-test behavior differs from original.'}
 Add-Type -Path (Join-Path (Split-Path $DnSpyConsole) 'dnlib.dll')
 $metadata = [dnlib.DotNet.ModuleDefMD]::Load((Join-Path (Split-Path $exe) 'UncheckedReferenceLibrary.dll'))
 try {
  $readFirst = ($metadata.GetTypes() | Where-Object FullName -eq 'ReferenceStore').Methods | Where-Object Name -eq 'ReadFirst'
  if(@($readFirst.Body.Instructions | Where-Object {$_.OpCode.Code -eq [dnlib.DotNet.Emit.Code]::Isinst -and $_.Operand.FullName -eq 'FirstValue'}).Count -ne 1){throw 'Original same-type isinst instruction was lost.'}
 } finally { $metadata.Dispose() }
 $unchanged=Join-Path $OutputDirectory "unchanged-client-$threads"
 New-Item -ItemType Directory -Path $unchanged | Out-Null
 Copy-Item -LiteralPath $inputs[1] -Destination $unchanged
 Get-ChildItem (Split-Path $exe) -Filter '*.dll' -File | Copy-Item -Destination $unchanged
 $unchangedExe=Join-Path $unchanged 'UncheckedReferenceClient.exe'
 $unchangedOutput = @(& $unchangedExe)
 $unchangedOutput | Write-Output
 if($LASTEXITCODE -ne 0 -or (Get-FileHash $unchangedExe).Hash -ne (Get-FileHash $inputs[1]).Hash){throw 'Unchanged unchecked reference caller failed.'}
 if(Compare-Object $originalOutput $unchangedOutput -SyncWindow 0){throw 'Unchanged caller type-test behavior differs from original.'}
 $outputs=@(Get-ChildItem (Split-Path $exe) -File | Where-Object Extension -in '.exe','.dll','.pdb' | Sort-Object Name | Get-FileHash | ForEach-Object Hash)
 dotnet build $project.FullName -c Release --nologo -v quiet
 if($LASTEXITCODE -ne 0){throw 'Incremental build failed.'}
 if(Compare-Object $outputs @(Get-ChildItem (Split-Path $exe) -File | Where-Object Extension -in '.exe','.dll','.pdb' | Sort-Object Name | Get-FileHash | ForEach-Object Hash) -SyncWindow 0){throw 'Incremental build changed restored output.'}
}
if(Compare-Object $hashes @($inputs | Get-FileHash | ForEach-Object Hash) -SyncWindow 0){throw 'Input changed.'}



