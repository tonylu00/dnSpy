param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$old = Join-Path $OutputDirectory 'old'
$current = Join-Path $OutputDirectory 'current'
$support = Join-Path $OutputDirectory 'support'
$consumer = Join-Path $OutputDirectory 'consumer'
New-Item -ItemType Directory -Path $old,$current,$support,$consumer | Out-Null
$key = Join-Path $OutputDirectory 'fixture.snk'
$rsa = [Security.Cryptography.RSACryptoServiceProvider]::new(2048, [Security.Cryptography.CspParameters]@{KeyNumber=2})
$rsa.PersistKeyInCsp = $false
try { [IO.File]::WriteAllBytes($key, $rsa.ExportCspBlob($true)) } finally { $rsa.Dispose() }
foreach ($item in @(@{Path=$old;Version='1.0.0.0'},@{Path=$current;Version='2.0.0.0'})) {
    $extra = if ($item.Path -eq $current) { '<ItemGroup><ProjectReference Include="..\support\Support.csproj" /></ItemGroup>' } else { '' }
    "<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net48</TargetFramework><AssemblyName>Library</AssemblyName><AssemblyVersion>$($item.Version)</AssemblyVersion><SignAssembly>true</SignAssembly><AssemblyOriginatorKeyFile>..\fixture.snk</AssemblyOriginatorKeyFile></PropertyGroup>$extra</Project>" |
        Set-Content -LiteralPath (Join-Path $item.Path 'Library.csproj')
}
'public static class Library { public static int Read(string value) { return 11; } }' | Set-Content (Join-Path $old 'Library.cs')
'public static class Library { public static int Read(string value) { return 23; } public static int Read(Payload value) { return 31; } }' |
    Set-Content (Join-Path $current 'Library.cs')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework></PropertyGroup></Project>' |
    Set-Content (Join-Path $support 'Support.csproj')
'public sealed class Payload { }' | Set-Content (Join-Path $support 'Payload.cs')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><ProjectReference Include="..\old\Library.csproj" /></ItemGroup></Project>' |
    Set-Content (Join-Path $consumer 'Consumer.csproj')
'public static class Consumer { public static int Main() { return Library.Read("fixture"); } }' | Set-Content (Join-Path $consumer 'Consumer.cs')
dotnet build (Join-Path $consumer 'Consumer.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Consumer fixture build failed.' }
dotnet build (Join-Path $current 'Library.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Updated library fixture build failed.' }
$bin = Join-Path $consumer 'bin\Release\net48'
Copy-Item (Join-Path $current 'bin\Release\net48\Library.dll'),(Join-Path $current 'bin\Release\net48\Support.dll') -Destination $bin -Force
$token = ([Reflection.AssemblyName]::GetAssemblyName((Join-Path $bin 'Library.dll')).GetPublicKeyToken() | ForEach-Object { $_.ToString('x2') }) -join ''
$config = Join-Path $bin 'Consumer.exe.config'
"<configuration><startup><supportedRuntime version=`"v4.0`" sku=`".NETFramework,Version=v4.8`" /></startup><runtime><assemblyBinding xmlns=`"urn:schemas-microsoft-com:asm.v1`"><dependentAssembly><assemblyIdentity name=`"Library`" culture=`"neutral`" publicKeyToken=`"$token`" /><bindingRedirect oldVersion=`"1.0.0.0-1.9.0.0`" newVersion=`"2.0.0.0`" /></dependentAssembly></assemblyBinding></runtime></configuration>" |
    Set-Content -LiteralPath $config
& (Join-Path $bin 'Consumer.exe')
if ($LASTEXITCODE -ne 23) { throw 'Original application binding redirect failed.' }
$export = Join-Path $OutputDirectory 'export'
& $DnSpyConsole --no-color --sdk-project --threads 1 --app-config $config -o $export (Join-Path $bin 'Consumer.exe')
if ($LASTEXITCODE -ne 0) { throw 'Configured export failed.' }
$project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
$xml = Get-Content -LiteralPath $project.FullName -Raw
if ($xml -notmatch 'Support.dll' -or $xml -notmatch 'Library.dll') { throw 'Export lost redirected or transitive file references.' }
$rebuilt = Join-Path $OutputDirectory 'rebuilt'
dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Configured export compilation failed.' }
& (Join-Path $rebuilt 'Consumer.exe')
if ($LASTEXITCODE -ne 23) { throw 'Rebuilt configured application behavior changed.' }

$legacyExport = Join-Path $OutputDirectory 'legacy-export'
& $DnSpyConsole --no-color --threads 1 --app-config $config -o $legacyExport (Join-Path $bin 'Consumer.exe')
if ($LASTEXITCODE -ne 0) { throw 'Traditional project export failed.' }
$legacyProject = Get-ChildItem -LiteralPath $legacyExport -Recurse -Filter '*.csproj' | Select-Object -First 1
$legacyXml = Get-Content -LiteralPath $legacyProject.FullName -Raw
if ($legacyXml -notmatch 'Support.dll' -or $legacyXml -notmatch 'Library.dll') { throw 'Traditional export lost transitive file references.' }

# A host redirect must not silently substitute a different contract when its
# identity or version range does not apply, or no host was explicitly selected.
foreach ($scenario in @('no-config', 'wrong-token', 'wrong-culture', 'outside-range')) {
    $arguments = @('--no-color', '--sdk-project', '--threads', '1')
    if ($scenario -ne 'no-config') {
        [xml] $mismatch = Get-Content -LiteralPath $config -Raw
        $dependency = $mismatch.configuration.runtime.assemblyBinding.dependentAssembly
        switch ($scenario) {
            'wrong-token' { $dependency.assemblyIdentity.SetAttribute('publicKeyToken', '0000000000000000') }
            'wrong-culture' { $dependency.assemblyIdentity.SetAttribute('culture', 'de-DE') }
            'outside-range' { $dependency.bindingRedirect.SetAttribute('oldVersion', '1.1.0.0-1.9.0.0') }
        }
        $mismatchPath = Join-Path $bin ($scenario + '.config')
        $mismatch.Save($mismatchPath)
        $arguments += @('--app-config', $mismatchPath)
    }
    $mismatchExport = Join-Path $OutputDirectory $scenario
    & $DnSpyConsole @arguments -o $mismatchExport (Join-Path $bin 'Consumer.exe')
    if ($LASTEXITCODE -ne 0) { throw "$scenario export failed." }
    $mismatchProject = Get-ChildItem -LiteralPath $mismatchExport -Recurse -Filter '*.csproj' | Select-Object -First 1
    if ((Get-Content -LiteralPath $mismatchProject.FullName -Raw) -match 'Library.dll') {
        throw "$scenario incorrectly selected the incompatible library."
    }
}
'PASS: configured binding redirects and transitive overload dependencies survive export and rebuild.'
