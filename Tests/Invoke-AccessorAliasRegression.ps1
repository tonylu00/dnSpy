param([Parameter(Mandatory)][string]$DnSpyConsole,[Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new test directory'}
$root=[IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory $root | Out-Null

# An obfuscated accessor: the property row keeps its readable name, the accessor
# method is a placeholder. The map carries the derived conventional name and the
# export restores the property.
New-Item -ItemType Directory "$root\fixture" | Out-Null
Set-Content -Encoding UTF8 "$root\fixture\fixture.csproj" @'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net48</TargetFramework>
    <OutputType>Exe</OutputType>
    <AssemblyName>Fixture</AssemblyName>
    <Nullable>disable</Nullable>
    <LangVersion>latest</LangVersion>
  </PropertyGroup>
</Project>
'@
Set-Content -Encoding UTF8 "$root\fixture\Program.cs" @'
public class Model
{
	private string value = "knx";
	public string Name { get { return value; } set { this.value = value; } }
}

internal static class Program
{
	private static int Main()
	{
		var model = new Model { Name = "ets" };
		return model.Name == "ets" ? 3 : 1;
	}
}
'@
dotnet build "$root\fixture\fixture.csproj" -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'Fixture build failed'}
$inputRoot="$root\fixture\bin\Release\net48"

Add-Type -Path (Join-Path (Split-Path $DnSpyConsole) 'dnlib.dll')
$module=[dnlib.DotNet.ModuleDefMD]::Load("$inputRoot\Fixture.exe",[dnlib.DotNet.ModuleCreationOptions]::new())
try {
 $model=$module.GetTypes() | Where-Object Name -eq 'Model'
 $property=$model.Properties | Where-Object Name -eq 'Name'
 $getter=$property.GetMethod;$setter=$property.SetMethod
 # Emulate the obfuscator: keep the property rows, rename the accessor methods.
 $getter.Name='a';$setter.Name='b'
 $module.Write("$inputRoot\Obfuscated.exe")
} finally {$module.Dispose()}
Remove-Item "$inputRoot\Fixture.exe"
$module=[dnlib.DotNet.ModuleDefMD]::Load("$inputRoot\Obfuscated.exe",[dnlib.DotNet.ModuleCreationOptions]::new())
try {
 $model=$module.GetTypes() | Where-Object Name -eq 'Model'
 $property=$model.Properties | Where-Object Name -eq 'Name'
 $map=[xml]'<SourceNameMap Version="1"><Module /></SourceNameMap>'
 $map.DocumentElement.SetAttribute('InputDirectory',$inputRoot)
 $row=$map.DocumentElement.SelectSingleNode('Module')
 $row.SetAttribute('Path','Obfuscated.exe');$row.SetAttribute('Mvid',$module.Mvid.ToString())
 $row.SetAttribute('Sha256',(Get-FileHash "$inputRoot\Obfuscated.exe").Hash)
 foreach($accessor in @($property.GetMethod,$property.SetMethod)){
   $entry=$map.CreateElement('Method')
   $entry.SetAttribute('Token',('0x{0:X8}' -f $accessor.MDToken.Raw));$entry.SetAttribute('ExpectedName',$accessor.Name)
   $entry.SetAttribute('Signature',$accessor.FullName)
   $entry.SetAttribute('NewName',($(if($accessor -eq $property.GetMethod){'get_Name'}else{'set_Name'})))
   $null=$row.AppendChild($entry)
 }
 $map.Save("$root\names.xml")
 # A free-form accessor name must not load.
 $bad=[xml]$map.OuterXml
 $bad.DocumentElement.SelectSingleNode('Module').SelectSingleNode('Method').SetAttribute('NewName','GetName')
 $bad.Save("$root\bad.xml")
} finally {$module.Dispose()}

$rejected=$false
& $DnSpyConsole --source-name-map "$root\bad.xml" --no-color -o "$root\export-bad" "$inputRoot\Obfuscated.exe" 2>$null
if($LASTEXITCODE -ne 0){$rejected=$true}
if(-not $rejected){throw 'A free-form accessor alias was accepted'}

& $DnSpyConsole --source-name-map "$root\names.xml" --no-color -o "$root\export" "$inputRoot\Obfuscated.exe"
if($LASTEXITCODE){throw 'Accessor alias export failed'}
$source=(Get-ChildItem "$root\export\Fixture" -Recurse -Filter '*.cs' | Get-Content) -join "`n"
if($source -notmatch 'string Name'){throw 'The property was not restored in the exported source'}
if($source -notmatch 'get_Name' -and $source -notmatch 'set_Name' -and $source -notmatch 'get\s*\{'){throw 'The accessor alias is absent from the exported source'}
dotnet build "$root\export\solution.sln" -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'Accessor alias export build failed'}
$runtime="$root\export\Fixture\bin\Release\net48"
& "$runtime\Fixture.exe"
if($LASTEXITCODE -ne 3){throw "Rebuilt accessor fixture returned $LASTEXITCODE, expected 3"}
$rebuilt=[dnlib.DotNet.ModuleDefMD]::Load("$runtime\Fixture.exe",[dnlib.DotNet.ModuleCreationOptions]::new())
try {
 $model=$rebuilt.GetTypes() | Where-Object Name -eq 'Model'
 $property=$model.Properties | Where-Object Name -eq 'Name'
 # The SDK export restores the original runtime names; the alias is a source
 # spelling only, so the rebuilt accessors are the original accessor names.
 if($property.GetMethod.Name -ne 'a' -or $property.SetMethod.Name -ne 'b'){throw "The rebuilt accessors did not restore the runtime names: $($property.GetMethod.Name)/$($property.SetMethod.Name)"}
} finally {$rebuilt.Dispose()}
Write-Output 'Accessor alias regression passed'
