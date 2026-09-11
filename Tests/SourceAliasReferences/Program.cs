using System.Security.Cryptography;
using System.Text.Json;
using System.Xml;
using System.Xml.Linq;
using dnlib.DotNet;
using dnSpy_Console;
using dnSpy.Contracts.Decompiler;

// Read-only preflight uses the exporter's exact physical-input/config resolvers.
// Scope-insensitive comparison diagnoses missed alias candidates; it NEVER binds
// a reference or permits two same-named dependency types to be substituted.
if (args.Length < 3) {
    Console.Error.WriteLine("Usage: SourceAliasReferences <inputs.json> <names.xml> <new-report.json> [--contexts file] [--config file] [--asm-path directory] [--no-gac]");
    return 2;
}
if (File.Exists(args[2])) { Console.Error.WriteLine("Choose a new report path."); return 2; }
var issues = new List<object>();
var modules = new List<ModuleDefMD>();
int references = 0, resolvedAliases = 0, nativeInputs = 0;
var pathComparer = OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal;
var paths = new List<string>();
string? contexts = null, config = null;
bool useGac = true;
try {
    for (int i = 3; i < args.Length; i++) {
        if (args[i] == "--no-gac") { useGac = false; continue; }
        if (i + 1 == args.Length) throw new ArgumentException("Missing option argument.");
        switch (args[i]) {
            case "--contexts": contexts = Path.GetFullPath(args[++i]); break;
            case "--config": config = Path.GetFullPath(args[++i]); break;
            case "--asm-path": paths.Add(Path.GetFullPath(args[++i])); break;
            default: throw new ArgumentException("Unknown option: " + args[i]);
        }
    }
    var context = ModuleDef.CreateModuleContext();
    var fallback = (AssemblyResolver)context.AssemblyResolver;
    fallback.EnableFrameworkRedirect = false;
    fallback.FindExactMatch = true;
    fallback.EnableTypeDefCache = true;
    fallback.UseGAC = useGac;
    foreach (var path in paths) fallback.PreSearchPaths.Add(path);
    if (config != null) fallback.PreSearchPaths.Add(Path.GetDirectoryName(config)!);
    var inputs = JsonSerializer.Deserialize<string[]>(File.ReadAllText(args[0])) ?? throw new InvalidDataException("Expected input path array.");
    foreach (var input in inputs) {
        // Native PE inputs are retained by dnSpy but have no managed references.
        using var pe = new System.Reflection.PortableExecutable.PEReader(File.OpenRead(input));
        if (!pe.HasMetadata) { nativeInputs++; continue; }
        modules.Add(ModuleDefMD.Load(input, context));
    }
    IAssemblyResolver resolver = new InputAssemblyResolver(fallback, modules);
    if (config != null) resolver = new ApplicationConfigResolver(resolver, config);
    if (contexts != null) resolver = new AssemblyContextResolver(resolver, contexts, modules, useGac, paths);
    context.AssemblyResolver = resolver;
    context.Resolver = new Resolver(resolver);
    var byPath = modules.ToDictionary(m => Path.GetFullPath(m.Location), pathComparer);
    using var reader = XmlReader.Create(args[1], new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null });
    var map = XDocument.Load(reader).Root ?? throw new InvalidDataException("Missing map.");
    if (map.Name != "SourceNameMap" || (string?)map.Attribute("Version") != "1") throw new InvalidDataException("Expected version 1 source map.");
    var root = Path.GetFullPath(Required(map, "InputDirectory"));
    var mapped = new HashSet<MethodDef>();
    foreach (var row in map.Elements("Module")) {
        var input = Path.GetFullPath(Path.Combine(root, Required(row, "Path")));
        if (!byPath.TryGetValue(input, out var module)) throw new InvalidDataException("Mapped module absent from inputs: " + input);
        if (module.Mvid != Guid.Parse(Required(row, "Mvid")) ||
            !StringComparer.OrdinalIgnoreCase.Equals(Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(input))), Required(row, "Sha256")))
            throw new InvalidDataException("Stale physical module: " + input);
        foreach (var alias in row.Elements("Method").Where(e => e.Attribute("NewName") != null)) {
            var method = module.ResolveToken(Convert.ToUInt32(Required(alias, "Token").Substring(2), 16)) as MethodDef;
            if (method == null || method.Name != Required(alias, "ExpectedName") || method.FullName != Required(alias, "Signature"))
                throw new InvalidDataException("Stale method identity in " + input);
            mapped.Add(method);
        }
    }
    var owners = mapped.GroupBy(m => m.DeclaringType).ToDictionary(g => g.Key, g => g.ToArray());
    var comparer = new SigComparer(SigComparerOptions.DontCompareTypeScope);
    foreach (var module in modules) foreach (var reference in module.GetMemberRefs().Where(r => r.IsMethodRef)) {
        var owner = reference.DeclaringType?.ResolveTypeDef();
        if (owner == null || !owners.TryGetValue(owner, out var methods)) continue;
        references++;
        var resolved = reference.ResolveMethodDef();
        if (resolved != null) { if (mapped.Contains(resolved)) resolvedAliases++; continue; }
        var typeArgs = ((reference.DeclaringType as TypeSpec)?.TypeSig as GenericInstSig)?.GenericArguments;
        var candidates = methods.Where(m => m.Name == reference.Name &&
            comparer.Equals(GenericArgumentResolver.Resolve(m.MethodSig, typeArgs, null), reference.MethodSig)).ToArray();
        if (candidates.Length == 0) continue;
        issues.Add(new {
            Module = module.Location, Token = reference.MDToken.ToString(), Reference = reference.FullName,
            Reason = "Unresolved reference may target an aliased method. Supply the exact signature dependencies/facades; do not ignore assembly identity.",
            Candidates = candidates.Select(m => new { Module = m.Module.Location, Token = m.MDToken.ToString(), Signature = m.FullName }).ToArray()
        });
    }
}
catch (Exception ex) { issues.Add(new { Reason = ex.Message }); }
finally { foreach (var module in modules) module.Dispose(); }
var report = new { Inputs = Path.GetFullPath(args[0]), Map = Path.GetFullPath(args[1]), Projects = modules.Count, NativeInputs = nativeInputs,
    ReferencesToMappedOwners = references, ResolvedAliasReferences = resolvedAliases, IssueCount = issues.Count, Issues = issues };
// Never replace an existing report, including on an argument or validation error.
using (var output = new FileStream(args[2], FileMode.CreateNew, FileAccess.Write)) JsonSerializer.Serialize(output, report, new JsonSerializerOptions { WriteIndented = true });
Console.WriteLine($"{(issues.Count == 0 ? "PASS" : "FAIL")}: {resolvedAliases} resolved alias references; {issues.Count} issues. {args[2]}");
return issues.Count == 0 ? 0 : 1;

static string Required(XElement element, string name) => (string?)element.Attribute(name) ?? throw new InvalidDataException("Missing " + name);
namespace dnSpy_Console { sealed class ErrorException : Exception { public ErrorException(string message) : base(message) { } } }
