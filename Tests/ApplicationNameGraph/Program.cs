using System.Security.Cryptography;
using System.Text.Json;
using System.Xml;
using System.Xml.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
using dnSpy_Console;
using De4dot.NameCandidates;
using SourceNameMapping;

if (args.Length < 3) {
    Console.Error.WriteLine("ApplicationNameGraph <export-map.xml> <names.xml> <new-directory> [--contexts file] [--config file] [--asm-path directory] [--no-gac] [--no-source]");
    return 2;
}
var output = Path.GetFullPath(args[2]);
if (Directory.Exists(output)) throw new IOException("Choose a fresh graph directory.");
string? contexts = null, config = null;
var search = new List<string>(); bool gac = true, source = true;
for (int i = 3; i < args.Length; i++) {
    if (args[i] == "--no-gac") { gac = false; continue; }
    if (args[i] == "--no-source") { source = false; continue; }
    if (i + 1 >= args.Length) throw new ArgumentException("Missing option value.");
    switch (args[i]) {
        case "--contexts": contexts = Path.GetFullPath(args[++i]); break;
        case "--config": config = Path.GetFullPath(args[++i]); break;
        case "--asm-path": search.Add(Path.GetFullPath(args[++i])); break;
        default: throw new ArgumentException("Unknown option: " + args[i]);
    }
}
var comparer = OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal;
var export = ReadXml(args[0]);
if (export.Name != "DnSpyExportMap" || (string?)export.Attribute("ExportErrors") != "0") throw new InvalidDataException("Expected a complete export manifest.");
var exportRoot = Path.GetDirectoryName(Path.GetFullPath(args[0]))!;
var rows = export.Elements("Project").ToArray();
var context = ModuleDef.CreateModuleContext();
var fallback = (AssemblyResolver)context.AssemblyResolver;
fallback.EnableFrameworkRedirect = false; fallback.FindExactMatch = true;
fallback.EnableTypeDefCache = true; fallback.UseGAC = gac;
foreach (var path in search) fallback.PreSearchPaths.Add(path);
if (config != null) fallback.PreSearchPaths.Add(Path.GetDirectoryName(config)!);
var modules = new List<ModuleDefMD>();
var records = new List<ModuleRow>();
var byPath = new Dictionary<string, ModuleRow>(comparer);
try {
    foreach (var row in rows) {
        var input = Path.GetFullPath(Required(row, "Source"));
        if (byPath.ContainsKey(input)) throw new InvalidDataException("Repeated physical input: " + input);
        var hash = Hash(input);
        var id = "m" + records.Count.ToString("D4");
        using var pe = new System.Reflection.PortableExecutable.PEReader(File.OpenRead(input));
        ModuleDefMD? module = pe.HasMetadata ? ModuleDefMD.Load(input, context) : null;
        if (module != null) {
            if (module.Mvid != Guid.Parse(Required(row, "Mvid"))) throw new InvalidDataException("Source/input MVID changed: " + input);
            modules.Add(module);
        }
        var record = new ModuleRow(id, input, hash, (string?)row.Attribute("Mvid"), (string?)row.Attribute("AssemblyName"), Required(row, "Project"), module?.IsILOnly == true);
        records.Add(record); byPath.Add(input, record);
    }
    IAssemblyResolver resolver = new InputAssemblyResolver(fallback, modules);
    if (config != null) resolver = new ApplicationConfigResolver(resolver, config);
    if (contexts != null) resolver = new AssemblyContextResolver(resolver, contexts, modules, gac, search);
    context.AssemblyResolver = resolver; context.Resolver = new Resolver(resolver);
    var physical = modules.ToDictionary(m => Path.GetFullPath(m.Location), comparer);
    string? Key(IMDTokenProvider? member, ModuleDef? module) => member == null || module == null || string.IsNullOrEmpty(module.Location) || !byPath.TryGetValue(Path.GetFullPath(module.Location), out var row) ? null : row.Id + ":0x" + member.MDToken.Raw.ToString("X8");
    var aliases = new Dictionary<string, string>();
    var map = ReadXml(args[1]);
    if (map.Name != "SourceNameMap" || (string?)map.Attribute("Version") != "1") throw new InvalidDataException("Expected a version 1 source name map.");
    var mapRoot = Path.GetFullPath(Required(map, "InputDirectory"));
    foreach (var row in map.Elements("Module")) {
        var path = Path.GetFullPath(Path.Combine(mapRoot, Required(row, "Path")));
        if (!byPath.TryGetValue(path, out var snapshot) || !physical.TryGetValue(path, out var module) || snapshot.Sha256 != Required(row, "Sha256").ToUpperInvariant() || module.Mvid != Guid.Parse(Required(row, "Mvid")))
            throw new InvalidDataException("Stale or missing mapped physical module: " + path);
        foreach (var symbol in row.Elements()) {
            uint token = Convert.ToUInt32(Required(symbol, "Token")[2..], 16);
            var definition = module.ResolveToken(token) as IMemberDef;
            if (definition == null || definition.Name != Required(symbol, "ExpectedName") || definition.FullName != Required(symbol, "Signature")) throw new InvalidDataException("Stale map symbol: " + path + " " + token);
            if (symbol.Attribute("NewName") != null) aliases.Add(Key(definition, module)!, Required(symbol, "NewName"));
        }
    }
    Directory.CreateDirectory(output);
    var graph = new MethodContractFamilies(modules, m => m.Location, useHostResolver: true);
    using var families = new StreamWriter(Path.Combine(output, "families.jsonl"));
    foreach (var family in graph.Families) Write(families, new { family.Id, Members = family.Methods.Select(m => Key(m, m.Module)).ToArray(), family.Blockers });
    using var nodes = new StreamWriter(Path.Combine(output, "symbols.jsonl"));
    using var edges = new StreamWriter(Path.Combine(output, "edges.jsonl"));
    var counts = new List<object>();
    foreach (var module in modules) {
        var info = byPath[Path.GetFullPath(module.Location)];
        var methods = module.GetTypes().SelectMany(t => t.Methods).ToArray();
        var vocabulary = de4dot.code.renamer.MethodNameAnalysis.Learn(methods.Select(m => m.Name.String), methods.Where(m => m.HasBody).SelectMany(m => m.Body.Instructions).Where(i => i.OpCode.Code == Code.Ldstr).Select(i => i.Operand as string));
        var cache = new Dictionary<IMethod, Target>(); var fieldCache = new Dictionary<IField, Target>();
        int candidateCount = 0, mappedCount = 0, edgeCount = 0, unresolved = 0;
        foreach (var type in module.GetTypes()) {
            string typeId = Key(type, module)!;
            Write(nodes, new { Kind = "Type", Id = typeId, Module = info.Id, Token = type.MDToken.ToString(), OriginalName = type.Name.String, Signature = type.FullName, Alias = aliases.GetValueOrDefault(typeId), BaseType = type.BaseType?.FullName, Interfaces = type.Interfaces.Select(i => i.Interface.FullName).ToArray() });
            foreach (var field in type.Fields) Write(nodes, new { Kind = "Field", Id = Key(field, module), Owner = typeId, Token = field.MDToken.ToString(), OriginalName = field.Name.String, Signature = field.FullName, field.IsStatic, field.IsLiteral, field.IsInitOnly });
            foreach (var method in type.Methods) {
                var id = Key(method, module)!;
                var reason = method.IsConstructor ? null : MethodReview.Reason(method.Name, vocabulary);
                if (reason != null) candidateCount++;
                if (aliases.ContainsKey(id)) mappedCount++;
                Write(nodes, new { Kind = "Method", Id = id, Owner = typeId, Token = method.MDToken.ToString(), OriginalName = method.Name.String, Signature = method.FullName, Alias = aliases.GetValueOrDefault(id), ReviewReason = reason, Blocker = MethodContractFamilies.MethodBlocker(method), Family = graph.Get(method)?.Id,
                    Parameters = method.Parameters.Where(p => p.IsNormalMethodParameter).Select(p => new { Sequence = p.MethodSigIndex + 1, OriginalName = p.Name, Type = p.Type.FullName, HasMetadata = p.ParamDef != null }).ToArray(),
                    Locals = method.HasBody ? method.Body.Variables.Select(v => new { Slot = v.Index, Type = v.Type.FullName }).ToArray() : null,
                    Strings = method.HasBody ? method.Body.Instructions.Where(i => i.OpCode.Code == Code.Ldstr).Select(i => (string)i.Operand).Distinct().ToArray() : null });
                if (!method.HasBody) continue;
                foreach (var instruction in method.Body.Instructions) {
                    Target target; string kind;
                    if (instruction.Operand is IMethod reference) {
                        if (!cache.TryGetValue(reference, out target!)) {
                            MethodDef? resolved = null; string? error = null;
                            try { resolved = reference.ResolveMethodDef(); } catch (Exception e) { error = e.Message; }
                            var key = Key(resolved, resolved?.Module);
                            target = new Target(key, reference.FullName, reference.DeclaringType?.DefinitionAssembly?.FullName, resolved?.Module.Location, resolved == null ? "unresolved" : key == null ? "external" : "input", error);
                            cache.Add(reference, target);
                        }
                        kind = "method";
                    } else if (instruction.Operand is IField field) {
                        if (!fieldCache.TryGetValue(field, out target!)) {
                            FieldDef? resolved = null; string? error = null;
                            try { resolved = field.ResolveFieldDef(); } catch (Exception e) { error = e.Message; }
                            var key = Key(resolved, resolved?.Module);
                            target = new Target(key, field.FullName, field.DeclaringType?.DefinitionAssembly?.FullName, resolved?.Module.Location, resolved == null ? "unresolved" : key == null ? "external" : "input", error);
                            fieldCache.Add(field, target);
                        }
                        kind = "field";
                    } else continue;
                    Write(edges, new { From = id, Kind = kind, Offset = instruction.Offset, Operation = instruction.OpCode.Name, Target = target });
                    edgeCount++; if (target.Status == "unresolved") unresolved++;
                }
            }
        }
        counts.Add(new { info.Id, Methods = methods.Length, ReviewCandidates = candidateCount, MappedMethods = mappedCount, Edges = edgeCount, UnresolvedEdges = unresolved });
        Console.WriteLine($"{info.Id} {info.Project}: {methods.Length} methods, {candidateCount} review candidates");
    }
    int sourceRows = source ? SourceIndex.Write(exportRoot, records, output) : 0;
    var retainedBinaries = export.Elements("Binary").Select(row => new { Input = Required(row, "Source"), RelativePath = Required(row, "Path"), Sha256 = Hash(Required(row, "Source")), NamingStatus = "Retained binary dependency; no editable managed source in this export" }).ToArray();
    var manifest = new { Format = 1, Export = Path.GetFullPath(args[0]), ExportSha256 = Hash(args[0]), Map = Path.GetFullPath(args[1]), MapSha256 = Hash(args[1]), Contexts = contexts, ContextsSha256 = contexts == null ? null : Hash(contexts), Config = config, SearchPaths = search, UseGac = gac, Modules = records, RetainedBinaries = retainedBinaries, Counts = counts, SourceRows = sourceRows,
        Limitations = new[] { "Static IL references and contract families are evidence, not a complete runtime call graph; reflection, delegates and virtual dispatch can add targets.", "Unresolved edges are retained and never rebound by name-only matching.", "Identical hashes are comparison evidence only; physical modules and source contexts remain separate.", "Source locals are syntax locations, not proven semantic bindings or stable IL slots." } };
    File.WriteAllText(Path.Combine(output, "manifest.json"), JsonSerializer.Serialize(manifest, new JsonSerializerOptions { WriteIndented = true }));
    return 0;
} finally { foreach (var module in modules) module.Dispose(); }

static XElement ReadXml(string path) { using var r = XmlReader.Create(path, new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null }); return XDocument.Load(r).Root ?? throw new InvalidDataException("Missing XML root."); }
static string Required(XElement row, string name) => (string?)row.Attribute(name) ?? throw new InvalidDataException("Missing " + name);
static string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
static void Write(StreamWriter output, object row) => output.WriteLine(JsonSerializer.Serialize(row));
record ModuleRow(string Id, string Input, string Sha256, string? Mvid, string? AssemblyName, string Project, bool IsILOnly);
record Target(string? Id, string Signature, string? Assembly, string? PhysicalModule, string Status, string? Error);
namespace dnSpy_Console { sealed class ErrorException : Exception { public ErrorException(string message) : base(message) { } } }
