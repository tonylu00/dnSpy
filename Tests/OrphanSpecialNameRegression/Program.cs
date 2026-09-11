using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json.Nodes;
using dnlib.DotNet;

if (args.Length != 3 || Directory.Exists(args[2])) throw new ArgumentException("Usage: OrphanSpecialNameRegression <dnSpy.Console.exe> <NameCandidates.dll> <new-output-directory>");
string exporter=Path.GetFullPath(args[0]), names=Path.GetFullPath(args[1]), root=Path.GetFullPath(args[2]);
Directory.CreateDirectory(root); File.WriteAllText(Path.Combine(root,"Directory.Build.props"),"<Project/>");
int index=0;
async Task Run(string executable, params string[] arguments) {
    var start=new ProcessStartInfo(executable) { WorkingDirectory=root, UseShellExecute=false, CreateNoWindow=true, RedirectStandardOutput=true, RedirectStandardError=true };
    foreach(string argument in arguments) start.ArgumentList.Add(argument);
    using var process=Process.Start(start)!;
    var stdout=process.StandardOutput.ReadToEndAsync(); var stderr=process.StandardError.ReadToEndAsync();
    await process.WaitForExitAsync();
    string log=Path.Combine(root,$"command-{index++:D3}.log"); File.WriteAllText(log,await stdout+await stderr);
    if(process.ExitCode!=0) throw new Exception($"Exit {process.ExitCode}: {log}");
}
void Project(string name,string source,string reference="",bool executable=false) {
    string folder=Path.Combine(root,name); Directory.CreateDirectory(folder);
    File.WriteAllText(Path.Combine(folder,name+".csproj"),$"<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net48</TargetFramework><LangVersion>latest</LangVersion><Optimize>true</Optimize><OutputType>{(executable?"Exe":"Library")}</OutputType></PropertyGroup><ItemGroup>{reference}</ItemGroup></Project>");
    File.WriteAllText(Path.Combine(folder,"Code.cs"),source);
}
Project("Library","""
using System;
public class Api {
    int stored; EventHandler changed;
    public int a() { return stored; }
    public void b(int value) { stored=value; }
    public void c(EventHandler value) { changed+=value; }
    public void d(EventHandler value) { changed-=value; }
    public void Raise() { changed?.Invoke(this,EventArgs.Empty); }
    public static int f() { return 42; }
    public int Value { get { return a(); } }
    public static implicit operator int(Api value) { return value.a(); }
}
""");
Project("Client","""
using System;
using System.Linq;
class Program {
    static void Main() {
        var api=new Api(); int calls=0; EventHandler handler=(sender,e)=>calls++;
        api.b(17); api.c(handler); api.Raise(); api.d(handler); api.Raise();
        if(api.a()!=17 || api.Value!=17 || (int)api!=17 || Api.f()!=42 || calls!=1) throw new Exception("Behavior changed");
        foreach(string name in new[]{"a","b","c","d","f"}) if(!typeof(Api).GetMethod(name).IsSpecialName) throw new Exception("SpecialName flag was lost: "+name);
        if(typeof(Api).GetMethods().Any(m=>m.Name.StartsWith("Reviewed")) || typeof(Api).GetMethod("b").GetParameters()[0].Name!="value") throw new Exception("Runtime names changed");
        Console.WriteLine("PASS orphan getter/setter/event-like/static methods, original flags/names, attached property and operator behavior");
    }
}
""","<ProjectReference Include=\"../Library/Library.csproj\"/>",true);
await Run("dotnet","build","Client/Client.csproj","-c","Release","--nologo","-v","quiet");
string input=Path.Combine(root,"input"); Directory.CreateDirectory(input);
foreach(string name in new[]{"Client.exe","Library.dll"}) File.Copy(Path.Combine(root,"Client/bin/Release/net48",name),Path.Combine(input,name));
string library=Path.Combine(input,"Library.dll");
using(var module=ModuleDefMD.Load(File.ReadAllBytes(library))) {
    foreach(var method in module.GetTypes().SelectMany(t=>t.Methods).Where(m=>new[]{"a","b","c","d","f"}.Contains(m.Name.String))) method.IsSpecialName=true;
    module.Write(library);
}
await Run(Path.Combine(input,"Client.exe"));
var hashes=Directory.GetFiles(input).ToDictionary(p=>p,p=>SHA256.HashData(File.ReadAllBytes(p)));
string reviewPath=Path.Combine(root,"review.json"), map=Path.Combine(root,"names.xml");
await Run("dotnet",names,"--review",library,reviewPath);
var review=JsonNode.Parse(File.ReadAllText(reviewPath))!;
foreach(var row in review["Methods"]!.AsArray()) {
    string original=row!["OriginalName"]!.GetValue<string>();
    if(original is "get_Value" or "op_Implicit") {
        if(row["MappingBlocker"]==null) throw new Exception("Actual syntax contract was unguarded");
        continue;
    }
    if(!new[]{"a","b","c","d","f"}.Contains(original)) continue;
    if(row["MappingBlocker"]!=null) throw new Exception("Orphan method blocked: "+row);
    row["NewName"]="Reviewed"+original;
    foreach(var parameter in row["ParameterNames"]!.AsArray()) parameter!["NewName"]=original=="b"?"newValue":"handler";
}
File.WriteAllText(reviewPath,review.ToJsonString());
await Run("dotnet",names,"--review-map",reviewPath,input,map);
foreach(int workers in new[]{1,4}) {
    string export=Path.Combine(root,"export"+workers);
    await Run(exporter,"--no-color","--source-name-map",map,"--threads",workers.ToString(),"--asm-path",input,"-o",export,library,Path.Combine(input,"Client.exe"));
    await Run("dotnet","build",Path.Combine(export,"solution.sln"),"-c","Release","--nologo","-v","quiet");
    string built=Path.Combine(export,"Client/bin/Release/net48");
    await Run(Path.Combine(built,"Client.exe"));
    var first=SHA256.HashData(File.ReadAllBytes(Path.Combine(built,"Library.dll")));
    await Run("dotnet","build",Path.Combine(export,"solution.sln"),"-c","Release","--nologo","-v","quiet");
    if(!first.SequenceEqual(SHA256.HashData(File.ReadAllBytes(Path.Combine(built,"Library.dll"))))) throw new Exception("Incremental output changed");
    File.Copy(Path.Combine(input,"Client.exe"),Path.Combine(built,"Client.exe"),true);
    await Run(Path.Combine(built,"Client.exe"));
}
if(hashes.Any(p=>!p.Value.SequenceEqual(SHA256.HashData(File.ReadAllBytes(p.Key))))) throw new Exception("Input changed");
Console.WriteLine("PASS orphan SpecialName maps, one/four workers, rebuilt/unchanged callers, runtime flags, parameter aliases, unchanged property/operator contracts and stable incremental builds.");
