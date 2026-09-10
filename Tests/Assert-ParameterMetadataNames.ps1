param([Parameter(Mandatory)][string]$DnlibPath,[Parameter(Mandatory)][string]$Original,[Parameter(Mandatory)][string]$Rebuilt)
$ErrorActionPreference='Stop'
Add-Type -Path $DnlibPath
$options=[dnlib.DotNet.ModuleCreationOptions]::new()
$before=[dnlib.DotNet.ModuleDefMD]::Load($Original,$options)
$after=[dnlib.DotNet.ModuleDefMD]::Load($Rebuilt,$options)
try {
 $comparer=[dnlib.DotNet.SigComparer]::new([dnlib.DotNet.SigComparerOptions]::DontCompareTypeScope)
 $count=0
 function Compare-Generics($left,$right) {
  if($left.Count -ne $right.Count){throw 'Generic parameter count differs'}
  for($i=0;$i -lt $left.Count;$i++) {
   if([Convert]::ToBase64String($left[$i].Name.Data) -cne [Convert]::ToBase64String($right[$i].Name.Data)){throw "Generic name differs at position $i"}
  }
 }
 foreach($type in $before.GetTypes() | Where-Object {!$_.IsGlobalModuleType}) {
  $matches=@($after.GetTypes() | Where-Object {$_.FullName -ceq $type.FullName})
  if($matches.Count -ne 1){throw "Missing/ambiguous type $($type.FullName)"}
  $actual=$matches[0]
  Compare-Generics $type.GenericParameters $actual.GenericParameters
  foreach($method in $type.Methods) {
   $methods=@($actual.Methods | Where-Object {$_.Name.String -ceq $method.Name.String -and $comparer.Equals($_.MethodSig,$method.MethodSig)})
   if($methods.Count -ne 1){throw "Missing/ambiguous method $($method.FullName)"}
   $rebuiltMethod=$methods[0]
   Compare-Generics $method.GenericParameters $rebuiltMethod.GenericParameters
   foreach($parameter in $method.ParamDefs) {
    $rows=@($rebuiltMethod.ParamDefs | Where-Object Sequence -eq $parameter.Sequence)
    if($rows.Count -eq 0 -and [string]::IsNullOrEmpty($parameter.Name.String)){continue}
    if($rows.Count -ne 1 -or [Convert]::ToBase64String($parameter.Name.Data) -cne [Convert]::ToBase64String($rows[0].Name.Data)){throw "Parameter name differs: $($method.FullName) sequence $($parameter.Sequence)"}
    $count++
   }
  }
 }
 "PASS original generic and parameter metadata names: $count parameter rows"
} finally {$before.Dispose();$after.Dispose()}
