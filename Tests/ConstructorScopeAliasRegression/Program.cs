using System.Xml.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using dnSpy.Decompiler.MSBuild;

// Consume the independently built NameCandidates constructor fixture through
// the actual dnSpy parser. No ETS exports/builds or input execution.
if (args.Length != 2 || Directory.Exists(args[1])) throw new ArgumentException("Supply constructor-scope/names.xml and a fresh report directory.");
var map = XDocument.Load(args[0]);
string input = (string)map.Root.Attribute("InputDirectory");
Directory.CreateDirectory(args[1]);
ModuleDefMD[] Load() => map.Root.Elements("Module").Select(r => ModuleDefMD.Load(Path.Combine(input, (string)r.Attribute("Path")))).ToArray();
void Require(bool value, string message) { if (!value) throw new Exception(message); }
var modules = Load();
try {
    SourceNameMap.Apply(args[0], modules);
    foreach (var row in map.Root.Elements("Module")) {
        var module = modules.Single(m => Guid.Parse((string)row.Attribute("Mvid")) == m.Mvid);
        foreach (var entry in row.Elements("Method")) {
            var method = (MethodDef)module.ResolveToken(Convert.ToUInt32(((string)entry.Attribute("Token"))[2..], 16));
            Require(method.IsConstructor && method.FullName == (string)entry.Attribute("Signature") &&
                SourceNameAliases.Get(method) == null && MetadataMethodNames.GetName(method) == method.Name, "constructor identity must remain unchanged");
            foreach (var alias in entry.Elements("Parameter")) {
                int sequence = (int)alias.Attribute("Sequence");
                var parameter = method.Parameters.Single(p => p.IsNormalMethodParameter && p.MethodSigIndex + 1 == sequence);
                Require(parameter.Name == (string)alias.Attribute("ExpectedName") && SourceNameAliases.GetParameter(parameter) == (string)alias.Attribute("NewName"), "physical constructor parameter alias");
            }
            foreach (var alias in entry.Elements("Local")) {
                var local = method.Body.Variables[(int)alias.Attribute("Index")];
                Require(local.Type.FullName == (string)alias.Attribute("ExpectedType") && SourceNameAliases.GetLocal(local) == (string)alias.Attribute("NewName"), "type initializer local alias");
            }
        }
        Require(MetadataMethodNames.GetMappings(module).Length == 0, "scope-only maps must not generate constructor name restoration");
    }
} finally { foreach (var module in modules) module.Dispose(); }
foreach (string invalid in new[] { "constructor-name", "initializer-name", "parameter-name", "local-type" }) {
    var bad = new XDocument(map);
    var methods = bad.Descendants("Method");
    if (invalid == "constructor-name") methods.First(m => (string)m.Attribute("ExpectedName") == ".ctor").SetAttributeValue("NewName", "CreatePacket");
    if (invalid == "initializer-name") methods.First(m => (string)m.Attribute("ExpectedName") == ".cctor").SetAttributeValue("NewName", "InitializePacket");
    if (invalid == "parameter-name") bad.Descendants("Parameter").First().SetAttributeValue("ExpectedName", "stale");
    if (invalid == "local-type") bad.Descendants("Local").First().SetAttributeValue("ExpectedType", "System.String");
    string path = Path.Combine(args[1], invalid + ".xml"); bad.Save(path);
    modules = Load(); bool rejected = false;
    try { SourceNameMap.Apply(path, modules); }
    catch (InvalidDataException) { rejected = true; }
    finally { foreach (var module in modules) module.Dispose(); }
    Require(rejected, "reject " + invalid);
}
Console.WriteLine("PASS constructor source-map aliases: separate physical copies, constructor parameters and type-initializer locals, unchanged constructor identities, rejected renames/stale metadata.");
