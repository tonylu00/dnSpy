param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$library = Join-Path $OutputDirectory 'library'
$consumer = Join-Path $OutputDirectory 'consumer'
$keyHolder = Join-Path $OutputDirectory 'key-holder'
New-Item -ItemType Directory -Path $library,$consumer,$keyHolder | Out-Null
$key = Join-Path $OutputDirectory 'fixture.snk'
$rsa = [Security.Cryptography.RSACryptoServiceProvider]::new(1024)
try { $rsa.PersistKeyInCsp = $false; [IO.File]::WriteAllBytes($key, $rsa.ExportCspBlob($true)) }
finally { $rsa.Dispose() }
$properties = '<TargetFramework>net48</TargetFramework><SignAssembly>true</SignAssembly><AssemblyOriginatorKeyFile>..\fixture.snk</AssemblyOriginatorKeyFile>'
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup>$properties</PropertyGroup></Project>" | Set-Content (Join-Path $keyHolder 'KeyHolder.csproj')
'internal class KeyHolder {}' | Set-Content (Join-Path $keyHolder 'KeyHolder.cs')
dotnet build (Join-Path $keyHolder 'KeyHolder.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Signing-key fixture compilation failed.' }
$publicKey = [BitConverter]::ToString([Reflection.AssemblyName]::GetAssemblyName((Join-Path $keyHolder 'bin\Release\net48\KeyHolder.dll')).GetPublicKey()).Replace('-','')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'FriendAccessLibrary.cs') -Destination $library
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'FriendAccessConsumer.cs') -Destination $consumer
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup>$properties</PropertyGroup></Project>" | Set-Content (Join-Path $library 'FriendLibrary.csproj')
@"
using System.Runtime.CompilerServices;
[assembly: InternalsVisibleTo("FriendApp, PublicKey=$publicKey")]
[assembly: InternalsVisibleTo("ExternalFriend, PublicKey=$publicKey")]
"@ | Set-Content (Join-Path $library 'Friends.cs')
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup>$properties<OutputType>Exe</OutputType></PropertyGroup><ItemGroup><ProjectReference Include=`"..\library\FriendLibrary.csproj`" /></ItemGroup></Project>" | Set-Content (Join-Path $consumer 'FriendApp.csproj')
dotnet build (Join-Path $consumer 'FriendApp.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Signed friend fixture compilation failed.' }
$bin = Join-Path $consumer 'bin\Release\net48'
$inputs = @((Join-Path $bin 'FriendApp.exe'), (Join-Path $bin 'FriendLibrary.dll'))
$before = $inputs | Get-FileHash | Select-Object Path,Hash
& $inputs[0]
if ($LASTEXITCODE -ne 0) { throw 'Signed friend fixture runtime failed.' }
foreach ($case in @(@{Name='sdk-1'; Threads=1; Options=@('--sdk-project')}, @{Name='sdk-4'; Threads=4; Options=@('--sdk-project')}, @{Name='legacy-4'; Threads=4; Options=@()})) {
    $export = Join-Path $OutputDirectory ('export-' + $case.Name)
    $exportOptions = $case.Options
    & $DnSpyConsole --no-color @exportOptions --threads $case.Threads -o $export @inputs
    if ($LASTEXITCODE -ne 0) { throw 'Friend fixture export failed.' }
    $solution = Get-ChildItem -LiteralPath $export -Filter '*.sln' | Select-Object -First 1
    dotnet build $solution.FullName -c Release --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Friend fixture source compilation failed.' }
    $rebuilt = Get-ChildItem -LiteralPath (Join-Path $export 'FriendApp\bin') -Recurse -Filter 'FriendApp.exe' | Select-Object -First 1
    & $rebuilt.FullName
    if ($LASTEXITCODE -ne 0) { throw 'Friend fixture rebuilt runtime failed.' }
    $info = Get-Content (Join-Path $export 'FriendLibrary\Properties\AssemblyInfo.cs') -Raw
    if ($info -notmatch 'InternalsVisibleTo\("FriendApp"\)' -or $info -notmatch [regex]::Escape("ExternalFriend, PublicKey=$publicKey")) {
        throw 'Exported and external friend declarations were not handled separately.'
    }
}
$export = Join-Path $OutputDirectory 'library-only'
& $DnSpyConsole --no-color --sdk-project --threads 4 -o $export $inputs[1]
if ($LASTEXITCODE -ne 0) { throw 'Single library export failed.' }
$info = Get-Content (Join-Path $export 'FriendLibrary\Properties\AssemblyInfo.cs') -Raw
if ($info -notmatch [regex]::Escape("FriendApp, PublicKey=$publicKey")) { throw 'Unexported friend identity changed.' }
$after = $inputs | Get-FileHash | Select-Object Path,Hash
if (Compare-Object $before $after -Property Path,Hash) { throw 'Export changed an input assembly.' }
$guards = Join-Path $OutputDirectory 'guards'
New-Item -ItemType Directory -Path $guards | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'FriendAssemblyGuards.cs') -Destination $guards
$runtime = Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$references = ('dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path = [Security.SecurityElement]::Escape((Join-Path $runtime ($_ + '.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net48</TargetFramework><LangVersion>latest</LangVersion><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $guards 'Guards.csproj')
dotnet build (Join-Path $guards 'Guards.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Friend guards compilation failed.' }
& (Join-Path $guards 'bin\Release\net48\Guards.exe') $runtime $inputs[0] $inputs[1]
if ($LASTEXITCODE -ne 0) { throw 'Friend identity guards failed.' }
Write-Output 'PASS: signed friend graph and isolated library preserve intended source access.'
