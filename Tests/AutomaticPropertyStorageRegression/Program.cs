using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Xml.Linq;
using dnlib.DotNet;

if (args.Length != 2) throw new ArgumentException("Usage: AutomaticPropertyStorageRegression <native-console> <fresh-directory>");
var root = Path.GetFullPath(args[1]); if (Directory.Exists(root)) throw new IOException("Fresh output required.");
Directory.CreateDirectory(root); File.WriteAllText(Path.Combine(root, "Directory.Build.props"), "<Project/>");
var input = Path.Combine(root, "input"); Directory.CreateDirectory(input);
var project = Path.Combine(input, "Storage.csproj");
File.WriteAllText(project, "<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><TargetFramework>net48</TargetFramework><OutputType>Exe</OutputType></PropertyGroup></Project>");
File.WriteAllText(Path.Combine(input, "Program.cs"), """
using System;
using System.IO;
using System.Reflection;
using System.Runtime.Serialization.Formatters.Binary;
using System.Threading;
[Serializable] public class Sample<T> {
 public int Count { get; }
 [field: NonSerialized] public T Value { get; set; }
 [field: ThreadStatic] public static int ThreadCount { get; set; }
 public Sample(int count, T value) { Count=count; Value=value; }
 public int IncreaseThread() { return ++ThreadCount; }
}
public static class Program {
 public static int Main(string[] args) {
  var type=typeof(Sample<int>);var flags=BindingFlags.NonPublic|BindingFlags.Instance|BindingFlags.Static;
  foreach(string name in new[]{"a","b","c"})if(type.GetField(name,flags)==null)throw new Exception("Missing runtime field "+name);
  if(type.GetFields(flags).Length!=3)throw new Exception("Unexpected storage");
  if(!type.GetField("a",flags).IsInitOnly || !type.GetField("b",flags).IsNotSerialized || !type.GetField("c",flags).IsDefined(typeof(ThreadStaticAttribute),false))throw new Exception("Storage flags changed");
  for(int i=0;i<128;i++) {
   var value=new Sample<int>(i,2*i); if(value.Count!=i || value.Value!=2*i)throw new Exception("Accessors");
   type.GetField("b",flags).SetValue(value,3*i);if(value.Value!=3*i)throw new Exception("Reflection disagrees with accessors");
  }
  Sample<int>.ThreadCount=31;int child=-1;var thread=new Thread(()=>{child=Sample<int>.ThreadCount;Sample<int>.ThreadCount=42;});thread.Start();thread.Join();
  if(child!=0 || new Sample<int>(0,0).IncreaseThread()!=32)throw new Exception("Thread static storage");
  if(args[0]=="write")using(var f=File.Create(args[1]))new BinaryFormatter().Serialize(f,new Sample<int>(731,42));
  else using(var f=File.OpenRead(args[1])) {var value=(Sample<int>)new BinaryFormatter().Deserialize(f);if(value.Count!=731 || value.Value!=0)throw new Exception("Original serialized field contract");}
  Console.WriteLine("PASS storage reflection, generic accessors, thread static and serialization");return 0;
 }
}
""");
await Run("dotnet", "build", project, "-c", "Release", "-nologo", "-v:q");
var compiled = Path.Combine(input, "bin", "Release", "net48", "Storage.exe");
var original = Path.Combine(root, "original", "Storage.exe"); Directory.CreateDirectory(Path.GetDirectoryName(original)!);
// Fixture generation only: mimic renamed compiler storage with dnlib. No ETS inputs are modified.
using (var module = ModuleDefMD.Load(compiled)) {
    module.LoadEverything();
    var type = module.GetTypes().Single(t => t.Name == "Sample`1");
    var names = type.Fields.ToDictionary(f => f, f => f.Name.String switch { "<Count>k__BackingField" => "a", "<Value>k__BackingField" => "b", "<ThreadCount>k__BackingField" => "c", _ => throw new Exception("Unexpected fixture field") });
    var refs = module.GetMemberRefs().Concat(module.GetTypes().SelectMany(t => t.Methods).Where(m => m.HasBody).SelectMany(m => m.Body.Instructions).Select(i => i.Operand).OfType<MemberRef>()).Distinct()
        .Where(r => r.IsFieldRef && r.DeclaringType is TypeSpec s && s.TypeSig is GenericInstSig g && g.GenericType.TypeDefOrRef == type)
        .Select(r => (Reference:r, Field:type.Fields.Single(f => f.Name == r.Name))).ToArray();
    if (refs.Select(r => r.Field).Distinct().Count() != 3) throw new Exception("Expected three generic storage definitions");
    foreach (var r in refs) r.Reference.Name = names[r.Field]; foreach (var field in names) field.Key.Name = field.Value;
    module.Write(original);
}
var originalHash = Hash(original); var payload = Path.Combine(root, "original.bin"); await Run(original, "write", payload); await Run(original, "read", payload);
var map = Path.Combine(root, "map.xml");
using (var module = ModuleDefMD.Load(original)) {
    var fields = module.GetTypes().Single(t => t.Name == "Sample`1").Fields;
    new XDocument(new XElement("SourceNameMap", new XAttribute("Version", "1"), new XAttribute("InputDirectory", Path.GetDirectoryName(original)!),
        new XElement("Module", new XAttribute("Path", "Storage.exe"), new XAttribute("Sha256", originalHash), new XAttribute("Mvid", module.Mvid!),
            fields.Select(f => new XElement("Field", new XAttribute("Token", "0x" + f.MDToken.Raw.ToString("X8")), new XAttribute("ExpectedName", f.Name), new XAttribute("Signature", f.FullName), new XAttribute("NewName", "stored" + f.Name.String.ToUpperInvariant())))))).Save(map);
}
var export = Path.Combine(root, "export");
await Run(Path.GetFullPath(args[0]), "--no-color", "--sdk-project", "--source-name-map", map, "-o", export, original);
var solution = Path.Combine(export, "solution.sln"); await Run("dotnet", "build", solution, "-c", "Release", "-nologo", "-v:q");
var rebuilt = Path.Combine(export, "Storage", "bin", "Release", "net48", "Storage.exe");
using (var before = ModuleDefMD.Load(original)) using (var after = ModuleDefMD.Load(rebuilt)) {
    var fields = before.GetTypes().Single(t => t.Name == "Sample`1").Fields;
    var restored = after.GetTypes().Single(t => t.Name == "Sample`1").Fields;
    foreach (var field in fields) { var match = restored.Single(f => f.FullName == field.FullName); if (match.Attributes != field.Attributes) throw new Exception("Field flags differ"); }
    if (after.GetTypes().SelectMany(t => t.Fields).SelectMany(f => f.CustomAttributes).Any(a => a.TypeFullName == "System.Reflection.ObfuscationAttribute")) throw new Exception("Restoration marker leaked");
}
await Run(rebuilt, "read", payload); var rebuiltPayload = Path.Combine(root, "rebuilt.bin"); await Run(rebuilt, "write", rebuiltPayload); await Run(original, "read", rebuiltPayload);
string rebuiltHash = Hash(rebuilt); await Run("dotnet", "build", solution, "-c", "Release", "-nologo", "-v:q");
if (Hash(rebuilt) != rebuiltHash || Hash(original) != originalHash) throw new Exception("Incremental output or original changed");
File.WriteAllText(Path.Combine(root, "result.json"), JsonSerializer.Serialize(new { Fields = 3, OriginalAndRebuiltExecuted = true, BidirectionalSerialization = true, GenericReflectionAndThreadStatic = true, IncrementalStable = true, OriginalSha256 = originalHash, RebuiltSha256 = rebuiltHash }, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine("PASS: native automatic property storage names, flags, generic references and unchanged serialized payloads.");
static string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
static async Task Run(string executable, params string[] arguments) {
    var start = new ProcessStartInfo(executable) { UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true, CreateNoWindow = true };
    foreach (var argument in arguments) start.ArgumentList.Add(argument);
    using var process = Process.Start(start)!; var stdout = process.StandardOutput.ReadToEndAsync(); var stderr = process.StandardError.ReadToEndAsync();
    await process.WaitForExitAsync(); Console.Write(await stdout); Console.Error.Write(await stderr);
    if (process.ExitCode != 0) throw new Exception($"Failed: {executable} ({process.ExitCode})");
}
