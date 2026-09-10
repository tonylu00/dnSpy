param([Parameter(Mandatory)][string]$DnSpyConsole,[Parameter(Mandatory)][string]$SigningKey,[Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new test directory'}
$root=[IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory $root | Out-Null
& "$PSScriptRoot\Invoke-PublicSignRegression.ps1" -DnSpyConsole $DnSpyConsole -SigningKey $SigningKey -OutputDirectory "$root\baseline"
$inputRoot="$root\baseline\friend\bin\Release\net48"
Add-Type -Path (Join-Path (Split-Path $DnSpyConsole) 'dnlib.dll')
$module=[dnlib.DotNet.ModuleDefMD]::Load("$inputRoot\SignedLibrary.dll",[dnlib.DotNet.ModuleCreationOptions]::new())
try {
 $map=[xml]'<SourceNameMap Version="1"><Module /></SourceNameMap>'
 $map.DocumentElement.SetAttribute('InputDirectory',$inputRoot)
 $row=$map.DocumentElement.SelectSingleNode('Module')
 $row.SetAttribute('Path','SignedLibrary.dll');$row.SetAttribute('Mvid',$module.Mvid.ToString())
 $row.SetAttribute('Sha256',(Get-FileHash "$inputRoot\SignedLibrary.dll").Hash)
 $type=$module.GetTypes() | Where-Object FullName -eq Api
 foreach($item in @(@($type,'ReadableLibrary'),@(($type.Methods | Where-Object {$_.Name.String -eq 'Read'}),'ReadCountAndLabel'),@(($type.Methods | Where-Object {$_.Name.String -eq 'Hidden'}),'ReadInternalCode'))){
  $member=$item[0];$kind=if($member -is [dnlib.DotNet.TypeDef]){'Type'}else{'Method'}
  $entry=$map.CreateElement($kind)
  $entry.SetAttribute('Token',('0x{0:X8}' -f $member.MDToken.Raw));$entry.SetAttribute('ExpectedName',$member.Name.String)
  $entry.SetAttribute('Signature',$member.FullName);$entry.SetAttribute('NewName',$item[1]);$null=$row.AppendChild($entry)
 }
 $map.Save("$root\names.xml")
} finally {$module.Dispose()}
& $DnSpyConsole --public-sign --source-name-map "$root\names.xml" --no-color -o "$root\export" "$inputRoot\SignedLibrary.dll" "$inputRoot\Friend.exe"
if($LASTEXITCODE){throw 'Source alias export failed'}
[xml]$snapshot=Get-Content "$root\export\dnspy-source-name-map.xml"
if($snapshot.DocumentElement.OuterXml -ne $map.DocumentElement.OuterXml){throw 'Source map snapshot differs'}
$source=(Get-ChildItem "$root\export\SignedLibrary" -Recurse -Filter '*.cs' | Get-Content) -join "`n"
if($source -notmatch 'class ReadableLibrary' -or $source -notmatch 'ReadCountAndLabel'){throw 'Readable source aliases absent'}
dotnet build "$root\export\solution.sln" -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'Source alias build failed'}
$runtime="$root\export\Friend\bin\Release\net48"
& "$runtime\Friend.exe"
if($LASTEXITCODE){throw 'Rebuilt alias caller failed'}
Copy-Item "$inputRoot\Friend.exe" "$runtime\Friend.exe" -Force
& "$runtime\Friend.exe"
if($LASTEXITCODE){throw 'Original SDK caller broke after source aliases'}
$rebuilt=[dnlib.DotNet.ModuleDefMD]::Load("$runtime\SignedLibrary.dll",[dnlib.DotNet.ModuleCreationOptions]::new())
try {
 $type=$rebuilt.GetTypes() | Where-Object FullName -eq Api
 if(!$type -or !($type.Methods | Where-Object {$_.Name.String -eq 'Read'}) -or ($rebuilt.GetTypes() | Where-Object FullName -eq ReadableLibrary)){throw 'Original runtime names were not restored'}
} finally {$rebuilt.Dispose()}
foreach($case in 'stale-mvid','stale-hash','stale-signature','collision','original-name-collision','invisible-format'){
 [xml]$bad=Get-Content "$root\names.xml"
 if($case -eq 'stale-mvid'){$bad.SourceNameMap.Module.SetAttribute('Mvid',[guid]::NewGuid().ToString())}
 elseif($case -eq 'stale-hash'){$bad.SourceNameMap.Module.SetAttribute('Sha256','00')}
 elseif($case -eq 'stale-signature'){$bad.SourceNameMap.Module.Method[0].SetAttribute('Signature','wrong signature')}
 elseif($case -eq 'original-name-collision'){$bad.SourceNameMap.Module.Method[0].SetAttribute('NewName','Hidden')}
 elseif($case -eq 'invisible-format'){$bad.SourceNameMap.Module.Method[0].SetAttribute('NewName',('Read'+[char]0x200B+'Count'))}
 else {$bad.SourceNameMap.Module.Method[0].SetAttribute('NewName','ReadableLibrary')}
 $bad.Save("$root\$case.xml")
 & $DnSpyConsole --public-sign --source-name-map "$root\$case.xml" --no-color -o "$root\$case" "$inputRoot\SignedLibrary.dll" "$inputRoot\Friend.exe"
 if(!$LASTEXITCODE){throw "Invalid map accepted: $case"}
}
'PASS descriptive source aliases, original signed SDK caller, runtime names and invalid-map guards'
