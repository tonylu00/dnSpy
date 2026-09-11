using System.Security.Cryptography;
using System.Text.Json;
using System.Xml.Linq;
using dnlib.DotNet;

// Metadata-only verification: no exported or input assembly is executed.
if (args.Length != 2) {
    Console.Error.WriteLine("Usage: SourceAliasContracts <built-export-directory> <new-report.json>");
    return 2;
}
var issues = new List<string>();
int modules = 0, types = 0, methods = 0, parameters = 0;
var pathComparer = OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal;
string Full(string root, string relative) => Path.GetFullPath(Path.Combine(root, relative.Replace('/', Path.DirectorySeparatorChar)));
string Required(XElement element, string name) => (string)element.Attribute(name) ?? throw new InvalidDataException($"Missing {name}");
bool SameBytes(UTF8String a, UTF8String b) => (a?.Data ?? Array.Empty<byte>()).SequenceEqual(b?.Data ?? Array.Empty<byte>());
bool SameTypeNames(TypeDef a, TypeDef b) => a == null || b == null ? a == b :
    SameBytes(a.Name, b.Name) && SameBytes(a.Namespace, b.Namespace) && SameTypeNames(a.DeclaringType, b.DeclaringType);
try {
    if (File.Exists(args[1])) throw new IOException("Choose a new report path.");
    var export = Path.GetFullPath(args[0]);
    var names = XDocument.Load(Path.Combine(export, "dnspy-source-name-map.xml")).Root;
    var projects = XDocument.Load(Path.Combine(export, "dnspy-export-map.xml")).Root;
    if (names?.Name != "SourceNameMap" || (string)names.Attribute("Version") != "1" ||
        projects?.Name != "DnSpyExportMap" || (string)projects.Attribute("ExportErrors") != "0")
        throw new InvalidDataException("Expected a successful export with a version 1 source-name map.");
    foreach (var row in names.Elements("Module")) {
        var input = Full(Required(names, "InputDirectory"), Required(row, "Path"));
        var matches = projects.Elements("Project").Where(p => pathComparer.Equals(Path.GetFullPath(Required(p, "Source")), input)).ToArray();
        if (matches.Length != 1) throw new InvalidDataException($"Expected one physical project for {input}");
        var project = Full(export, Required(matches[0], "Project"));
        var settings = XDocument.Load(project);
        string Setting(string name) => settings.Descendants().First(e => e.Name.LocalName == name).Value;
        var name = Setting("AssemblyName") + (Setting("OutputType") == "Library" ? ".dll" : ".exe");
        var suffix = Path.Combine("Release", Setting("TargetFramework"), name);
        var bin = Path.Combine(Path.GetDirectoryName(project), "bin");
        var binaries = Directory.GetFiles(bin, name, SearchOption.AllDirectories)
            .Where(p => p.EndsWith(suffix, OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal)).ToArray();
        if (binaries.Length != 1) throw new InvalidDataException($"Expected one Release binary for {project}; found {binaries.Length}");
        var bytes = File.ReadAllBytes(input);
        if (!StringComparer.OrdinalIgnoreCase.Equals(Convert.ToHexString(SHA256.HashData(bytes)), Required(row, "Sha256")))
            throw new InvalidDataException($"Stale map hash: {input}");
        using var before = ModuleDefMD.Load(bytes);
        using var after = ModuleDefMD.Load(binaries[0]);
        if (!Guid.TryParse(Required(row, "Mvid"), out var mvid) || before.Mvid != mvid)
            throw new InvalidDataException($"Stale map MVID: {input}");
        modules++;
        var outputTypes = after.GetTypes().ToArray();
        var outputMethods = outputTypes.SelectMany(t => t.Methods).GroupBy(m => m.FullName)
            .ToDictionary(g => g.Key, g => g.ToArray(), StringComparer.Ordinal);
        foreach (var entry in row.Elements()) {
            var token = Convert.ToUInt32(Required(entry, "Token").Substring(2), 16);
            var original = before.ResolveToken(token) as IMemberDef;
            if (original == null || original.Name.String != Required(entry, "ExpectedName") || original.FullName != Required(entry, "Signature"))
                throw new InvalidDataException($"Stale member: {input} {token:X8}");
            if (entry.Name == "Type") {
                types++;
                var restored = outputTypes.Where(t => t.FullName == original.FullName).ToArray();
                if (restored.Length != 1 || !SameTypeNames((TypeDef)original, restored[0]))
                    issues.Add($"{input} {token:X8}: original type name missing or ambiguous");
            }
            else if (entry.Name == "Method") {
                methods++;
                if (!outputMethods.TryGetValue(original.FullName, out var restored) || restored.Length != 1 ||
                    !SameBytes(original.Name, restored[0].Name) || !SameTypeNames(original.DeclaringType, restored[0].DeclaringType)) {
                    issues.Add($"{input} {token:X8}: original method name/signature missing or ambiguous");
                    continue;
                }
                foreach (var parameter in entry.Elements("Parameter")) {
                    parameters++;
                    var sequence = ushort.Parse(Required(parameter, "Sequence"));
                    var expected = ((MethodDef)original).ParamDefs.Single(p => p.Sequence == sequence);
                    if (expected.Name.String != Required(parameter, "ExpectedName"))
                        throw new InvalidDataException($"Stale parameter: {input} {token:X8}/{sequence}");
                    var found = restored[0].ParamDefs.Where(p => p.Sequence == sequence).ToArray();
                    if (found.Length != 1 || !SameBytes(found[0].Name, expected.Name))
                        issues.Add($"{input} {token:X8} parameter {sequence}: original name missing");
                }
            }
            else throw new InvalidDataException($"Unknown source alias kind: {entry.Name}");
        }
    }
    using var stream = new FileStream(args[1], FileMode.CreateNew, FileAccess.Write);
    JsonSerializer.Serialize(stream, new { Export = export, Modules = modules, Types = types, Methods = methods, Parameters = parameters, IssueCount = issues.Count, Issues = issues }, new JsonSerializerOptions { WriteIndented = true });
    Console.WriteLine($"{(issues.Count == 0 ? "PASS" : "FAIL")}: {modules} modules, {types} types, {methods} methods, {parameters} parameters; {issues.Count} issues.");
    return issues.Count == 0 ? 0 : 1;
}
catch (Exception ex) {
    Console.Error.WriteLine(ex.Message);
    return 2;
}
