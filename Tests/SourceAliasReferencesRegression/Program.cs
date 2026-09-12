using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Xml.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

if (args.Length != 2) throw new ArgumentException("Usage: SourceAliasReferencesRegression <preflight.dll> <new-work-directory>");
var tool = Path.GetFullPath(args[0]);
var root = Path.GetFullPath(args[1]);
if (Directory.Exists(root)) throw new IOException("Choose a new work directory.");
Directory.CreateDirectory(root);
ModuleDefUser NewModule(string assemblyName, string directory) {
    Directory.CreateDirectory(directory);
    var module = new ModuleDefUser(assemblyName + ".dll") { Kind = ModuleKind.Dll, Mvid = Guid.NewGuid() };
    new AssemblyDefUser(assemblyName, new Version(1, 0, 0, 0)).Modules.Add(module);
    return module;
}
TypeDef AddType(ModuleDef module, string name) {
    var type = new TypeDefUser("Example", name, module.CorLibTypes.Object.TypeDefOrRef) { Attributes = TypeAttributes.Public };
    module.Types.Add(type); return type;
}
string Write(ModuleDef module, string directory) { var path = Path.Combine(directory, module.Name); module.Write(path); return path; }
var vendorA = NewModule("VendorA", root); AddType(vendorA, "Payload");
var vendorB = NewModule("VendorB", root); AddType(vendorB, "Payload");
var aPath = Write(vendorA, root); var bPath = Write(vendorB, root);
ITypeDefOrRef Payload(ModuleDef module, string vendor) => new TypeRefUser(module, "Example", "Payload", new AssemblyRefUser(vendor, new Version(1, 0, 0, 0)));
string Library(string directory, string vendor) {
    var module = NewModule("Library", directory);
    var owner = AddType(module, "Service");
    var method = new MethodDefUser("a", MethodSig.CreateStatic(module.CorLibTypes.Int32, new ClassSig(Payload(module, vendor))), MethodImplAttributes.IL, MethodAttributes.Public | MethodAttributes.Static);
    method.Body = new CilBody(); method.Body.Instructions.Add(Instruction.CreateLdcI4(1)); method.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
    owner.Methods.Add(method); return Write(module, directory);
}
string Caller(string directory, string name, string vendor) {
    var module = NewModule(name, directory);
    var owner = AddType(module, "Caller");
    var target = new TypeRefUser(module, "Example", "Service", new AssemblyRefUser("Library", new Version(1, 0, 0, 0)));
    var reference = new MemberRefUser(module, "a", MethodSig.CreateStatic(module.CorLibTypes.Int32, new ClassSig(Payload(module, vendor))), target);
    var method = new MethodDefUser("Run", MethodSig.CreateStatic(module.CorLibTypes.Int32), MethodImplAttributes.IL, MethodAttributes.Public | MethodAttributes.Static);
    method.Body = new CilBody(); method.Body.Instructions.Add(Instruction.Create(OpCodes.Ldnull)); method.Body.Instructions.Add(Instruction.Create(OpCodes.Call, reference)); method.Body.Instructions.Add(Instruction.Create(OpCodes.Ret));
    owner.Methods.Add(method); return Write(module, directory);
}
var folderA = Path.Combine(root, "a"); var folderB = Path.Combine(root, "b");
var libA = Library(folderA, "VendorA"); var libB = Library(folderB, "VendorB");
var validA = Caller(folderA, "ValidA", "VendorA"); var validB = Caller(folderB, "ValidB", "VendorB");
var invalidA = Caller(folderA, "InvalidA", "VendorB");
var map = new XElement("SourceNameMap", new XAttribute("Version", "1"), new XAttribute("InputDirectory", root));
foreach (var path in new[] { libA, libB }) {
    using var module = ModuleDefMD.Load(path);
    var method = module.GetTypes().Single(t => t.Name == "Service").Methods.Single();
    map.Add(new XElement("Module", new XAttribute("Path", Path.GetRelativePath(root, path)), new XAttribute("Mvid", module.Mvid!),
        new XAttribute("Sha256", Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)))),
        new XElement("Method", new XAttribute("Token", "0x" + method.MDToken.Raw.ToString("X8")), new XAttribute("ExpectedName", "a"),
            new XAttribute("Signature", method.FullName), new XAttribute("NewName", "ConsumePayload"))));
}
var mapPath = Path.Combine(root, "names.xml"); new XDocument(map).Save(mapPath);
void Run(string name, string[] callers, int expectedIssues, int expectedResolved) {
    var inputs = Path.Combine(root, name + "-inputs.json"); var report = Path.Combine(root, name + ".json");
    File.WriteAllText(inputs, JsonSerializer.Serialize(new[] { aPath, bPath, libA, libB }.Concat(callers)));
    var info = new ProcessStartInfo("dotnet") { UseShellExecute = false };
    foreach (var arg in new[] { tool, inputs, mapPath, report, "--no-gac" }) info.ArgumentList.Add(arg);
    using var process = Process.Start(info)!; process.WaitForExit();
    using var result = JsonDocument.Parse(File.ReadAllText(report));
    if (process.ExitCode != (expectedIssues == 0 ? 0 : 1) || result.RootElement.GetProperty("IssueCount").GetInt32() != expectedIssues ||
        result.RootElement.GetProperty("ResolvedAliasReferences").GetInt32() != expectedResolved) throw new Exception("Unexpected preflight result: " + name);
}
Run("same-identities-separate-deployments", new[] { validA, validB }, 0, 2);
Run("wrong-vendor-scope", new[] { invalidA }, 1, 0);
Console.WriteLine("PASS: exact physical duplicate deployments remain separate; same-named vendor types are not substituted.");
// Two disjoint deployments use identically named global aliases. Only one
// consumer also imports an existing namespaced type with that simple name.
var aliasRoot = Path.Combine(root, "global-alias");
var globalPaths = new List<string>();
foreach (var side in new[] { "a", "b" }) {
    string directory = Path.Combine(aliasRoot, side);
    var library = NewModule("GlobalLibrary", directory);
    var globalType = AddType(library, "a"); globalType.Namespace = "";
    globalPaths.Add(Write(library, directory));
    var consumer = NewModule("Consumer" + side, directory);
    var consumerType = AddType(consumer, "Consumer");
    consumerType.Fields.Add(new FieldDefUser("Aliased", new FieldSig(new ClassSig(new TypeRefUser(consumer, "", "a",
        new AssemblyRefUser("GlobalLibrary", new Version(1, 0, 0, 0))))), FieldAttributes.Public));
    if (side == "a") consumerType.Fields.Add(new FieldDefUser("Original", new FieldSig(new ClassSig(Payload(consumer, "VendorA"))), FieldAttributes.Public));
    globalPaths.Add(Write(consumer, directory));
}
var globalMap = new XElement("SourceNameMap", new XAttribute("Version", "1"), new XAttribute("InputDirectory", root));
foreach (var path in globalPaths.Where(p => Path.GetFileName(p) == "GlobalLibrary.dll")) {
    using var module = ModuleDefMD.Load(path);
    var type = module.Types.Single(t => t.Name == "a");
    globalMap.Add(new XElement("Module", new XAttribute("Path", Path.GetRelativePath(root, path)), new XAttribute("Mvid", module.Mvid!),
        new XAttribute("Sha256", Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)))),
        new XElement("Type", new XAttribute("Token", "0x" + type.MDToken.Raw.ToString("X8")), new XAttribute("ExpectedName", "a"),
            new XAttribute("Signature", type.FullName), new XAttribute("NewName", "Payload"))));
}
var globalMapPath = Path.Combine(root, "global-names.xml");
var globalInputs = Path.Combine(root, "global-inputs.json");
File.WriteAllText(globalInputs, JsonSerializer.Serialize(globalPaths.Append(aPath)));
void RunGlobal(string name, int expectedIssues) {
    new XDocument(globalMap).Save(globalMapPath);
    var report = Path.Combine(root, name + ".json");
    var info = new ProcessStartInfo("dotnet") { UseShellExecute = false };
    foreach (var arg in new[] { tool, globalInputs, globalMapPath, report, "--no-gac" }) info.ArgumentList.Add(arg);
    using var process = Process.Start(info)!; process.WaitForExit();
    using var result = JsonDocument.Parse(File.ReadAllText(report));
    if (process.ExitCode != (expectedIssues == 0 ? 0 : 1) || result.RootElement.GetProperty("IssueCount").GetInt32() != expectedIssues)
        throw new Exception("Unexpected global-alias result: " + name);
    if (name == "global-type-shadow") {
        var issue = result.RootElement.GetProperty("Issues")[0];
        if (issue.GetProperty("Module").GetString() != globalPaths[1] || issue.GetProperty("AliasModule").GetString() != globalPaths[0])
            throw new Exception("Global alias collision leaked into the other deployment.");
    }
}
RunGlobal("global-type-shadow", 1);
foreach (var type in globalMap.Descendants("Type")) type.SetAttributeValue("NewName", "GlobalLibraryPayload");
RunGlobal("distinct-global-alias", 0);
globalMap.Descendants("Type").First().SetAttributeValue("Signature", "stale");
RunGlobal("stale-type-alias", 1);
Console.WriteLine("PASS: global type shadowing detected before export; distinct aliases and disjoint duplicate deployments pass; stale type rows rejected.");
