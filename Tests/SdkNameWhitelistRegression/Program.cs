using System.Xml.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using dnSpy.Decompiler.MSBuild;

// Uses only synthetic fixtures created by the portable NameCandidates suite.
if (args.Length is < 1 or > 2) throw new ArgumentException("Supply the fixture sdk-whitelist directory and optionally its scoped-map.xml.");
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
if (args.Length == 2) {
    var scoped = XDocument.Load(args[1]);
    string scopedRoot = (string)scoped.Root.Attribute("InputDirectory");
    using var module = ModuleDefMD.Load(Path.Combine(scopedRoot, "Scoped.dll"));
    SourceNameMap.Apply(args[1], new[] { module });
    var alpha = module.Find("Example.Alpha/x", false);
    var beta = module.Find("Example.Beta/z", false);
    Require(alpha != null && beta != null && alpha.DeclaringType != beta.DeclaringType, "separate physical nested owners");
    Require(SourceNameAliases.Get(alpha) == "WorkState" && SourceNameAliases.Get(beta) == "WorkState",
        "dnSpy accepts the same nested alias in separate enclosing types");
    using var invalid = ModuleDefMD.Load(Path.Combine(scopedRoot, "Scoped.dll"));
    bool collisionRejected = false;
    try { SourceNameMap.Apply(Path.Combine(Path.GetDirectoryName(args[1]), "scoped-nested-invalid.xml"), new[] { invalid }); }
    catch (InvalidDataException ex) when (ex.Message.Contains("alias collision")) { collisionRejected = true; }
    Require(collisionRejected && invalid.GetTypes().All(t => SourceNameAliases.Get(t) == null),
        "same-owner collision rejected before registering any type aliases");
    // Identical assembly identities in separate physical deployments also have
    // independent top-level type scopes. Only synthetic fixture files are used.
    string compatFile = Path.Combine(scopedRoot, "compat", "Scoped.dll");
    Directory.CreateDirectory(Path.GetDirectoryName(compatFile));
    File.Copy(Path.Combine(scopedRoot, "Scoped.dll"), compatFile, overwrite: true);
    var compatibilityMap = new XDocument(scoped);
    var rootOwner = module.Find("Example.Alpha", false);
    var physical = compatibilityMap.Root.Element("Module");
    physical.Add(new XElement("Type", new XAttribute("Token", "0x" + rootOwner.MDToken.Raw.ToString("X8")),
        new XAttribute("ExpectedName", rootOwner.Name), new XAttribute("Signature", rootOwner.FullName),
        new XAttribute("NewName", "Example.RenamedOwner")));
    var second = new XElement(physical); second.SetAttributeValue("Path", "compat/Scoped.dll"); compatibilityMap.Root.Add(second);
    string compatibilityMapPath = Path.Combine(Path.GetDirectoryName(args[1]), "scoped-source-compatibility.xml");
    compatibilityMap.Save(compatibilityMapPath);
    using var firstCopy = ModuleDefMD.Load(Path.Combine(scopedRoot, "Scoped.dll"));
    using var secondCopy = ModuleDefMD.Load(compatFile);
    SourceNameMap.Apply(compatibilityMapPath, new[] { firstCopy, secondCopy });
    Require(SourceNameAliases.Get(firstCopy.Find("Example.Alpha", false)) != null &&
        SourceNameAliases.Get(firstCopy.Find("Example.Alpha", false)) == SourceNameAliases.Get(secondCopy.Find("Example.Alpha", false)),
        "same top-level alias accepted in separate same-identity physical modules");
    Console.WriteLine("PASS dnSpy nested type aliases retain distinct owners without suffixes.");
    Console.WriteLine("PASS dnSpy top-level type aliases retain independent physical compatibility modules.");
}
