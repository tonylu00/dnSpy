param([Parameter(Mandatory)][string]$DnSpyConsole, [Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new test directory'}
$root=[IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory "$root\library","$root\app" | Out-Null
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><LangVersion>latest</LangVersion><AssemblyName>OverloadLibrary</AssemblyName></PropertyGroup></Project>' | Set-Content "$root\library\OverloadLibrary.csproj"
@'
public static class Api {
	public static string Describe(int value) => "int:" + value;
	public static string Describe(string value) => "str:" + value;
}
'@ | Set-Content "$root\library\Api.cs" -Encoding UTF8
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><LangVersion>latest</LangVersion><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost></PropertyGroup><ItemGroup><ProjectReference Include="..\library\OverloadLibrary.csproj" /></ItemGroup></Project>' | Set-Content "$root\app\App.csproj"
@'
class Program { static int Main() {
	if (Api.Describe(7) != "int:7" || Api.Describe("x") != "str:x") throw new System.Exception("original overloads broken");
	System.Console.WriteLine("PASS original overload contract"); return 0;
} }
'@ | Set-Content "$root\app\Program.cs" -Encoding UTF8
dotnet build "$root\app\App.csproj" -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'Baseline build failed'}
$inputRoot="$root\app\bin\Release\net8.0"
dotnet "$inputRoot\App.dll"
if($LASTEXITCODE){throw 'Baseline run failed'}

Add-Type -Path (Join-Path (Split-Path $DnSpyConsole) 'dnlib.dll')
$module=[dnlib.DotNet.ModuleDefMD]::Load("$inputRoot\OverloadLibrary.dll",[dnlib.DotNet.ModuleCreationOptions]::new())
try {
	$map=[xml]'<SourceNameMap Version="1"><Module /></SourceNameMap>'
	$map.DocumentElement.SetAttribute('InputDirectory',$inputRoot)
	$row=$map.DocumentElement.SelectSingleNode('Module')
	$row.SetAttribute('Path','OverloadLibrary.dll');$row.SetAttribute('Mvid',$module.Mvid.ToString())
	$row.SetAttribute('Sha256',(Get-FileHash "$inputRoot\OverloadLibrary.dll").Hash)
	$type=$module.GetTypes() | Where-Object FullName -eq Api
	foreach($method in ($type.Methods | Where-Object {$_.Name.String -eq 'Describe'})){
		$entry=$map.CreateElement('Method')
		$entry.SetAttribute('Token',('0x{0:X8}' -f $method.MDToken.Raw));$entry.SetAttribute('ExpectedName','Describe')
		$entry.SetAttribute('Signature',$method.FullName);$entry.SetAttribute('NewName','Render')
		$null=$row.AppendChild($entry)
	}
	if($row.SelectNodes('Method').Count -ne 2){throw 'Fixture must expose two overloads'}
	$map.Save("$root\names.xml")
} finally {$module.Dispose()}

& $DnSpyConsole --source-name-map "$root\names.xml" --no-color -o "$root\export" "$inputRoot\OverloadLibrary.dll" "$inputRoot\App.dll"
if($LASTEXITCODE){throw 'Scoped overload export failed'}
$source=(Get-ChildItem "$root\export" -Recurse -Filter '*.cs' | Get-Content -Raw) -join "`n"
if(([regex]::Matches($source,'Render\(')).Count -lt 2){throw 'Both overloads must appear under the shared alias'}
dotnet build "$root\export\solution.sln" -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'Exported overload solution failed to build'}
$runtime="$root\export\App\bin\Release\net8.0"
Copy-Item "$inputRoot\App.dll" "$runtime\App.dll" -Force
dotnet "$runtime\App.dll"
if($LASTEXITCODE){throw 'Original caller broke after the overload alias export'}
$rebuilt=[dnlib.DotNet.ModuleDefMD]::Load("$runtime\OverloadLibrary.dll",[dnlib.DotNet.ModuleCreationOptions]::new())
try {
	$methods=@($rebuilt.GetTypes() | Where-Object FullName -eq Api | ForEach-Object { $_.Methods } | Where-Object {$_.Name.String -eq 'Describe'})
	if($methods.Count -ne 2){throw 'Both original overload names must be restored'}
	$signatures=($methods | ForEach-Object { $_.FullName }) -join ';'
	if($signatures -notmatch 'System.String' -or $signatures -notmatch 'System.Int32'){throw 'Restored overload signatures changed: ' + $signatures}
} finally {$rebuilt.Dispose()}
'PASS overload aliases share one readable name and both original names and signatures are restored'
