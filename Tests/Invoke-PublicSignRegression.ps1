param([Parameter(Mandatory)][string]$DnSpyConsole,[Parameter(Mandatory)][string]$SigningKey,[Parameter(Mandatory)][string]$OutputDirectory,[string]$StrongNameTool)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $OutputDirectory){throw 'Choose a new test directory'}
$root=[IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory "$root\library","$root\friend" | Out-Null
Copy-Item -LiteralPath $SigningKey -Destination "$root\test.snk"
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><LangVersion>latest</LangVersion><SignAssembly>true</SignAssembly><AssemblyOriginatorKeyFile>..\test.snk</AssemblyOriginatorKeyFile></PropertyGroup></Project>' | Set-Content "$root\library\SignedLibrary.csproj"
@'
public static class Api {
 internal static int Hidden() => 7;
 public static (int Count,string Label) Read() => (42, new System.Resources.ResourceManager("SignedLibrary.Words",typeof(Api).Assembly).GetString("Label"));
}
'@ | Set-Content "$root\library\Api.cs"
foreach($pair in @(@('Words.resx','Hello'),@('Words.zh-CN.resx','你好'))){
 ('<root><resheader name="resmimetype"><value>text/microsoft-resx</value></resheader><resheader name="version"><value>2.0</value></resheader><resheader name="reader"><value>System.Resources.ResXResourceReader, System.Windows.Forms</value></resheader><resheader name="writer"><value>System.Resources.ResXResourceWriter, System.Windows.Forms</value></resheader><data name="Label" xml:space="preserve"><value>'+ $pair[1]+'</value></data></root>') | Set-Content (Join-Path "$root\library" $pair[0])
}
dotnet build "$root\library\SignedLibrary.csproj" -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'Original library failed'}
$identity=[Reflection.AssemblyName]::GetAssemblyName("$root\library\bin\Release\net48\SignedLibrary.dll")
$key=([BitConverter]::ToString($identity.GetPublicKey())).Replace('-','')
('[assembly:System.Runtime.CompilerServices.InternalsVisibleTo("Friend, PublicKey='+$key+'")]') | Set-Content "$root\library\Friends.cs"
'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net48</TargetFramework><LangVersion>latest</LangVersion><OutputType>Exe</OutputType><SignAssembly>true</SignAssembly><AssemblyOriginatorKeyFile>..\test.snk</AssemblyOriginatorKeyFile></PropertyGroup><ItemGroup><ProjectReference Include="..\library\SignedLibrary.csproj"/></ItemGroup></Project>' | Set-Content "$root\friend\Friend.csproj"
@'
class Program { static int Main() {
 System.Threading.Thread.CurrentThread.CurrentUICulture=System.Globalization.CultureInfo.GetCultureInfo("zh-CN");
 var result=Api.Read();
 if(result.Count!=42 || result.Label!="你好" || Api.Hidden()!=7) throw new System.Exception("SDK, friend or satellite mismatch");
 System.Console.WriteLine("PASS tuple contract, keyed friend and translated satellite"); return 0;
} }
'@ | Set-Content "$root\friend\Program.cs"
dotnet build "$root\friend\Friend.csproj" -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'Original friend failed'}
& "$root\friend\bin\Release\net48\Friend.exe"
if($LASTEXITCODE){throw 'Original runtime failed'}
$inputRoot="$root\friend\bin\Release\net48"
$hashes=@(Get-ChildItem $inputRoot -Recurse -File | Get-FileHash)
& $DnSpyConsole --public-sign --no-color -o "$root\export" "$inputRoot\SignedLibrary.dll" "$inputRoot\Friend.exe"
if($LASTEXITCODE){throw 'Export failed'}
dotnet build "$root\export\solution.sln" -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'Public-sign rebuild failed'}
$runtime="$root\export\Friend\bin\Release\net48"
& "$runtime\Friend.exe"
if($LASTEXITCODE){throw 'Rebuilt caller failed'}
foreach($relative in 'Friend.exe','SignedLibrary.dll','zh-CN\SignedLibrary.resources.dll'){
 $before=[Reflection.AssemblyName]::GetAssemblyName((Join-Path $inputRoot $relative)).FullName
 $after=[Reflection.AssemblyName]::GetAssemblyName((Join-Path $runtime $relative)).FullName
 if($before -ne $after){throw "Assembly identity changed: $relative"}
}
$incremental=@(Get-ChildItem "$root\export\SignedLibrary\bin\Release\net48" -Recurse -File | Get-FileHash)
dotnet build "$root\export\solution.sln" -c Release --nologo -v quiet
if($LASTEXITCODE){throw 'Incremental build failed'}
foreach($hash in $incremental){if((Get-FileHash -LiteralPath $hash.Path).Hash -ne $hash.Hash){throw 'Incremental output changed'}}
if($StrongNameTool){
 & $StrongNameTool -vf "$inputRoot\SignedLibrary.dll"
 if($LASTEXITCODE){throw 'Original fixture signature is invalid'}
 & $StrongNameTool -vf "$runtime\SignedLibrary.dll"
 if(!$LASTEXITCODE){throw 'Public-signed output unexpectedly verifies as a genuine signature'}
}
Copy-Item "$inputRoot\Friend.exe" "$runtime\Friend.exe" -Force
& "$runtime\Friend.exe"
if($LASTEXITCODE){throw 'Unchanged signed caller failed'}
foreach($hash in $hashes){if((Get-FileHash -LiteralPath $hash.Path).Hash -ne $hash.Hash){throw 'Original input changed'}}
'PASS public-key identities and unchanged signed caller; no valid cryptographic signature claimed'
