using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Xml.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

if (args.Length != 2) throw new ArgumentException("ApplicationNameGraphRegression <graph.dll> <fresh-directory>");
string tool = Path.GetFullPath(args[0]), root = Path.GetFullPath(args[1]);
if (Directory.Exists(root)) throw new IOException("Use a fresh directory.");
Directory.CreateDirectory(root);
var manifest = new XElement("DnSpyExportMap", new XAttribute("Version", 1), new XAttribute("ExportErrors", 0));
var names = new XElement("SourceNameMap", new XAttribute("Version", 1), new XAttribute("InputDirectory", root));
ModuleDefUser Module(string name) { var m = new ModuleDefUser(name + ".dll") { Kind = ModuleKind.Dll, Mvid = Guid.NewGuid() }; new AssemblyDefUser(name, new Version(1, 0, 0, 0)).Modules.Add(m); return m; }
TypeDef Type(ModuleDef m, string name) { var t = new TypeDefUser("Fixture", name, m.CorLibTypes.Object.TypeDefOrRef) { Attributes = TypeAttributes.Public }; m.Types.Add(t); return t; }
void Save(ModuleDef module, string folder) {
    string directory = Path.Combine(root, folder); Directory.CreateDirectory(directory);
    string file = Path.Combine(directory, module.Name); module.Write(file);
    using var read = ModuleDefMD.Load(file);
    string project = folder + "/fixture.csproj"; File.WriteAllText(Path.Combine(root, project), "<Project/>");
    manifest.Add(new XElement("Project", new XAttribute("Source", file), new XAttribute("Project", project), new XAttribute("AssemblyName", read.Assembly.Name), new XAttribute("Mvid", read.Mvid!)));
}
ITypeDefOrRef Payload(ModuleDef m, string vendor) => new TypeRefUser(m, "Fixture", "Payload", new AssemblyRefUser(vendor, new Version(1, 0, 0, 0)));
foreach (string side in new[] { "A", "B" }) {
    var vendor = Module("Vendor" + side); Type(vendor, "Payload"); Save(vendor, "vendor" + side);
    var library = Module("Library"); var owner = Type(library, "Service");
    owner.Fields.Add(new FieldDefUser("b", new FieldSig(library.CorLibTypes.Int32), FieldAttributes.Public | FieldAttributes.Static));
    var method = new MethodDefUser("a", MethodSig.CreateStatic(library.CorLibTypes.Int32, new ClassSig(Payload(library, "Vendor" + side))), MethodImplAttributes.IL, MethodAttributes.Public | MethodAttributes.Static) { Body = new CilBody() };
    method.Body.Instructions.Add(Instruction.Create(OpCodes.Ldsfld, owner.Fields[0])); method.Body.Instructions.Add(Instruction.Create(OpCodes.Ret)); owner.Methods.Add(method); Save(library, side);
    foreach (bool valid in side == "A" ? new[] { true, false } : new[] { true }) {
        var caller = Module((valid ? "Valid" : "Invalid") + side); var type = Type(caller, "Caller");
        var target = new TypeRefUser(caller, "Fixture", "Service", new AssemblyRefUser("Library", new Version(1, 0, 0, 0)));
        var reference = new MemberRefUser(caller, "a", MethodSig.CreateStatic(caller.CorLibTypes.Int32, new ClassSig(Payload(caller, "Vendor" + (valid ? side : "B")))), target);
        var run = new MethodDefUser("Run", MethodSig.CreateStatic(caller.CorLibTypes.Int32), MethodImplAttributes.IL, MethodAttributes.Public | MethodAttributes.Static) { Body = new CilBody() };
        run.Body.Instructions.Add(Instruction.Create(OpCodes.Ldnull)); run.Body.Instructions.Add(Instruction.Create(OpCodes.Call, reference)); run.Body.Instructions.Add(Instruction.Create(OpCodes.Ret)); type.Methods.Add(run); Save(caller, side + "/" + caller.Assembly.Name);
    }
}
File.WriteAllText(Path.Combine(root, "A", "Sample.cs"), """
// A non-BMP character before spans: 😀
// Token: 0x02000002
class Service {
    // Token: 0x04000001
    int b;
    // Token: 0x06000001
    void a(object value) {
        var count = 0;
        foreach (var item in new object[0]) { }
        try { } catch (System.Exception failure) { }
        if (value is string text) { }
    }
}
""");
var native = Path.Combine(root, "native.bin"); File.WriteAllBytes(native, new byte[] { 1, 2, 3 });
manifest.Add(new XElement("Binary", new XAttribute("Source", native), new XAttribute("Path", "Native/native.bin")));
var exportFile = Path.Combine(root, "export.xml"); new XDocument(manifest).Save(exportFile);
var namesFile = Path.Combine(root, "names.xml"); new XDocument(names).Save(namesFile);
var output = Path.Combine(root, "graph");
var info = new ProcessStartInfo("dotnet") { UseShellExecute = false };
foreach (var arg in new[] { tool, exportFile, namesFile, output, "--no-gac", "--asm-path", Path.Combine(root, "vendorA"), "--asm-path", Path.Combine(root, "vendorB") }) info.ArgumentList.Add(arg);
using (var process = Process.Start(info)!) { process.WaitForExit(); if (process.ExitCode != 0) throw new Exception("Graph failed."); }
var graph = JsonDocument.Parse(File.ReadAllText(Path.Combine(output, "manifest.json"))).RootElement;
var modules = graph.GetProperty("Modules").EnumerateArray().ToDictionary(m => m.GetProperty("Id").GetString()!, m => m.GetProperty("Input").GetString()!);
foreach (string side in new[] { "A", "B" }) {
    var caller = modules.Single(m => m.Value.EndsWith("Valid" + side + ".dll")).Key;
    var edge = Lines("edges.jsonl").Single(e => e.GetProperty("From").GetString()!.StartsWith(caller + ":") && e.GetProperty("Kind").GetString() == "method");
    string target = edge.GetProperty("Target").GetProperty("PhysicalModule").GetString()!;
    if (target != Path.Combine(root, side, "Library.dll")) throw new Exception("Crossed physical compatibility context.");
}
var invalid = modules.Single(m => m.Value.EndsWith("InvalidA.dll")).Key;
if (Lines("edges.jsonl").Single(e => e.GetProperty("From").GetString()!.StartsWith(invalid + ":")).GetProperty("Target").GetProperty("Status").GetString() != "unresolved") throw new Exception("Wrong vendor signature was rebound.");
if (Lines("edges.jsonl").Count(e => e.GetProperty("Kind").GetString() == "field" && e.GetProperty("Target").GetProperty("Status").GetString() == "input") != 2) throw new Exception("Field edges missing.");
var source = Lines("source.jsonl").Single(e => e.GetProperty("Source").GetString() == "A/Sample.cs" && e.GetProperty("Kind").GetString() == "MethodDeclaration");
var bindings = source.GetProperty("Bindings").EnumerateArray().ToArray();
foreach (string name in new[] { "value", "count", "item", "failure", "text" }) if (!bindings.Any(b => b.GetProperty("Name").GetString() == name)) throw new Exception("Missing binding " + name);
string sourceText = File.ReadAllText(Path.Combine(root, "A/Sample.cs"));
foreach (var binding in bindings) if (sourceText.Substring(binding.GetProperty("Start").GetInt32(), binding.GetProperty("Length").GetInt32()) != binding.GetProperty("Name").GetString()) throw new Exception("Incorrect UTF16 source span.");
if (graph.GetProperty("RetainedBinaries").GetArrayLength() != 1) throw new Exception("Retained binary omitted.");
Console.WriteLine("PASS: physical contexts, wrong-scope unresolved edge, fields, foreach/catch/pattern/parameter bindings, UTF16 spans and retained binary coverage.");
IEnumerable<JsonElement> Lines(string file) => File.ReadLines(Path.Combine(output, file)).Select(l => JsonDocument.Parse(l).RootElement.Clone());
