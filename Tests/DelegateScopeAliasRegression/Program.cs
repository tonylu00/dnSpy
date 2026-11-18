using System.Xml.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;
using dnSpy.Decompiler.MSBuild;

if (args.Length != 2 || Directory.Exists(args[1])) throw new ArgumentException("Supply delegate-scope/names.xml and a fresh report directory.");
var map = XDocument.Load(args[0]);
string input = (string)map.Root.Attribute("InputDirectory");
Directory.CreateDirectory(args[1]);
ModuleDefMD Load() => ModuleDefMD.Load(Path.Combine(input, "Delegates.dll"));
using (var module = Load()) {
    SourceNameMap.Apply(args[0], new[] { module });
    var method = module.GetTypes().SelectMany(t => t.Methods).Single(m => m.Name == "Invoke");
    var parameter = method.Parameters.Single(p => p.IsNormalMethodParameter);
    if (!method.IsRuntime || !method.IsVirtual || method.HasBody || SourceNameAliases.Get(method) != null ||
        parameter.Name != "a" || SourceNameAliases.GetParameter(parameter) != "candidateValue" ||
        MetadataMethodNames.GetMappings(module).Length != 0)
        throw new Exception("Runtime slot and original parameter metadata must remain intact while the source alias is readable.");
}
foreach (string invalid in new[] { "rename", "parameter", "local" }) {
    var bad = new XDocument(map);
    var method = bad.Descendants("Method").Single();
    if (invalid == "rename") method.SetAttributeValue("NewName", "RunCallback");
    if (invalid == "parameter") method.Element("Parameter").SetAttributeValue("ExpectedName", "stale");
    if (invalid == "local") method.Add(new XElement("Local", new XAttribute("Index", 0), new XAttribute("ExpectedType", "System.Int32"), new XAttribute("NewName", "candidateValue")));
    string path = Path.Combine(args[1], invalid + ".xml"); bad.Save(path);
    using var module = Load(); bool rejected = false;
    try { SourceNameMap.Apply(path, new[] { module }); } catch (InvalidDataException) { rejected = true; }
    if (!rejected) throw new Exception("Reject " + invalid);
}
Console.WriteLine("PASS actual dnSpy parser: readable delegate parameter alias, preserved runtime slot, rejected renames/stale metadata/locals.");
