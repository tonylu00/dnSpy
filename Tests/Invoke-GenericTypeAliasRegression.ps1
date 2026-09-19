param([Parameter(Mandatory)][string]$DnSpyConsole,[Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new test directory'}
$root=[IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory $root | Out-Null

# A generic type the obfuscator left in the global namespace, plus a caller.
New-Item -ItemType Directory "$root\fixture" | Out-Null
Set-Content -Encoding UTF8 "$root\fixture\fixture.csproj" @'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net48</TargetFramework>
    <OutputType>Exe</OutputType>
    <AssemblyName>Fixture</AssemblyName>
    <RootNamespace></RootNamespace>
    <Nullable>disable</Nullable>
  </PropertyGroup>
</Project>
'@
Set-Content -Encoding UTF8 "$root\fixture\Program.cs" @'
internal sealed class ClassG<T>
{
	public T Value;
	public static string Tag() => "generic";
}

internal sealed class ClassH
{
	public static int Other() => 1;
}

internal static class Program
{
	private static int Main()
	{
		var box = new ClassG<int>();
		box.Value = 42;
		if (box.Value != 42) return 1;
		if (ClassG<string>.Tag() != "generic") return 2;
		if (ClassH.Other() != 1) return 3;
		return 7;
	}
}
'@
dotnet build "$root\fixture\fixture.csproj" -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'Fixture build failed'}
$inputRoot="$root\fixture\bin\Release\net48"

Add-Type -Path (Join-Path (Split-Path $DnSpyConsole) 'dnlib.dll')
$module=[dnlib.DotNet.ModuleDefMD]::Load("$inputRoot\Fixture.exe",[dnlib.DotNet.ModuleCreationOptions]::new())
try {
 $map=[xml]'<SourceNameMap Version="1"><Module /></SourceNameMap>'
 $map.DocumentElement.SetAttribute('InputDirectory',$inputRoot)
 $row=$map.DocumentElement.SelectSingleNode('Module')
 $row.SetAttribute('Path','Fixture.exe');$row.SetAttribute('Mvid',$module.Mvid.ToString())
 $row.SetAttribute('Sha256',(Get-FileHash "$inputRoot\Fixture.exe").Hash)
 $type=$module.GetTypes() | Where-Object { $_.Name -eq 'ClassG`1' }
 if(!$type){throw 'Fixture generic type not found'}
 $entry=$map.CreateElement('Type')
 $entry.SetAttribute('Token',('0x{0:X8}' -f $type.MDToken.Raw));$entry.SetAttribute('ExpectedName','ClassG`1')
 $entry.SetAttribute('Signature',$type.FullName)
 # Renamers paste the metadata name they see in dnSpy, arity suffix included.
 $entry.SetAttribute('NewName','Example.Generic.RenamedCache`1')
 $null=$row.AppendChild($entry)
 $map.Save("$root\names.xml")
} finally {$module.Dispose()}

& $DnSpyConsole --source-name-map "$root\names.xml" --no-color -o "$root\export" "$inputRoot\Fixture.exe"
if($LASTEXITCODE){throw 'Generic type alias export failed'}
$source=(Get-ChildItem "$root\export\Fixture" -Recurse -Filter '*.cs' | Get-Content) -join "`n"
if($source -notmatch 'namespace Example\.Generic'){throw 'Generic type alias namespace is absent from the exported source'}
if($source -notmatch 'class RenamedCache<T>'){throw 'Generic type alias leaf/arity is wrong in the exported source'}
if($source -notmatch 'RenamedCache<int>'){throw 'Generic type references were not rewritten to the aliased type'}
if($source -match 'ClassG'){throw 'The original generic type name leaked into the exported source'}
dotnet build "$root\export\solution.sln" -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'Generic type alias export build failed'}
$runtime="$root\export\Fixture\bin\Release\net48"
& "$runtime\Fixture.exe"
if($LASTEXITCODE -ne 7){throw "Rebuilt generic-alias fixture returned $LASTEXITCODE, expected 7"}
$rebuilt=[dnlib.DotNet.ModuleDefMD]::Load("$runtime\Fixture.exe",[dnlib.DotNet.ModuleCreationOptions]::new())
try {
 $restored=$rebuilt.GetTypes() | Where-Object { $_.Name -eq 'ClassG`1' }
 if(!$restored){throw 'Original generic type name/arity was not restored'}
 if($restored.Namespace -ne ''){throw "Original global namespace was not restored: $($restored.Namespace)"}
 if((($restored.GenericParameters | Measure-Object).Count) -ne 1){throw 'Generic parameters were not preserved'}
 if($rebuilt.GetTypes() | Where-Object { $_.Name -like 'RenamedCache*' }){throw 'Aliased generic type name leaked into the runtime assembly'}
} finally {$rebuilt.Dispose()}

# A pasted arity that does not match the type must be rejected, not silently accepted.
[xml]$bad=Get-Content "$root\names.xml"
$bad.SourceNameMap.Module.Type.SetAttribute('NewName','Example.Generic.RenamedCache`2')
$bad.Save("$root\bad-arity.xml")
& $DnSpyConsole --source-name-map "$root\bad-arity.xml" --no-color -o "$root\bad-arity" "$inputRoot\Fixture.exe" 2>$null
if($LASTEXITCODE -eq 0){throw 'A mismatched generic arity was accepted'}
Remove-Item "$root\bad-arity.xml" -Force
Remove-Item "$root\bad-arity" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host 'Generic type alias regression passed'
