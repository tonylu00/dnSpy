using System.Diagnostics;
using System.Security.Cryptography;
using System.Xml.Linq;
using dnlib.DotNet;

if(args.Length!=2)throw new ArgumentException("Usage: SourceParameterCaptureRegression <dnSpy.Console> <new-work-directory>");
var exporter=Path.GetFullPath(args[0]);var root=Path.GetFullPath(args[1]);
if(Directory.Exists(root))throw new IOException("Choose a new work directory.");
Directory.CreateDirectory(root);
void Write(string relative,string text){var path=Path.Combine(root,relative);Directory.CreateDirectory(Path.GetDirectoryName(path)!);File.WriteAllText(path,text);}
void Run(string executable,params string[] arguments){
    var info=new ProcessStartInfo(executable){UseShellExecute=false,RedirectStandardOutput=true,RedirectStandardError=true};
    foreach(var argument in arguments)info.ArgumentList.Add(argument);
    using var process=Process.Start(info)!;var stdout=process.StandardOutput.ReadToEndAsync();var stderr=process.StandardError.ReadToEndAsync();process.WaitForExit();Task.WaitAll(stdout,stderr);
    if(process.ExitCode!=0)throw new Exception(executable+" failed: "+stdout.Result+stderr.Result);
}
Write("Library/Library.csproj","<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net48</TargetFramework></PropertyGroup></Project>");
Write("Library/Api.cs","""
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
public static class Api {
 public static Func<string> Make(string a) { return () => a; }
 public static Func<Func<string>> Nested(string a) { return () => () => a; }
 public static async Task<string> Async(string a) { await Task.Yield(); Func<string> f = () => a; return f(); }
 public static async Task<T> Generic<T>(T a) { await Task.Yield(); Func<T> f = () => a; return f(); }
 public static IEnumerable<string> Iterate(string a) { Func<string> f = () => a; yield return f(); }
 public static string OrdinaryField(string a) { return new Payload { payload = a }.payload; }
 public sealed class Payload { public string payload; }
}
""");
Write("Caller/Caller.csproj","<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType></PropertyGroup><ItemGroup><ProjectReference Include=\"../Library/Library.csproj\"/></ItemGroup></Project>");
Write("Caller/Program.cs","""
using System;
using System.Linq;
class Program { static int Main() {
 if(Api.Make("one")()!="one" || Api.Nested("two")()()!="two" || Api.Async("three").GetAwaiter().GetResult()!="three" ||
    Api.Generic(4).GetAwaiter().GetResult()!=4 || Api.Iterate("five").Single()!="five" || Api.OrdinaryField("six")!="six") throw new Exception("Capture behavior changed");
 foreach(var m in typeof(Api).GetMethods(System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.Static))
   if(m.GetParameters().Length==1 && m.GetParameters()[0].Name!="a")throw new Exception("Parameter identity changed");
 if(typeof(Api.Payload).GetField("payload")==null)throw new Exception("Ordinary field changed");
 Console.WriteLine("PASS synchronous, nested, async, generic and iterator captures plus ordinary fields");return 0;
} }
""");
Run("dotnet","build",Path.Combine(root,"Caller/Caller.csproj"),"-c","Release","--nologo","-v","quiet");
var inputs=Path.Combine(root,"Caller/bin/Release/net48");Run(Path.Combine(inputs,"Caller.exe"));
var library=Path.Combine(inputs,"Library.dll");
var map=new XElement("SourceNameMap",new XAttribute("Version","1"),new XAttribute("InputDirectory",inputs));
using(var module=ModuleDefMD.Load(library)) {
    var row=new XElement("Module",new XAttribute("Path","Library.dll"),new XAttribute("Mvid",module.Mvid!),new XAttribute("Sha256",Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(library)))));
    foreach(var method in module.GetTypes().Single(t=>t.Name=="Api").Methods.Where(m=>m.IsPublic&&m.IsStatic)) {
        var entry=new XElement("Method",new XAttribute("Token","0x"+method.MDToken.Raw.ToString("X8")),new XAttribute("ExpectedName",method.Name),new XAttribute("Signature",method.FullName));
        if(method.Name=="Generic")entry.Add(new XAttribute("NewName","GetCapturedValueAsync"));
        entry.Add(new XElement("Parameter",new XAttribute("Sequence","1"),new XAttribute("ExpectedName","a"),new XAttribute("NewName","payload")));row.Add(entry);
    }
    map.Add(row);
}
var mapPath=Path.Combine(root,"names.xml");new XDocument(map).Save(mapPath);
foreach(var name in new[]{"baseline","aliased"}) {
    var output=Path.Combine(root,name);var arguments=new List<string>{"--no-color","--sdk-project","--threads","2","-o",output};
    if(name=="aliased")arguments.AddRange(new[]{"--source-name-map",mapPath});
    arguments.AddRange(new[]{library,Path.Combine(inputs,"Caller.exe")});Run(exporter,arguments.ToArray());
    Run("dotnet","build",Path.Combine(output,"solution.sln"),"-c","Release","--nologo","-v","quiet");
    var caller=Path.Combine(output,"Caller/bin/Release/net48/Caller.exe");Run(caller);
    File.Copy(Path.Combine(inputs,"Caller.exe"),caller,true);Run(caller);
}
string[] Fields(string name){using var module=ModuleDefMD.Load(Path.Combine(root,name,"Library/bin/Release/net48/Library.dll"));return module.GetTypes().SelectMany(t=>t.Fields).Select(f=>f.FullName).OrderBy(n=>n,StringComparer.Ordinal).ToArray();}
if(!Fields("baseline").SequenceEqual(Fields("aliased")))throw new Exception("Captured field names/signatures differ from baseline: "+string.Join("; ",Fields("aliased").Except(Fields("baseline"))));
// Re-running restoration on already-restored outputs remains safe.
Run("dotnet","build",Path.Combine(root,"aliased/solution.sln"),"-c","Release","--nologo","-v","quiet");
if(!Fields("baseline").SequenceEqual(Fields("aliased")))throw new Exception("Incremental build changed captured fields.");
Console.WriteLine("PASS: parameter/closure names and field signatures restored; generated and unchanged callers execute correctly; incremental build is idempotent.");
