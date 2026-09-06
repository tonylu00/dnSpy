param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression output folder.'}
$inputDirectory=Join-Path $OutputDirectory 'input'
$emitterDirectory=Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $inputDirectory,$emitterDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'RecordWithFixture.cs') -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitRecordCloneNames.cs') -Destination $emitterDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><Optimize>true</Optimize><LangVersion>latest</LangVersion></PropertyGroup></Project>' | Set-Content (Join-Path $inputDirectory 'RecordWithFixture.csproj')
$dnlib=[Security.SecurityElement]::Escape((Join-Path (Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))) 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitterDirectory 'Emitter.csproj')
dotnet build (Join-Path $inputDirectory 'RecordWithFixture.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Record fixture build failed.'}
$original=Join-Path $inputDirectory 'bin\Release\net48\RecordWithFixture.exe'
foreach($renamed in @($false,$true)) {
    $input=$original; $arguments=@()
    if($renamed) {
        $input=Join-Path $OutputDirectory 'RecordWithFixture.exe'; $arguments=@('renamed')
        dotnet run --project (Join-Path $emitterDirectory 'Emitter.csproj') -c Release -- $original $input
        if($LASTEXITCODE -ne 0){throw 'Record clone renaming failed.'}
    }
    & $input @arguments
    if($LASTEXITCODE -ne 0){throw 'Original record behavior failed.'}
    $consumer=Join-Path $OutputDirectory "consumer-$renamed"
    New-Item -ItemType Directory -Path $consumer | Out-Null
    $baseCopy=if($renamed){'source.CopyRecord()'}else{'source with { }'}
    $genericCopy=if($renamed){'generic.CopyRecord()'}else{'generic with { }'}
    @"
using System;
class Consumer {
    static void Main() {
        RecordTrace.Text = "";
        RecordBase source = new DerivedRecord(23, "consumer");
        var copy = $baseCopy;
        if (copy.GetType() != typeof(DerivedRecord) || ReferenceEquals(source, copy) || copy.Value != 23 ||
            ((DerivedRecord)copy).Name != "consumer" || RecordTrace.Text != "BD") throw new Exception("External virtual clone changed");
        var generic = new GenericRecord<string>("external", 9);
        var genericCopy = $genericCopy;
        if (genericCopy.Value != "external" || genericCopy.Count != 9 || ReferenceEquals(generic, genericCopy))
            throw new Exception("External generic clone changed");
        Console.WriteLine("Unchanged record consumer: 2 checks");
    }
}
"@ | Set-Content (Join-Path $consumer 'Program.cs')
    $reference=[Security.SecurityElement]::Escape($input)
    "<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><LangVersion>latest</LangVersion></PropertyGroup><ItemGroup><Reference Include=`"RecordWithFixture`"><HintPath>$reference</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $consumer 'Consumer.csproj')
    dotnet build (Join-Path $consumer 'Consumer.csproj') -c Release --nologo -v quiet
    if($LASTEXITCODE -ne 0){throw 'Record binary consumer build failed.'}
    $consumerExe=Join-Path $consumer 'bin\Release\net48\Consumer.exe'
    $consumerHash=(Get-FileHash -LiteralPath $consumerExe).Hash
    & $consumerExe
    if($LASTEXITCODE -ne 0){throw 'Original record binary contract failed.'}
    foreach($threads in @(1,4)) {
        $export=Join-Path $OutputDirectory "export-$renamed-$threads"
        & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $input
        if($LASTEXITCODE -ne 0){throw 'Record export failed.'}
        $project=Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
        $rebuilt=Join-Path $OutputDirectory "rebuilt-$renamed-$threads"
        dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
        if($LASTEXITCODE -ne 0){throw 'Record source compilation failed.'}
        & (Join-Path $rebuilt 'RecordWithFixture.exe') @arguments
        if($LASTEXITCODE -ne 0){throw 'Rebuilt record behavior changed.'}
        Copy-Item -LiteralPath (Join-Path $rebuilt 'RecordWithFixture.exe') -Destination (Split-Path $consumerExe) -Force
        if((Get-FileHash -LiteralPath $consumerExe).Hash -ne $consumerHash){throw 'Consumer was unexpectedly rebuilt.'}
        & $consumerExe
        if($LASTEXITCODE -ne 0){throw 'Rebuilt record binary contract changed.'}
    }
}
$debug=Join-Path $OutputDirectory 'debug'
New-Item -ItemType Directory -Path $debug | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'RecordWithDebug.cs') -Destination $debug
$runtime=Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$references=('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path=[Security.SecurityElement]::Escape((Join-Path $runtime ($_+'.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
foreach($input in @($original,(Join-Path $OutputDirectory 'RecordWithFixture.exe'))) {
    dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- $input
    if($LASTEXITCODE -ne 0){throw 'Record AST/debug/recognition guards failed.'}
}
