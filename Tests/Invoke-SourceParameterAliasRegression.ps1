param([Parameter(Mandatory)][string]$DnSpyConsole,[Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new output directory'}
$root=[IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory "$root/library","$root/caller" | Out-Null
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework></PropertyGroup></Project>' | Set-Content "$root/library/Library.csproj"
@'
public static class Api {
 public static int Add(int a,int b) { return a*10+b; }
 public static T Echo<T>(T a) { return a; }
}
'@ | Set-Content "$root/library/Api.cs"
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><ProjectReference Include="../library/Library.csproj"/></ItemGroup></Project>' | Set-Content "$root/caller/Caller.csproj"
@'
class Program { static int Main() {
 if(Api.Add(b:2,a:4)!=42 || Api.Echo(7)!=7) throw new System.Exception("Dispatch mismatch");
 var p=typeof(Api).GetMethod("Add").GetParameters();
 if(p[0].Name!="a" || p[1].Name!="b" || typeof(Api).GetMethod("Echo").GetParameters()[0].Name!="a") throw new System.Exception("Reflection names changed");
 System.Console.WriteLine("PASS behavior and original parameter names"); return 0;
} }
'@ | Set-Content "$root/caller/Program.cs"
dotnet build "$root/caller/Caller.csproj" -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'Fixture build failed'}
$inputRoot="$root/caller/bin/Release/net48"
& "$inputRoot/Caller.exe"
if($LASTEXITCODE){throw 'Original fixture failed'}
$hash=(Get-FileHash "$inputRoot/Library.dll").Hash
Add-Type -Path (Join-Path (Split-Path $DnSpyConsole) 'dnlib.dll')
$module=[dnlib.DotNet.ModuleDefMD]::Load("$inputRoot/Library.dll",[dnlib.DotNet.ModuleCreationOptions]::new())
try {
 [xml]$map='<SourceNameMap Version="1"><Module/></SourceNameMap>'
 $map.DocumentElement.SetAttribute('InputDirectory',$inputRoot)
 $row=$map.DocumentElement.SelectSingleNode('Module')
 $row.SetAttribute('Path','Library.dll');$row.SetAttribute('Mvid',$module.Mvid.ToString());$row.SetAttribute('Sha256',$hash)
 foreach($method in ($module.GetTypes() | Where-Object FullName -eq Api).Methods){
  $entry=$map.CreateElement('Method');$entry.SetAttribute('Token',('0x{0:X8}' -f $method.MDToken.Raw));$entry.SetAttribute('ExpectedName',$method.Name.String);$entry.SetAttribute('Signature',$method.FullName)
  if($method.Name.String -eq 'Add'){$entry.SetAttribute('NewName','CombineDigits')}
  foreach($parameter in $method.ParamDefs){
   $p=$map.CreateElement('Parameter');$p.SetAttribute('Sequence',$parameter.Sequence.ToString());$p.SetAttribute('ExpectedName',$parameter.Name.String)
   $alias=if($method.Name.String -eq 'Echo'){'payload'}elseif($parameter.Sequence -eq 1){'tens'}else{'units'}
   $p.SetAttribute('NewName',$alias);$null=$entry.AppendChild($p)
  }
  $null=$row.AppendChild($entry)
 }
 $map.Save("$root/names.xml")
} finally {$module.Dispose()}
foreach($workers in 1,4){
 & $DnSpyConsole --threads $workers --source-name-map "$root/names.xml" --no-color -o "$root/export$workers" "$inputRoot/Library.dll" "$inputRoot/Caller.exe"
 if($LASTEXITCODE){throw 'Parameter alias export failed'}
 $source=(Get-ChildItem "$root/export$workers/Library" -Recurse -Filter '*.cs' | Get-Content) -join "`n"
 if($source -notmatch 'CombineDigits\(int tens, int units\)' -or $source -notmatch 'Echo<T>\(T payload\)'){throw 'Readable parameter aliases absent'}
 dotnet build "$root/export$workers/solution.sln" -c Release --nologo -v quiet
 if($LASTEXITCODE){throw 'Alias compilation failed'}
 $runtime="$root/export$workers/Caller/bin/Release/net48"
 & "$runtime/Caller.exe"
 if($LASTEXITCODE){throw 'Rebuilt caller failed'}
 Copy-Item "$inputRoot/Caller.exe" "$runtime/Caller.exe" -Force
 & "$runtime/Caller.exe"
 if($LASTEXITCODE){throw 'Unchanged caller failed'}
}
foreach($case in 'sequence','expected-name','duplicate','collision','generic-collision'){
 [xml]$bad=$map.OuterXml
 $p=$bad.SourceNameMap.Module.Method[0].Parameter[0]
 switch($case){
  'sequence' {$p.SetAttribute('Sequence','0')}
  'expected-name' {$p.SetAttribute('ExpectedName','stale')}
  'duplicate' {$null=$p.ParentNode.AppendChild($p.CloneNode($true))}
  'collision' {$p.SetAttribute('NewName','b')}
  'generic-collision' {$bad.SourceNameMap.Module.Method[1].Parameter.SetAttribute('NewName','T')}
 }
 $bad.Save("$root/$case.xml")
 & $DnSpyConsole --source-name-map "$root/$case.xml" --no-color -o "$root/$case" "$inputRoot/Library.dll" "$inputRoot/Caller.exe"
 if(!$LASTEXITCODE){throw "Invalid parameter map accepted: $case"}
}
if((Get-FileHash "$inputRoot/Library.dll").Hash -ne $hash){throw 'Input changed'}
'PASS source aliases, generic method, one/four workers, unchanged caller, original reflection names and invalid-map guards'
