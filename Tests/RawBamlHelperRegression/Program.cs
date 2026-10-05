using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using dnlib.DotNet;

if(args.Length!=3)throw new ArgumentException("Usage: RawBamlHelperRegression <old-console> <new-console> <fresh-directory>");
if(!OperatingSystem.IsWindows())throw new PlatformNotSupportedException("This fixture executes WPF.");
var root=Path.GetFullPath(args[2]);if(Directory.Exists(root))throw new IOException("Fresh directory required.");
Directory.CreateDirectory(root);File.WriteAllText(Path.Combine(root,"Directory.Build.props"),"<Project/>");
var input=Path.Combine(root,"input");Directory.CreateDirectory(input);
var project=Path.Combine(input,"RawBaml.csproj");
File.WriteAllText(project,"<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType><UseWPF>true</UseWPF></PropertyGroup></Project>");
File.WriteAllText(Path.Combine(input,"resources.xaml"),"<ResourceDictionary xmlns=\"http://schemas.microsoft.com/winfx/2006/xaml/presentation\" xmlns:x=\"http://schemas.microsoft.com/winfx/2006/xaml\" xmlns:local=\"clr-namespace:Fixture\"><local:PrivateControl x:Key=\"control\" /></ResourceDictionary>");
File.WriteAllText(Path.Combine(input,"Program.cs"),"""
using System;
using System.Windows;
using System.Windows.Controls;
namespace Fixture {
 internal class PrivateControl : Control { public PrivateControl() { Tag = "raw-baml-value"; } }
 public static class Program {
  [STAThread] public static int Main() {
   var helper=typeof(XamlGeneratedNamespace.GeneratedInternalTypeHelper);
   if(!helper.IsPublic || helper.BaseType!=typeof(System.Windows.Markup.InternalTypeHelper))throw new Exception("Helper contract changed");
   var app=new Application();
   var dictionary=new ResourceDictionary { Source=new Uri("/RawBaml;component/resources.xaml",UriKind.Relative) };
   var value=(Control)dictionary["control"];
   if(value.GetType().FullName!="Fixture.PrivateControl" || (string)value.Tag!="raw-baml-value")throw new Exception("Internal BAML behavior changed");
   Console.WriteLine("PASS: original helper and internal BAML behavior");return 0;
  }
 }
}
""");
await Run("dotnet","build",project,"-c","Release","-nologo","-v:q");
var original=Path.Combine(input,"bin","Release","net48","RawBaml.exe");var originalHash=Hash(original);
await Run(original);
string helperName="XamlGeneratedNamespace.GeneratedInternalTypeHelper";
string[] contracts;byte[] originalBaml;
using(var m=ModuleDefMD.Load(original)) {contracts=m.GetTypes().Single(t=>t.FullName==helperName).Methods.Select(t=>t.FullName).Order().ToArray();originalBaml=((EmbeddedResource)m.Resources.Single(r=>r.Name=="RawBaml.g.resources")).CreateReader().ToArray();}
var exports=new List<string>();
for(int i=0;i<2;i++) {
 var export=Path.Combine(root,i==0?"old-export":"new-export");exports.Add(export);
 await Run(Path.GetFullPath(args[i]),"--no-color","--sdk-project","--no-baml","-o",export,original);
 var hasHelper=Directory.GetFiles(export,"*.cs",SearchOption.AllDirectories).Any(p=>File.ReadAllText(p).Contains("class GeneratedInternalTypeHelper"));
 if(hasHelper!=(i==1))throw new Exception("Expected old omission and new helper retention");
}
await Run("dotnet","build",Path.Combine(exports[1],"solution.sln"),"-c","Release","-nologo","-v:q");
var rebuilt=Path.Combine(exports[1],"RawBaml","bin","Release","net48","RawBaml.exe");
using(var m=ModuleDefMD.Load(rebuilt)) {
 var helper=m.GetTypes().Single(t=>t.FullName==helperName);
 if(!helper.IsPublic || !helper.Methods.Select(t=>t.FullName).Order().SequenceEqual(contracts))throw new Exception("Helper metadata contract changed");
 if(!((EmbeddedResource)m.Resources.Single(r=>r.Name=="RawBaml.g.resources")).CreateReader().ToArray().SequenceEqual(originalBaml))throw new Exception("Raw BAML changed");
}
await Run(rebuilt);var rebuiltHash=Hash(rebuilt);
await Run("dotnet","build",Path.Combine(exports[1],"solution.sln"),"-c","Release","-nologo","-v:q");
if(Hash(rebuilt)!=rebuiltHash || Hash(original)!=originalHash)throw new Exception("Inputs or incremental output changed");
File.WriteAllText(Path.Combine(root,"result.json"),JsonSerializer.Serialize(new {OldExporterOmissionObserved=true,HelperMethods=contracts.Length,RawBamlUnchanged=true,OriginalAndRebuiltExecuted=true,IncrementalStable=true,OriginalSha256=originalHash,RebuiltSha256=rebuiltHash},new JsonSerializerOptions {WriteIndented=true}));
Console.WriteLine("PASS: raw BAML helper retention, metadata, execution and incremental stability.");
static string Hash(string path)=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
static async Task Run(string executable,params string[] arguments) {
 var start=new ProcessStartInfo(executable) {UseShellExecute=false,RedirectStandardOutput=true,RedirectStandardError=true,CreateNoWindow=true};
 foreach(var argument in arguments)start.ArgumentList.Add(argument);
 using var process=Process.Start(start)!;var stdout=process.StandardOutput.ReadToEndAsync();var stderr=process.StandardError.ReadToEndAsync();
 await process.WaitForExitAsync();Console.Write(await stdout);Console.Error.Write(await stderr);
 if(process.ExitCode!=0)throw new Exception($"Failed: {executable} ({process.ExitCode})");
}
