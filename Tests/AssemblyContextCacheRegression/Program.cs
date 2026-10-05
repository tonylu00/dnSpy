using System.Security.Cryptography;
using System.Xml.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
using dnSpy_Console;

if (args.Length != 1 || Directory.Exists(args[0])) throw new ArgumentException("Supply a fresh fixture directory.");
string root = Path.GetFullPath(args[0]); Directory.CreateDirectory(root);
int checks = 0;
void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
string Write(string directory, string name, int value, int version = 1) {
    Directory.CreateDirectory(directory);
    string path = Path.Combine(directory, name + ".dll");
    using var module = new ModuleDefUser(name + ".dll") { Kind = ModuleKind.Dll, Mvid = new Guid("aaaaaaaa-0000-0000-0000-000000000001") };
    new AssemblyDefUser(name, new Version(version, 0, 0, 0)).Modules.Add(module);
    var type = new TypeDefUser("", "Value", module.CorLibTypes.Object.TypeDefOrRef); module.Types.Add(type);
    var method = new MethodDefUser("Read", MethodSig.CreateStatic(module.CorLibTypes.Int32), MethodImplAttributes.IL, MethodAttributes.Public | MethodAttributes.Static) { Body = new CilBody() };
    method.Body.Instructions.Add(Instruction.Create(OpCodes.Ldc_I4, value)); method.Body.Instructions.Add(Instruction.Create(OpCodes.Ret)); type.Methods.Add(method);
    module.Write(path); return path;
}
string host = Path.Combine(root, "host"), compat = Path.Combine(root, "compat"), support = Path.Combine(root, "support");
string hostLibrary = Write(host, "Shared.Contract", 11), compatLibrary = Write(compat, "Shared.Contract", 22);
string hostLeaf = Write(host, "Shared.Leaf", 33), compatLeaf = Write(compat, "Shared.Leaf", 44);
string newerLibrary = Write(support, "Shared.Contract", 55, 2);
string[] files = Enumerable.Range(0, 5).Select(i => Write(i == 2 ? compat : host, "Input" + i, i)).ToArray();
string config = Path.Combine(root, "redirect.config");
File.WriteAllText(config, "<configuration><runtime><assemblyBinding xmlns='urn:schemas-microsoft-com:asm.v1'><dependentAssembly><assemblyIdentity name='Shared.Contract' publicKeyToken='null' culture='neutral'/><bindingRedirect oldVersion='1.0.0.0' newVersion='2.0.0.0'/></dependentAssembly></assemblyBinding></runtime></configuration>");
string separateConfig = Path.Combine(root, "separate.config"); File.WriteAllText(separateConfig, "<configuration/>");
var doc = new XElement("AssemblyContexts", files.Select((f, i) => new XElement("Context", new XAttribute("Source", f), new XAttribute("Directory", i == 2 ? compat : host), i is 3 or 4 ? new XAttribute("Config", i == 3 ? config : separateConfig) : null)));
string manifest = Path.Combine(root, "contexts.xml"); doc.Save(manifest);
var pins = files.Concat(new[] { hostLibrary, compatLibrary, hostLeaf, compatLeaf, newerLibrary }).ToDictionary(p => p, p => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(p))));
// Include the libraries as exported definitions, just as the full application
// export does. The same physical library under a different config must still
// remain a separately loaded dependency graph.
foreach (string library in new[] { hostLibrary, compatLibrary, hostLeaf, compatLeaf })
    doc.Add(new XElement("Context", new XAttribute("Source", library), new XAttribute("Directory", Path.GetDirectoryName(library))));
