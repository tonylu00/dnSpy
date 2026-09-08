param([Parameter(Mandatory)][string]$DnSpyConsole,[Parameter(Mandatory)][string]$OutputDirectory,[ValidateSet('AnyCPU','x86')][string]$Platform='AnyCPU')
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new output directory.'}
foreach($dir in 'fixture','emitter','input'){New-Item -ItemType Directory -Path (Join-Path $OutputDirectory $dir) | Out-Null}
'<Project />' | Set-Content (Join-Path $OutputDirectory 'Directory.Build.props')
Copy-Item (Join-Path $PSScriptRoot 'NativeArithmeticFixture.cs') (Join-Path $OutputDirectory 'fixture')
Copy-Item (Join-Path $PSScriptRoot 'EmitNativeArithmetic.cs') (Join-Path $OutputDirectory 'emitter')
('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><PlatformTarget>{0}</PlatformTarget></PropertyGroup></Project>' -f $Platform) | Set-Content (Join-Path $OutputDirectory 'fixture\NativeArithmeticFixture.csproj')
$dnlib=[Security.SecurityElement]::Escape((Join-Path (Split-Path $DnSpyConsole) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $OutputDirectory 'emitter\Emitter.csproj')
dotnet build (Join-Path $OutputDirectory 'fixture\NativeArithmeticFixture.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Fixture build failed.'}
$inputFile=Join-Path $OutputDirectory 'input\NativeArithmeticFixture.exe'
dotnet run --project (Join-Path $OutputDirectory 'emitter\Emitter.csproj') -c Release -- (Join-Path $OutputDirectory 'fixture\bin\Release\net48\NativeArithmeticFixture.exe') $inputFile
if($LASTEXITCODE -ne 0){throw 'Metadata emission failed.'}
$hash=(Get-FileHash $inputFile).Hash
$original=@(& $inputFile)
if($LASTEXITCODE -ne 0){throw 'Original runtime failed.'}
$original | Write-Output
foreach($threads in 1,4){
 $export=Join-Path $OutputDirectory "export-$threads"
 & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $inputFile
 if($LASTEXITCODE -ne 0){throw 'Export failed.'}
 $project=Get-ChildItem $export -Recurse -Filter NativeArithmeticFixture.csproj | Select-Object -First 1
 $rebuilt=Join-Path $OutputDirectory "rebuilt-$threads"
 dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
 if($LASTEXITCODE -ne 0){throw 'Source build failed.'}
 $actual=@(& (Join-Path $rebuilt 'NativeArithmeticFixture.exe'))
 if($LASTEXITCODE -ne 0){throw 'Rebuilt runtime failed.'}
 if(Compare-Object $original $actual){throw 'Native execution width changed.'}
 $actual | Write-Output
}
if((Get-FileHash $inputFile).Hash -ne $hash){throw 'Input changed.'}
$one=Join-Path $OutputDirectory 'export-1'
$four=Join-Path $OutputDirectory 'export-4'
foreach($file in Get-ChildItem $one -Recurse -Filter '*.cs') {
 $relative=$file.FullName.Substring($one.Length).TrimStart('\')
 if((Get-FileHash $file.FullName).Hash -ne (Get-FileHash (Join-Path $four $relative)).Hash){throw 'Worker count changed source.'}
}
Write-Host 'PASS: native arithmetic regression'


