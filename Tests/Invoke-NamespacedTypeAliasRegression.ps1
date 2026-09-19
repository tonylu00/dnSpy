param([Parameter(Mandatory)][string]$DnSpyConsole,[Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new test directory'}
$root=[IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory $root | Out-Null

# A type the obfuscator flattened into the global namespace.
New-Item -ItemType Directory "$root\fixture" | Out-Null
Set-Content -Encoding UTF8 "$root\fixture\fixture.csproj" @'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net48</TargetFramework>
    <OutputType>Exe</OutputType>
    <AssemblyName>Fixture</AssemblyName>
    <RootNamespace></RootNamespace>
    <Nullable>disable</Nullable>
    <LangVersion>latest</LangVersion>
  </PropertyGroup>
</Project>
'@
Set-Content -Encoding UTF8 "$root\fixture\Program.cs" @'
internal static class ClassA
{
	public static string Hello() => "hello";
	public static int Value() => 42;
}

internal static class ClassB
{
	public static int Other() => 1;
}

internal static class Program
{
	private static int Main()
	{
		if (ClassA.Value() != 42) return 1;
		if (ClassA.Hello() != "hello") return 2;
		if (ClassB.Other() != 1) return 3;
		return ClassA.Hello().Length;
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
 $type=$module.GetTypes() | Where-Object FullName -eq ClassA
 $entry=$map.CreateElement('Type')
 $entry.SetAttribute('Token',('0x{0:X8}' -f $type.MDToken.Raw));$entry.SetAttribute('ExpectedName','ClassA')
 $entry.SetAttribute('Signature',$type.FullName);$entry.SetAttribute('NewName','Example.Sample.RenamedHelper')
 $null=$row.AppendChild($entry)
 $map.Save("$root\names.xml")
} finally {$module.Dispose()}

& $DnSpyConsole --source-name-map "$root\names.xml" --no-color -o "$root\export" "$inputRoot\Fixture.exe"
if($LASTEXITCODE){throw 'Namespaced type alias export failed'}
$source=(Get-ChildItem "$root\export\Fixture" -Recurse -Filter '*.cs' | Get-Content) -join "`n"
if($source -notmatch 'namespace Example\.Sample' -or $source -notmatch 'class RenamedHelper'){throw 'Namespaced type alias is absent from the exported source'}
if($source -notmatch 'RenamedHelper\.Value\(\)'){throw 'References were not rewritten to the aliased type'}
dotnet build "$root\export\solution.sln" -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'Namespaced type alias export build failed'}
$runtime="$root\export\Fixture\bin\Release\net48"
& "$runtime\Fixture.exe"
if($LASTEXITCODE -ne 5){throw "Rebuilt namespaced-alias fixture returned $LASTEXITCODE, expected 5"}
$rebuilt=[dnlib.DotNet.ModuleDefMD]::Load("$runtime\Fixture.exe",[dnlib.DotNet.ModuleCreationOptions]::new())
try {
 $restored=$rebuilt.GetTypes() | Where-Object {$_.Name -eq 'ClassA'}
 if(!$restored){throw 'Original runtime type name was not restored'}
 if($restored.Namespace -ne ''){throw "Original global namespace was not restored: $($restored.Namespace)"}
 if($rebuilt.GetTypes() | Where-Object {$_.Name -eq 'RenamedHelper'}){throw 'Aliased type name leaked into the runtime assembly'}
} finally {$rebuilt.Dispose()}
[xml]$bad=Get-Content "$root\names.xml"
$bad.SourceNameMap.Module.Type.SetAttribute('NewName','Example..Broken')
$bad.Save("$root\bad-syntax.xml")
& $DnSpyConsole --source-name-map "$root\bad-syntax.xml" --no-color -o "$root\bad-syntax" "$inputRoot\Fixture.exe" 2>$null
if($LASTEXITCODE -eq 0){throw 'A malformed dotted alias was accepted'}
[xml]$dup=Get-Content "$root\names.xml"
$module2=[dnlib.DotNet.ModuleDefMD]::Load("$inputRoot\Fixture.exe",[dnlib.DotNet.ModuleCreationOptions]::new())
try {
 $other=$module2.GetTypes() | Where-Object FullName -eq ClassB
 $entry2=$dup.CreateElement('Type')
 $entry2.SetAttribute('Token',('0x{0:X8}' -f $other.MDToken.Raw));$entry2.SetAttribute('ExpectedName','ClassB')
 $entry2.SetAttribute('Signature',$other.FullName);$entry2.SetAttribute('NewName','Example.Sample.RenamedHelper')
 $null=$dup.SourceNameMap.Module.AppendChild($entry2)
} finally {$module2.Dispose()}
$dup.Save("$root\bad-duplicate.xml")
& $DnSpyConsole --source-name-map "$root\bad-duplicate.xml" --no-color -o "$root\bad-duplicate" "$inputRoot\Fixture.exe" 2>$null
if($LASTEXITCODE -eq 0){throw 'A duplicate dotted type alias was accepted'}
Remove-Item "$root\bad-syntax.xml","$root\bad-duplicate.xml" -Force
Remove-Item "$root\bad-syntax","$root\bad-duplicate" -Recurse -Force -ErrorAction SilentlyContinue
Write-Host 'Namespaced type alias regression passed'