doc.Save(manifest);
var inputs = files.Concat(new[] { hostLibrary, compatLibrary, hostLeaf, compatLeaf }).Select(path => ModuleDefMD.Load(path)).ToArray();
try {
    var fallback = new EmptyResolver();
    var resolver = new AssemblyContextResolver(fallback, manifest, inputs, false, new[] { support });
    var contract = new AssemblyNameInfo("Shared.Contract, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null");
    var leaf = new AssemblyNameInfo("Shared.Leaf, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null");
    var first = resolver.Resolve(contract, inputs[0]);
    var second = resolver.Resolve(contract, inputs[1]);
    var twin = resolver.Resolve(contract, inputs[2]);
    Check(ReferenceEquals(first, second), "Inputs with the same directory/config must share one loaded graph.");
    Check(ReferenceEquals(first, inputs[5].Assembly) && ReferenceEquals(twin, inputs[6].Assembly), "Bind source aliases to the exact exported library definitions in each physical context.");
    Check(first.FullNameToken == twin.FullNameToken && first.ManifestModule.Mvid == twin.ManifestModule.Mvid, "Fixture must contain identity/MVID twins.");
    Check(!ReferenceEquals(first, twin) && first.ManifestModule.Location == hostLibrary && twin.ManifestModule.Location == compatLibrary, "Keep distinct compatibility paths even with equal identities/MVIDs.");
    int Value(AssemblyDef a) => (int)a.ManifestModule.GetTypes().Single(t => t.Name == "Value").Methods.Single(m => m.Name == "Read").Body.Instructions[0].Operand;
    Check(Value(first) == 11 && Value(twin) == 22, "Physical implementations must retain distinct behavior.");
    var redirected = resolver.Resolve(contract, inputs[3]);
    Check(redirected.Version == new Version(2, 0, 0, 0) && redirected.ManifestModule.Location == newerLibrary && Value(redirected) == 55, "Separate configuration retains its binding redirect.");
    var configured = resolver.Resolve(contract, inputs[4]);
    Check(configured.FullNameToken == first.FullNameToken && !ReferenceEquals(configured, first), "Different explicit configuration paths must remain isolated.");
    Check(ReferenceEquals(resolver.Resolve(contract, first.ManifestModule), first), "Nested same-assembly requests retain the source context cache.");
    Check(resolver.Resolve(leaf, first.ManifestModule).ManifestModule.Location == hostLeaf && resolver.Resolve(leaf, twin.ManifestModule).ManifestModule.Location == compatLeaf, "Nested dependency closure must follow each physical context.");
    foreach (var input in inputs) Check(ReferenceEquals(resolver.Resolve(input.Assembly, input), input.Assembly), "Own input must stay the original exported module.");
    Check(resolver.Resolve(new AssemblyNameInfo("Missing, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null"), inputs[0]) == null && fallback.Calls == 0, "Explicit-context misses must not fall through to host fallback.");
    resolver.Resolve(contract, null); Check(fallback.Calls == 1, "Unscoped queries retain fallback behavior.");
    Parallel.For(0, 200, i => { if (!ReferenceEquals(resolver.Resolve(contract, inputs[i % 2]), first)) throw new Exception("Concurrent queries duplicated or merged the graph."); });
    Check(true, "200 parallel same-context resolutions completed.");
    foreach (string invalid in new[] { "duplicate", "missing-source", "missing-directory", "missing-config" }) {
        var bad = new XElement(doc);
        if (invalid == "duplicate") bad.Add(new XElement(bad.Elements().First()));
        if (invalid == "missing-source") bad.Elements().First().SetAttributeValue("Source", newerLibrary);
        if (invalid == "missing-directory") bad.Elements().First().SetAttributeValue("Directory", Path.Combine(root, "absent"));
        if (invalid == "missing-config") bad.Elements().First().SetAttributeValue("Config", Path.Combine(root, "absent.config"));
        string path = Path.Combine(root, invalid + ".xml"); bad.Save(path);
        bool rejected = false;
        try { new AssemblyContextResolver(fallback, path, inputs, false, new[] { support }); }
        catch (Exception ex) when (ex is ErrorException or IOException) { rejected = true; }
        Check(rejected, "Retain context validation: " + invalid);
    }
    Check(pins.All(pin => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(pin.Key))) == pin.Value), "Inspection must preserve every input binary.");
} finally { foreach (var module in inputs) module.Dispose(); }
Console.WriteLine($"PASS: {checks} physical/context/cache/redirect guards; 200 concurrent resolutions.");

namespace dnSpy_Console {
    sealed class ErrorException : Exception { public ErrorException(string text) : base(text) { } }
    sealed class EmptyResolver : IAssemblyResolver {
        public int Calls;
        public AssemblyDef Resolve(IAssembly assembly, ModuleDef source) { Calls++; return null; }
    }
}
