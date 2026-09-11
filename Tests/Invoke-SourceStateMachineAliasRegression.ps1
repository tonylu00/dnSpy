param([Parameter(Mandatory)][string]$DnSpyConsole,
      [Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression directory.'}
$root=[IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path "$root/input" | Out-Null
'<Project />' | Set-Content "$root/Directory.Build.props"
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize></PropertyGroup></Project>' | Set-Content "$root/input/Fixture.csproj"
Copy-Item -LiteralPath "$PSScriptRoot/SourceStateMachineAliasFixture.cs" -Destination "$root/input/Program.cs"
dotnet build "$root/input/Fixture.csproj" -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'Original fixture build failed.'}
$original="$root/input/bin/Release/net48/Fixture.exe"
& $original
if($LASTEXITCODE){throw 'Original fixture behavior failed.'}
$hash=(Get-FileHash -LiteralPath $original).Hash
Add-Type -LiteralPath (Join-Path (Split-Path $DnSpyConsole) 'dnlib.dll')
$module=[dnlib.DotNet.ModuleDefMD]::Load($original)
try {
    [xml]$map='<SourceNameMap Version="1"><Module /></SourceNameMap>'
    $map.DocumentElement.SetAttribute('InputDirectory',(Split-Path $original))
    $row=$map.DocumentElement.SelectSingleNode('Module')
    $row.SetAttribute('Path','Fixture.exe');$row.SetAttribute('Mvid',$module.Mvid.ToString());$row.SetAttribute('Sha256',$hash)
    $owner=$module.GetTypes() | Where-Object FullName -EQ 'Container`1'
    foreach($pair in @(@('a','ComputeValueAsync'),@('b','EnumerateValues'),@('c','EchoValueAsync'),@('d','RunCapturedAsync'),@('e','OnChanged'),@('f','OnPayloadChanged'),@('g','SumPositiveDoubles'),@('h','CreateOffsetCallback'))){
        $method=$owner.Methods | Where-Object {$_.Name.String -ceq $pair[0]}
        $entry=$map.CreateElement('Method')
        $entry.SetAttribute('Token',('0x{0:X8}' -f $method.MDToken.Raw));$entry.SetAttribute('ExpectedName',$method.Name.String)
        $entry.SetAttribute('Signature',$method.FullName);$entry.SetAttribute('NewName',$pair[1]);$null=$row.AppendChild($entry)
    }
    $map.Save("$root/names.xml")
} finally {$module.Dispose()}
foreach($workers in 1,4){
    & $DnSpyConsole --no-color --source-name-map "$root/names.xml" --threads $workers -o "$root/export$workers" $original
    if($LASTEXITCODE){throw 'Mapped fixture export failed.'}
    $source=Get-Content "$root/export$workers/Fixture/Container.cs" -Raw
    foreach($alias in 'ComputeValueAsync','EnumerateValues','EchoValueAsync','RunCapturedAsync','OnChanged','OnPayloadChanged','SumPositiveDoubles','CreateOffsetCallback'){
        if($source -notmatch ('\b'+$alias+'(?:<U>)?\(')){throw "Readable source alias missing: $alias"}
    }
    dotnet build "$root/export$workers/solution.sln" -c Release --nologo -v quiet
    if($LASTEXITCODE){throw 'Mapped fixture build failed.'}
    $rebuilt="$root/export$workers/Fixture/bin/Release/net48/Fixture.exe"
    & $rebuilt
    if($LASTEXITCODE){throw 'Mapped state-machine behavior or reflection names failed.'}
    $metadata=[dnlib.DotNet.ModuleDefMD]::Load($rebuilt)
    try {
        $cacheFields=@($metadata.GetTypes() | Where-Object {$_.Name.String.StartsWith('<>O')} | ForEach-Object Fields)
        foreach($suffix in '__e','__f'){
            if(@($cacheFields|Where-Object {$_.Name.String.EndsWith($suffix)}).Count -eq 0){throw "Delegate cache restoration was not exercised: $suffix"}
        }
    } finally {$metadata.Dispose()}
    $before=(Get-FileHash -LiteralPath $rebuilt).Hash
    dotnet build "$root/export$workers/solution.sln" -c Release --nologo -v quiet
    if($LASTEXITCODE -or (Get-FileHash -LiteralPath $rebuilt).Hash -ne $before){throw 'Incremental restoration changed the assembly.'}
}
if((Get-FileHash -LiteralPath $original).Hash -ne $hash){throw 'Input assembly changed.'}
