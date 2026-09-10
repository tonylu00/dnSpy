param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference = 'Stop'
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $OutputDirectory) { throw 'Choose a new regression output folder.' }
$inputDirectory = Join-Path $OutputDirectory 'input'
$emitterDirectory = Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $inputDirectory,$emitterDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'GlobalMembersFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitGlobalMembers.cs') -Destination $emitterDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' |
    Set-Content (Join-Path $inputDirectory 'GlobalMembersFixture.csproj')
$dnlib = [Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" |
    Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
dotnet build (Join-Path $inputDirectory 'GlobalMembersFixture.csproj') -c Release --nologo -v quiet
if ($LASTEXITCODE -ne 0) { throw 'Global-member fixture build failed.' }
$original = Join-Path $OutputDirectory 'GlobalMembersFixture.exe'
dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- (Join-Path $inputDirectory 'bin\Release\net48\GlobalMembersFixture.exe') $original
if ($LASTEXITCODE -ne 0) { throw 'Global-member metadata emission failed.' }
& $original
if ($LASTEXITCODE -ne 0) { throw 'Original global-member behavior failed.' }
$hash = (Get-FileHash $original).Hash
foreach ($threads in @(1,4)) {
    $export = Join-Path $OutputDirectory "export-$threads"
    & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $original
    if ($LASTEXITCODE -ne 0) { throw 'Global-member export failed.' }
    $project = Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
    $rebuilt = Join-Path $OutputDirectory "rebuilt-$threads"
    dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
    if ($LASTEXITCODE -ne 0) { throw 'Global-member source compilation failed.' }
    & (Join-Path $rebuilt 'GlobalMembersFixture.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Rebuilt global-member behavior changed.' }
    Add-Type -Path (Join-Path (Split-Path $DnSpyConsole) 'dnlib.dll')
    $before = [dnlib.DotNet.ModuleDefMD]::Load($original)
    $after = [dnlib.DotNet.ModuleDefMD]::Load((Join-Path $rebuilt 'GlobalMembersFixture.exe'))
    try {
        $comparer = [dnlib.DotNet.SigComparer]::new([dnlib.DotNet.SigComparerOptions]0)
        if ($before.GlobalType.Methods.Count -ne $after.GlobalType.Methods.Count -or $before.GlobalType.Fields.Count -ne $after.GlobalType.Fields.Count) { throw 'Global member counts differ' }
        foreach ($method in $before.GlobalType.Methods) {
            $matches = @($after.GlobalType.Methods | Where-Object { $_.Name -eq $method.Name -and $comparer.Equals($_.MethodSig, $method.MethodSig) })
            if ($matches.Count -ne 1 -or $matches[0].Attributes -ne $method.Attributes) { throw 'Global method contract changed' }
        }
        foreach ($field in $before.GlobalType.Fields) {
            $matches = @($after.GlobalType.Fields | Where-Object { $_.Name -eq $field.Name -and $comparer.Equals($_.FieldSig, $field.FieldSig) })
            if ($matches.Count -ne 1 -or $matches[0].Attributes -ne $field.Attributes) { throw 'Global field contract changed' }
        }
        if (@($after.Types | Where-Object { $_.CustomAttributes | Where-Object { $_.TypeFullName -eq 'System.Reflection.ObfuscationAttribute' } }).Count) { throw 'Global projection markers survived' }
    } finally { $before.Dispose(); $after.Dispose() }
}
if ((Get-FileHash $original).Hash -ne $hash) { throw 'Original global module changed' }


