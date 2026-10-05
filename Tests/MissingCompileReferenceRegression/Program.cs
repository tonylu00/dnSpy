using System.Reflection;
using System.Security.Cryptography;
using System.Xml.Linq;
using dnlib.DotNet;
using dnSpy.Decompiler.MSBuild;

string root = Path.GetFullPath(args[0]);
if (Directory.Exists(root)) throw new IOException("Choose a fresh fixture directory.");
Directory.CreateDirectory(root);
int checks = 0;
void Check(bool value, string message) { checks++; if (!value) throw new Exception(message); }
byte[] key = typeof(object).Assembly.GetName().GetPublicKey();
string Asset(string folder, int version = 7, byte[] signingKey = null, string culture = "") {
    string path = Path.Combine(root, folder, "Legacy.Contract.dll");
    Directory.CreateDirectory(Path.GetDirectoryName(path));
    using var module = new ModuleDefUser("Legacy.Contract.dll") { Kind = ModuleKind.Dll, Mvid = Guid.NewGuid() };
    new AssemblyDefUser("Legacy.Contract", new Version(version, 0, 0, 0), new PublicKey(signingKey ?? key), culture).Modules.Add(module);
    module.Write(path); return path;
}
string target = Asset("good");
string identity = AssemblyName.GetAssemblyName(target).FullName;
string source = Path.Combine(root, "Original.dll");
Guid mvid = Guid.NewGuid();
using (var module = new ModuleDefUser("Original.dll") { Kind = ModuleKind.Dll, Mvid = mvid }) {
    new AssemblyDefUser("Original", new Version(1,0,0,0)).Modules.Add(module);
    var type = new TypeDefUser("Test", "Owner", module.CorLibTypes.Object.TypeDefOrRef); module.Types.Add(type);
    type.Fields.Add(new FieldDefUser("Contract", new FieldSig(new ClassSig(new TypeRefUser(module, "Test", "Contract", new AssemblyRefUser(new AssemblyNameInfo(identity)))))));
    module.Write(source);
}
string Snapshot(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
string originalHash = Snapshot(source), targetHash = Snapshot(target);
string Export(string name, string extra = "", bool legacy = false) {
    string export = Path.Combine(root, name); Directory.CreateDirectory(export);
    string project = Path.Combine(export, "Original.csproj");
    XNamespace ns = legacy ? "http://schemas.microsoft.com/developer/msbuild/2003" : "";
    new XDocument(new XElement(ns + "Project", new XElement(ns + "ItemGroup", new XElement(ns + "Reference", new XAttribute("Include", "Legacy.Contract")),
        new XElement(ns + "Reference", new XAttribute("Include", "Unknown.Contract")), new XElement(ns + "Reference", new XAttribute("Include", "Pinned.Contract"), new XElement(ns + "HintPath", "untouched.dll")),
        new XElement(ns + "ProjectReference", new XAttribute("Include", "untouched.csproj"))))).Save(project);
    if (extra != "") File.WriteAllText(Path.Combine(export, "Unlisted.csproj"), extra);
    File.WriteAllText(Path.Combine(export, "Owner.cs"), "Original application source");
    new XDocument(new XElement("DnSpyExportMap", new XAttribute("Version", 1), new XAttribute("ExportErrors", 0), new XElement("Project",
        new XAttribute("Source", source), new XAttribute("Project", "Original.csproj"), new XAttribute("AssemblyName", "Original"), new XAttribute("Mvid", mvid)))).Save(Path.Combine(export,"dnspy-export-map.xml"));
    return export;
}
foreach (bool legacy in new[] { false, true }) {
    string export = Export("valid" + legacy, "Unlisted must remain unchanged", legacy);
    var result = MissingCompileReferenceResolver.Resolve(export, new[] { Path.GetDirectoryName(target) });
    Check(result.Count == 1, "Wrong resolution scope");
    Check(result[0].Identity == identity && result[0].SourceHash == originalHash && result[0].TargetHash == targetHash, "Missing physical identity proof");
    var project = XDocument.Load(Path.Combine(export,"Original.csproj")); XNamespace ns = project.Root.Name.Namespace;
    var reference = project.Descendants(ns+"Reference").Single(r => (string)r.Attribute("Include") == identity);
    Check(reference.Element(ns+"HintPath").Value == target && reference.Element(ns+"SpecificVersion").Value == "true", "Exact reference not emitted");
    Check(project.Descendants(ns+"DnSpyPreservedCompileReference").Single().Attribute("Include").Value == target, "Package conflict guard missing");
    Check(project.Descendants(ns+"ProjectReference").Single().Attribute("Include").Value == "untouched.csproj", "Project reference changed");
    Check(File.ReadAllText(Path.Combine(export,"Unlisted.csproj")) == "Unlisted must remain unchanged" && File.ReadAllText(Path.Combine(export,"Owner.cs")) == "Original application source", "Unrelated files changed");
    string before = Snapshot(Path.Combine(export,"Original.csproj"));
    Check(MissingCompileReferenceResolver.Resolve(export, new[]{Path.GetDirectoryName(target)}).Count == 0 && Snapshot(Path.Combine(export,"Original.csproj")) == before, "Not idempotent");
}
foreach (var bad in new[]{ Asset("wrong-version", version:8), Asset("wrong-key", signingKey: typeof(ModuleDef).Assembly.GetName().GetPublicKey()), Asset("unsigned", signingKey:Array.Empty<byte>()), Asset("culture", culture:"fr") }) {
    string export = Export("rejected" + checks); string before = Snapshot(Path.Combine(export,"Original.csproj"));
    Check(MissingCompileReferenceResolver.Resolve(export,new[]{Path.GetDirectoryName(bad)}).Count == 0, "Inexact identity accepted");
    Check(Snapshot(Path.Combine(export,"Original.csproj")) == before, "Unresolved project mutated");
}
string duplicate = Asset("duplicate");
void Reject(string export, string[] dirs, string message) {
    string before = Snapshot(Path.Combine(export,"Original.csproj"));
    try { MissingCompileReferenceResolver.Resolve(export,dirs); throw new Exception(message); }
    catch (InvalidDataException) { Check(Snapshot(Path.Combine(export,"Original.csproj")) == before,"Rejected project mutated: " + message); }
}
Reject(Export("ambiguous"),new[]{Path.GetDirectoryName(target),Path.GetDirectoryName(duplicate)},"Distinct physical candidates accepted");
foreach (string path in new[]{"../Outside.csproj","obj/Original.csproj","Original_wpftmp.csproj"}) {
    string export = Export("bad-path"+checks); var map = XDocument.Load(Path.Combine(export,"dnspy-export-map.xml")); map.Root.Element("Project").SetAttributeValue("Project",path); map.Save(Path.Combine(export,"dnspy-export-map.xml"));
    Reject(export,new[]{Path.GetDirectoryName(target)},"Invalid export path accepted");
}
{
    string export = Export("changed-mvid"); var map = XDocument.Load(Path.Combine(export,"dnspy-export-map.xml")); map.Root.Element("Project").SetAttributeValue("Mvid",Guid.NewGuid()); map.Save(Path.Combine(export,"dnspy-export-map.xml"));
    Reject(export,new[]{Path.GetDirectoryName(target)},"Changed original module accepted");
}
Check(Snapshot(source)==originalHash && Snapshot(target)==targetHash,"Original or candidate binary changed");
Console.WriteLine("PASS: " + checks + " exact compile-reference identity, scope, ambiguity and preservation checks.");
