param([Parameter(Mandatory)][string]$DnSpyConsole, [Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression output folder.'}
$source=Join-Path $OutputDirectory 'source'
New-Item -ItemType Directory -Path $source | Out-Null
'<Project />' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include="System.Configuration" /></ItemGroup></Project>' | Set-Content (Join-Path $source 'ConfigTokenFixture.csproj')
'using System; using System.Configuration; class Program { static int Main() { if(ConfigurationManager.AppSettings["message"]!="left & right") return 1; Console.WriteLine("PASS: application settings and unsigned configuration load"); return 0; } }' | Set-Content (Join-Path $source 'Program.cs')
dotnet build $source -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Fixture build failed.'}
$original=Join-Path $source 'bin\Release\net48\ConfigTokenFixture.exe'
$config=$original+'.config'
@"
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <!-- Preserve application settings and binding details. -->
  <appSettings><add key="message" value="left &amp; right" /></appSettings>
  <runtime><assemblyBinding xmlns="urn:schemas-microsoft-com:asm.v1">
    <dependentAssembly><assemblyIdentity name="UnsignedDependency" publicKeyToken="" culture="neutral" /><bindingRedirect oldVersion="0.0.0.0-2.1.0.0" newVersion="2.1.0.0" /></dependentAssembly>
    <dependentAssembly><assemblyIdentity name="SignedDependency" publicKeyToken="b77a5c561934e089" culture="neutral" /><bindingRedirect oldVersion="1.0.0.0" newVersion="2.0.0.0" /></dependentAssembly>
    <dependentAssembly><assemblyIdentity name="NoTokenDependency" culture="neutral" /><bindingRedirect oldVersion="1.0.0.0" newVersion="2.0.0.0" /></dependentAssembly>
  </assemblyBinding></runtime>
</configuration>
"@ | Set-Content $config
$hash=(Get-FileHash $config).Hash
& $original
if($LASTEXITCODE -ne 0){throw 'Original config runtime failed.'}
foreach($format in @('sdk','legacy')) {
  $export=Join-Path $OutputDirectory $format
  $argsList=@('--no-color','--threads','4','-o',$export)
  if($format -eq 'sdk'){$argsList+='--sdk-project'}
  & $DnSpyConsole @argsList $original
  if($LASTEXITCODE -ne 0){throw 'Config export failed.'}
  $project=Get-ChildItem $export -Recurse -Filter '*.csproj' | Select-Object -First 1
  $rebuilt=Join-Path $OutputDirectory ('rebuilt-'+$format)
  dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
  if($LASTEXITCODE -ne 0){throw 'Config source build failed.'}
  & (Join-Path $rebuilt 'ConfigTokenFixture.exe')
  if($LASTEXITCODE -ne 0){throw 'Rebuilt config runtime failed.'}
  $expected=[System.Xml.Linq.XDocument]::Load($config)
  $ns=[System.Xml.Linq.XNamespace]::Get('urn:schemas-microsoft-com:asm.v1')
  $identity=@($expected.Descendants($ns+'assemblyIdentity')) | Where-Object { $_.Attribute('name').Value -eq 'UnsignedDependency' }
  $identity.Attribute('publicKeyToken').Value='null'
  $actual=[System.Xml.Linq.XDocument]::Load((Join-Path $project.DirectoryName 'app.config'))
  if(![System.Xml.Linq.XNode]::DeepEquals($expected,$actual)){throw 'Export changed unrelated config content.'}
}
if((Get-FileHash $config).Hash -ne $hash){throw 'Original config changed.'}
'PASS: empty unsigned token normalizes without changing settings, signed identities or redirects.'
