param([Parameter(Mandatory)][string]$DnSpyConsole,
      [Parameter(Mandatory)][string]$ReactorTestDirectory,
      [Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $root){throw 'Choose a new output directory'}
New-Item -ItemType Directory $root | Out-Null
foreach($scenario in 'method-only','method-and-control-flow') {
 $inputRoot="$ReactorTestDirectory\$scenario\output"
 $work=Join-Path $root $scenario
 New-Item -ItemType Directory $work | Out-Null
 $inputs=@(Get-ChildItem $inputRoot -Recurse -File | Where-Object {$_.Extension -in '.exe','.dll'} | ForEach-Object {try {$null=[Reflection.AssemblyName]::GetAssemblyName($_.FullName); $_.FullName} catch [BadImageFormatException] {}})
 & $DnSpyConsole --no-color --sdk-project --threads 4 --asm-path $inputRoot -o "$work\source" @inputs > "$work\export.log" 2>&1
 if($LASTEXITCODE){throw "Export failed: $scenario"}
 dotnet build "$work\source\solution.sln" -c Release --nologo -v quiet > "$work\build.log" 2>&1
 if($LASTEXITCODE){throw "Build failed: $scenario"}
 [xml]$map=Get-Content "$work\source\dnspy-export-map.xml" -Raw
 $count=0
 foreach($project in $map.DnSpyExportMap.Project | Where-Object AssemblyName -eq App){
  $dir=Split-Path (Join-Path "$work\source" $project.Project)
  $exe=@(Get-ChildItem "$dir\bin\Release" -Recurse -Filter App.exe | Where-Object FullName -NotMatch '\\ref\\')[0].FullName
  & $exe
  $expected=if($project.Source -match '\\compat\\'){120}else{100}
  if($LASTEXITCODE -ne $expected){throw "Runtime mismatch $scenario $($project.Source): $LASTEXITCODE expected $expected"}
  $count++
 }
 if($count -ne 2){throw 'Both application contexts must execute'}
 "PASS $scenario full source recompilation and both compatibility executions"
}



