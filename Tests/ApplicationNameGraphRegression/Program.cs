using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Xml.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

if (args.Length != 2 && args.Length != 3) throw new ArgumentException("ApplicationNameGraphRegression <graph.dll> <fresh-directory> [reference-check.dll]");
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
    if (read.Assembly.Name == "Library") {
        var field = read.GetTypes().SelectMany(t => t.Fields).Single(f => f.Name == "c");
        names.Add(new XElement("Module", new XAttribute("Path", Path.GetRelativePath(root, file)), new XAttribute("Mvid", read.Mvid!),
            new XAttribute("Sha256", Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(file)))),
            new XElement("Field", new XAttribute("Token", "0x" + field.MDToken.Raw.ToString("X8")), new XAttribute("ExpectedName", "c"),
                new XAttribute("Signature", field.FullName), new XAttribute("NewName", "payload"))));
    }
}
ITypeDefOrRef Payload(ModuleDef m, string vendor) => new TypeRefUser(m, "Fixture", "Payload", new AssemblyRefUser(vendor, new Version(1, 0, 0, 0)));
foreach (string side in new[] { "A", "B" }) {
    var vendor = Module("Vendor" + side); Type(vendor, "Payload"); Save(vendor, "vendor" + side);
    var library = Module("Library"); var owner = Type(library, "Service");
    owner.Fields.Add(new FieldDefUser("b", new FieldSig(library.CorLibTypes.Int32), FieldAttributes.Public | FieldAttributes.Static));
    owner.Fields.Add(new FieldDefUser("c", new FieldSig(new ClassSig(Payload(library, "Vendor" + side))), FieldAttributes.Public | FieldAttributes.Static));
    var method = new MethodDefUser("a", MethodSig.CreateStatic(library.CorLibTypes.Int32, new ClassSig(Payload(library, "Vendor" + side))), MethodImplAttributes.IL, MethodAttributes.Public | MethodAttributes.Static) { Body = new CilBody() };
    method.Body.Instructions.Add(Instruction.Create(OpCodes.Ldsfld, owner.Fields[0])); method.Body.Instructions.Add(Instruction.Create(OpCodes.Ret)); owner.Methods.Add(method); Save(library, side);
    foreach (bool valid in side == "A" ? new[] { true, false } : new[] { true }) {
        var caller = Module((valid ? "Valid" : "Invalid") + side); var type = Type(caller, "Caller");
        var target = new TypeRefUser(caller, "Fixture", "Service", new AssemblyRefUser("Library", new Version(1, 0, 0, 0)));
        var reference = new MemberRefUser(caller, "a", MethodSig.CreateStatic(caller.CorLibTypes.Int32, new ClassSig(Payload(caller, "Vendor" + (valid ? side : "B")))), target);
        var run = new MethodDefUser("Run", MethodSig.CreateStatic(caller.CorLibTypes.Int32), MethodImplAttributes.IL, MethodAttributes.Public | MethodAttributes.Static) { Body = new CilBody() };
        run.Body.Instructions.Add(Instruction.Create(OpCodes.Ldsfld, new MemberRefUser(caller, "c", new FieldSig(new ClassSig(Payload(caller, "Vendor" + (valid ? side : "B")))), target)));
        run.Body.Instructions.Add(Instruction.Create(OpCodes.Pop));
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
if (Lines("edges.jsonl").Where(e => e.GetProperty("From").GetString()!.StartsWith(invalid + ":")).Any(e => e.GetProperty("Target").GetProperty("Status").GetString() != "unresolved")) throw new Exception("Wrong vendor signature was rebound.");
if (Lines("edges.jsonl").Count(e => e.GetProperty("Kind").GetString() == "field" && e.GetProperty("Target").GetProperty("Status").GetString() == "input") != 4) throw new Exception("Field edges missing.");
if (Lines("symbols.jsonl").Count(e => e.GetProperty("Kind").GetString() == "Field" && e.GetProperty("Alias").GetString() == "payload") != 2) throw new Exception("Mapped field alias missing.");
var source = Lines("source.jsonl").Single(e => e.GetProperty("Source").GetString() == "A/Sample.cs" && e.GetProperty("Kind").GetString() == "MethodDeclaration");
var bindings = source.GetProperty("Bindings").EnumerateArray().ToArray();
foreach (string name in new[] { "value", "count", "item", "failure", "text" }) if (!bindings.Any(b => b.GetProperty("Name").GetString() == name)) throw new Exception("Missing binding " + name);
string sourceText = File.ReadAllText(Path.Combine(root, "A/Sample.cs"));
foreach (var binding in bindings) if (sourceText.Substring(binding.GetProperty("Start").GetInt32(), binding.GetProperty("Length").GetInt32()) != binding.GetProperty("Name").GetString()) throw new Exception("Incorrect UTF16 source span.");
if (graph.GetProperty("RetainedBinaries").GetArrayLength() != 1) throw new Exception("Retained binary omitted.");
Console.WriteLine("PASS: physical contexts, wrong-scope unresolved edge, fields, foreach/catch/pattern/parameter bindings, UTF16 spans and retained binary coverage.");
if (args.Length == 3) {
    string inputs = Path.Combine(root, "inputs.json"), report = Path.Combine(root, "references.json");
    File.WriteAllText(inputs, JsonSerializer.Serialize(manifest.Elements("Project").Select(p => (string)p.Attribute("Source")!).ToArray()));
    var check = new ProcessStartInfo("dotnet") { UseShellExecute = false };
    foreach (var arg in new[] { Path.GetFullPath(args[2]), inputs, namesFile, report, "--no-gac", "--asm-path", Path.Combine(root, "vendorA"), "--asm-path", Path.Combine(root, "vendorB") }) check.ArgumentList.Add(arg);
    using (var process = Process.Start(check)!) { process.WaitForExit(); if (process.ExitCode != 1) throw new Exception("Field preflight must report the invalid vendor reference."); }
    var checkedReferences = JsonDocument.Parse(File.ReadAllText(report)).RootElement;
    if (checkedReferences.GetProperty("IssueCount").GetInt32() != 1 || checkedReferences.GetProperty("ResolvedFieldAliasReferences").GetInt32() != 2 ||
        !checkedReferences.GetProperty("Issues")[0].GetProperty("Module").GetString()!.EndsWith("InvalidA.dll")) throw new Exception("Field alias preflight lost physical identity or missed the wrong signature.");
    Console.WriteLine("PASS: field alias reference preflight accepts distinct physical consumers and rejects a wrong-vendor signature.");
}
IEnumerable<JsonElement> Lines(string file) => File.ReadLines(Path.Combine(output, file)).Select(l => JsonDocument.Parse(l).RootElement.Clone());
