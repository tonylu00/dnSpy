param([Parameter(Mandatory)][string]$DnSpyConsole, [Parameter(Mandatory)][string]$OutputDirectory, [switch]$WithoutContexts)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new output directory.'}
$support=Join-Path $OutputDirectory 'support'
New-Item -ItemType Directory -Path $support | Out-Null
'<Project />' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
'public class SupportBase { public static string Suffix { get { return " support"; } } }' | Set-Content (Join-Path $support 'Support.cs')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><AssemblyName>Support</AssemblyName></PropertyGroup></Project>' | Set-Content (Join-Path $support 'Support.csproj')
foreach($kind in @('Old','New')) {
 $lib=Join-Path $OutputDirectory "$kind\library"
 $client=Join-Path $OutputDirectory "$kind\client"
 New-Item -ItemType Directory -Path $lib,$client | Out-Null
 "public class ${kind}Api : SupportBase { public static string Read() { return `"$kind`" + Suffix; } }" | Set-Content (Join-Path $lib 'Library.cs')
 '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><AssemblyName>Library</AssemblyName></PropertyGroup><ItemGroup><ProjectReference Include="..\..\support\Support.csproj" /></ItemGroup></Project>' | Set-Content (Join-Path $lib 'Library.csproj')
 "using System; class Client { static int Main() { if (${kind}Api.Read() != `"$kind support`") return 1; Console.WriteLine(`"PASS: $kind context`"); return 0; } }" | Set-Content (Join-Path $client 'Client.cs')
 '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><ProjectReference Include="..\library\Library.csproj" /></ItemGroup></Project>' | Set-Content (Join-Path $client 'Client.csproj')
 dotnet build (Join-Path $client 'Client.csproj') -c Release --nologo -v quiet
 if($LASTEXITCODE -ne 0){throw 'Fixture build failed.'}
 & (Join-Path $client 'bin\Release\net48\Client.exe')
 if($LASTEXITCODE -ne 0){throw 'Original fixture failed.'}
}
# The selected old context must use the explicitly supplied support path.
Remove-Item -LiteralPath (Join-Path $OutputDirectory 'Old\client\bin\Release\net48\Support.dll')
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
 & $DnSpyConsole --no-color --sdk-project --threads $threads --asm-path (Join-Path $support 'bin\Release\net48') @contextArgs -o $export @inputs
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
