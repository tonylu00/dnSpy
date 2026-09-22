using System.Xml.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using dnSpy.Decompiler.MSBuild;

// Uses only synthetic fixtures created by the portable NameCandidates suite.
if (args.Length != 1) throw new ArgumentException("Supply the fixture sdk-whitelist directory.");
var map = XDocument.Load(Path.Combine(args[0], "protected.xml"));
string input = (string)map.Root.Attribute("InputDirectory");
ModuleDefMD[] Load() => Directory.EnumerateFiles(input, "*.dll", SearchOption.AllDirectories).Select(path => ModuleDefMD.Load(path)).ToArray();
void Require(bool condition, string message) { if (!condition) throw new Exception(message); }
var modules = Load();
try {
    SourceNameMap.Apply(Path.Combine(args[0], "protected.xml"), modules);
    var sdk = modules.Single(m => m.Name == "Sdk.dll");
    var helper = sdk.GetTypes().SelectMany(t => t.Methods).Single(m => m.Name == "a");
    var api = sdk.GetTypes().SelectMany(t => t.Methods).Single(m => m.Name == "GetCount");
    Require(SourceNameAliases.Get(helper) == "ComputeCount", "private SDK helper source alias accepted");
    Require(SourceNameAliases.Get(api) == null && SourceNameAliases.GetParameter(api.Parameters.Single(p => p.IsNormalMethodParameter)) == null,
        "SDK name and parameter remain unchanged");
    var compatibility = modules.Single(m => m.Name == "Model.dll" && Path.GetFileName(Path.GetDirectoryName(m.Location)) == "compat");
    Require(SourceNameAliases.Get(compatibility.GetTypes().SelectMany(t => t.Methods).Single(m => m.Name == "ReadValue")) == "ReadAlternateValue",
        "independent compatibility copy stays editable");
} finally { foreach (var module in modules) module.Dispose(); }
modules = Load();
try {
    bool rejected = false;
    try { SourceNameMap.Apply(Path.Combine(args[0], "invalid.xml"), modules); }
    catch (InvalidDataException ex) when (ex.Message.Contains("SDK whitelist")) { rejected = true; }
    Require(rejected, "dnSpy must reject protected aliases even without a prior preflight");
    Require(modules.SelectMany(m => m.GetTypes()).SelectMany(t => t.Methods).All(m => SourceNameAliases.Get(m) == null),
        "invalid map rejected before any source aliases are registered");
} finally { foreach (var module in modules) module.Dispose(); }
Console.WriteLine("PASS dnSpy SDK whitelist: private helper/physical compatibility aliases accepted, SDK public name and parameter retained, invalid map rejected before mutation.");
