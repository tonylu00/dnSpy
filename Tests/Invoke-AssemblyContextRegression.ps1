param([Parameter(Mandatory)][string]$DnSpyConsole, [Parameter(Mandatory)][string]$OutputDirectory, [switch]$WithoutContexts)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new output directory.'}
foreach($kind in @('Old','New')) {
 $lib=Join-Path $OutputDirectory "$kind\library"
 $client=Join-Path $OutputDirectory "$kind\client"
 New-Item -ItemType Directory -Path $lib,$client | Out-Null
 "public static class ${kind}Api { public static string Read() { return `"$kind`"; } }" | Set-Content (Join-Path $lib 'Library.cs')
 '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><AssemblyName>Library</AssemblyName></PropertyGroup></Project>' | Set-Content (Join-Path $lib 'Library.csproj')
 "using System; class Client { static int Main() { if (${kind}Api.Read() != `"$kind`") return 1; Console.WriteLine(`"PASS: $kind context`"); return 0; } }" | Set-Content (Join-Path $client 'Client.cs')
 '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><ProjectReference Include="..\library\Library.csproj" /></ItemGroup></Project>' | Set-Content (Join-Path $client 'Client.csproj')
 dotnet build (Join-Path $client 'Client.csproj') -c Release --nologo -v quiet
 if($LASTEXITCODE -ne 0){throw 'Fixture build failed.'}
 & (Join-Path $client 'bin\Release\net48\Client.exe')
 if($LASTEXITCODE -ne 0){throw 'Original fixture failed.'}
}
$hostRoot=Join-Path $OutputDirectory 'host'
New-Item -ItemType Directory -Path $hostRoot | Out-Null
Copy-Item (Join-Path $OutputDirectory 'New\client\bin\Release\net48\Client.exe') $hostRoot
Copy-Item (Join-Path $OutputDirectory 'New\client\bin\Release\net48\Library.dll') $hostRoot
Copy-Item (Join-Path $OutputDirectory 'Old\client\bin\Release\net48\Client.exe') (Join-Path $hostRoot 'AlternateClient.exe')
$source=[Security.SecurityElement]::Escape((Join-Path $hostRoot 'AlternateClient.exe'))
$directory=[Security.SecurityElement]::Escape((Join-Path $OutputDirectory 'Old\client\bin\Release\net48'))
$manifest=Join-Path $OutputDirectory 'contexts.xml'
"<AssemblyContexts><Context Source=`"$source`" Directory=`"$directory`" /></AssemblyContexts>" | Set-Content $manifest
$inputs=@(Get-ChildItem $hostRoot -File | ForEach-Object FullName)
$hashes=@($inputs | Get-FileHash | ForEach-Object Hash)
foreach($threads in @(1,4)) {
 $export=Join-Path $OutputDirectory "export-$threads"
 $contextArgs=if($WithoutContexts){@()}else{@('--assembly-contexts',$manifest)}
 & $DnSpyConsole --no-color --sdk-project --threads $threads @contextArgs -o $export @inputs
 if($LASTEXITCODE -ne 0){throw 'Context export failed.'}
 [xml]$map=Get-Content (Join-Path $export 'dnspy-export-map.xml')
 foreach($entry in $map.DnSpyExportMap.Project | Where-Object Source -like '*.exe') {
  $project=Join-Path $export $entry.Project
  $rebuilt=Join-Path $OutputDirectory ("rebuilt-$threads-"+[IO.Path]::GetFileNameWithoutExtension($entry.Source))
  dotnet build $project -c Release -o $rebuilt --nologo -v quiet
  if($LASTEXITCODE -ne 0){throw 'Context source rebuild failed.'}
  & (Join-Path $rebuilt 'Client.exe')
  if($LASTEXITCODE -ne 0){throw 'Rebuilt context behavior changed.'}
 }
}
if(Compare-Object $hashes @($inputs | Get-FileHash | ForEach-Object Hash)){throw 'Input changed.'}
