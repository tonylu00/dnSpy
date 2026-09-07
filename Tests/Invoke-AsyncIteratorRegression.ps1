param(
    [Parameter(Mandatory)][string] $DnSpyConsole,
    [Parameter(Mandatory)][string] $OutputDirectory
)
$ErrorActionPreference='Stop'
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new regression output folder.'}
$inputDirectory=Join-Path $OutputDirectory 'input'
New-Item -ItemType Directory -Path $inputDirectory | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'AsyncIteratorFixture.cs') -Destination $inputDirectory
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><LangVersion>latest</LangVersion><Optimize>true</Optimize><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.Bcl.AsyncInterfaces" Version="9.0.0" /></ItemGroup></Project>' | Set-Content (Join-Path $inputDirectory 'AsyncIteratorFixture.csproj')
dotnet build (Join-Path $inputDirectory 'AsyncIteratorFixture.csproj') -c Release --nologo -v quiet
if($LASTEXITCODE -ne 0){throw 'Async iterator fixture build failed.'}
$original=Join-Path $inputDirectory 'bin\Release\net48\AsyncIteratorFixture.exe'
$runtime=Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$emitter=Join-Path $OutputDirectory 'emitter'
New-Item -ItemType Directory -Path $emitter | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'EmitAsyncIterator.cs') -Destination $emitter
$dnlib=[Security.SecurityElement]::Escape((Join-Path $runtime 'dnlib.dll'))
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><Reference Include=`"dnlib`"><HintPath>$dnlib</HintPath></Reference></ItemGroup></Project>" | Set-Content (Join-Path $emitter 'Emitter.csproj')
$reordered=Join-Path $OutputDirectory 'reordered'
Copy-Item -LiteralPath (Split-Path $original) -Destination $reordered -Recurse
dotnet run --project (Join-Path $emitter 'Emitter.csproj') -c Release -- $original (Join-Path $reordered 'AsyncIteratorFixture.exe')
if($LASTEXITCODE -ne 0){throw 'Iterator block rearrangement failed.'}
foreach($variant in @('compiler','reordered')) {
    $inputAssembly=if($variant -eq 'compiler'){$original}else{Join-Path $reordered 'AsyncIteratorFixture.exe'}
    & $inputAssembly
    if($LASTEXITCODE -ne 0){throw 'Input async iterator behavior failed.'}
    foreach($threads in @(1,4)) {
        $export=Join-Path $OutputDirectory "export-$variant-$threads"
        & $DnSpyConsole --no-color --sdk-project --threads $threads -o $export $inputAssembly
        if($LASTEXITCODE -ne 0){throw 'Async iterator export failed.'}
        $source=Get-Content (Join-Path $export 'AsyncIteratorFixture\AsyncIteratorFixture.cs') -Raw
        foreach($method in @('Range','Single','Empty','Cleanup','Cancellable','Items')) {
            if($source -notmatch "async IAsyncEnum(erable|erator)<[^>]+> $method") {throw "Iterator was not recovered: $method"}
        }
        if($source -match 'AsyncIteratorStateMachine\('){throw 'Reconstructed iterator retained its state machine attribute.'}
        $project=Get-ChildItem -LiteralPath $export -Recurse -Filter '*.csproj' | Select-Object -First 1
        $rebuilt=Join-Path $OutputDirectory "rebuilt-$variant-$threads"
        dotnet build $project.FullName -c Release -o $rebuilt --nologo -v quiet
        if($LASTEXITCODE -ne 0){throw 'Async iterator source compilation failed.'}
        & (Join-Path $rebuilt 'AsyncIteratorFixture.exe')
        if($LASTEXITCODE -ne 0){throw 'Rebuilt async iterator behavior changed.'}
    }
}
$debug=Join-Path $OutputDirectory 'debug'
New-Item -ItemType Directory -Path $debug | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'AsyncIteratorDebug.cs') -Destination $debug
$runtime=Split-Path ([IO.Path]::GetFullPath($DnSpyConsole))
$references=('ICSharpCode.NRefactory','ICSharpCode.NRefactory.CSharp','ICSharpCode.Decompiler','dnlib','dnSpy.Contracts.Logic' | ForEach-Object {
    $path=[Security.SecurityElement]::Escape((Join-Path $runtime ($_+'.dll')))
    "<Reference Include=`"$_`"><HintPath>$path</HintPath></Reference>"
}) -join ''
"<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><TargetFramework>net10.0-windows</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup>$references</ItemGroup></Project>" | Set-Content (Join-Path $debug 'Debug.csproj')
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release -- $original
if($LASTEXITCODE -ne 0){throw 'Async iterator debug or rejection guard failed.'}
dotnet run --project (Join-Path $debug 'Debug.csproj') -c Release --no-build -- (Join-Path $reordered 'AsyncIteratorFixture.exe')
if($LASTEXITCODE -ne 0){throw 'Reordered iterator debug or rejection guard failed.'}
