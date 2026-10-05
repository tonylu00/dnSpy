using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;
using dnlib.DotNet;

// Read-only physical join. Reconstruction evidence is not a waiver for a runtime contract.
if (args.Length != 4) {
    Console.Error.WriteLine("Usage: SourceAliasEvidence <scope-audit.json> <alias-audit.json> <compiled-source-bindings.json> <new-report.json>");
    return 2;
}
var paths = OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal;
try {
    if (File.Exists(args[3]) || Directory.Exists(args[3])) throw new IOException("Choose a fresh output.");
    using var scopeDoc = Read(args[0]); using var aliasDoc = Read(args[1]); using var compiledDoc = Read(args[2]);
    var scope = scopeDoc.RootElement; var alias = aliasDoc.RootElement; var compiled = compiledDoc.RootElement;
    Require(Text(scope, "Kind") == "PhysicalScopeFinalAstCoverageAudit" && scope.GetProperty("PrintedReferenceCoverage").GetBoolean(), "Complete printed scope audit required.");
    Require(Text(compiled, "Kind") == "ActualCompiledSourceToNativeObservationJoin", "Actual compiled-source join required.");
    var pins = args.Take(3).Select(p => new Pin(Path.GetFullPath(p), Hash(p))).ToList();
    Require(Hash(Text(scope, "Summary")) == Text(scope, "SummarySha256"), "Stale scope summary.");
    Require(Hash(Text(compiled.GetProperty("ScopeSummary"), "Path")) == Text(compiled.GetProperty("ScopeSummary"), "Sha256"), "Stale compiled scope summary.");
    Require(Text(compiled.GetProperty("ScopeSummary"), "Sha256") == Text(scope, "SummarySha256"), "Different source scopes.");
    var modules = scope.GetProperty("Modules").EnumerateArray().ToDictionary(m => Full(Text(m, "Input")), paths);
    var sources = compiled.GetProperty("Rows").EnumerateArray().ToDictionary(m => Full(Text(m, "Module")), paths);
    Require(modules.Count == scope.GetProperty("TotalModules").GetInt32() && modules.Count == sources.Count, "Incomplete physical join.");
    var states = scope.GetProperty("StateMachineSourceCoverage").GetProperty("Modules").EnumerateArray().ToDictionary(m => Full(Text(m, "Input")), paths);
    var cross = scope.GetProperty("CrossModuleFirstPartyPrintedDefinitions").EnumerateArray().GroupBy(m => Full(Text(m, "Module")), paths)
        .ToDictionary(g => g.Key, g => g.ToDictionary(m => Token(m, "Token"), m => m.GetProperty("UseRecords").GetInt32()), paths);
    var issues = alias.GetProperty("Issues").EnumerateArray().Select(i => ParseIssue(i.GetString()!)).ToArray();
    Require(issues.Length == alias.GetProperty("IssueCount").GetInt32(), "Issue count mismatch.");
    var rows = new List<object>(); var counts = new Dictionary<string, int>();
    foreach (var group in issues.GroupBy(i => Full(i.Module), paths)) {
        Require(modules.TryGetValue(group.Key, out var moduleAudit) && sources.TryGetValue(group.Key, out _), "Missing physical module.");
        var source = sources[group.Key];
        string exportRoot = Full(Text(alias, "Export"));
        foreach (var file in source.GetProperty("Sources").EnumerateArray()) {
            string path = Full(Path.Combine(exportRoot, Text(file, "File")));
            string relative = Path.GetRelativePath(exportRoot, path);
            Require(!Path.IsPathRooted(relative) && relative != ".." && !relative.StartsWith(".." + Path.DirectorySeparatorChar), "Source escaped export root.");
            Require(Hash(path) == Text(file, "FileSha256"), "Compiled source changed.");
            pins.Add(new(path, Text(file, "FileSha256")));
        }
        string reportPath = Text(moduleAudit, "Report");
        Require(Hash(reportPath) == Text(moduleAudit, "ReportSha256"), "Native report changed.");
        pins.Add(new(reportPath, Text(moduleAudit, "ReportSha256")));
        Require(Hash(group.Key) == Text(moduleAudit, "Sha256") && Text(source, "InputSha256") == Text(moduleAudit, "Sha256") && Text(source, "Mvid") == Text(moduleAudit, "Mvid"), "Original physical module changed.");
        using var original = ModuleDefMD.Load(group.Key);
        Require(original.Mvid.ToString() == Text(moduleAudit, "Mvid") && original.Assembly.FullName == Text(moduleAudit, "Identity"), "Original identity mismatch.");
        using var nativeDoc = Read(reportPath); var native = nativeDoc.RootElement;
        Require(Text(native, "InputSha256") == Text(moduleAudit, "Sha256") && Text(native, "Mvid") == Text(moduleAudit, "Mvid") && Text(native, "MapSha256") == Text(scope, "SourceMapSha256"), "Observation identity mismatch.");
        var roots = native.GetProperty("Roots").EnumerateArray().ToArray();
        var wanted = group.Select(i => i.Token).ToHashSet();
        var evidence = wanted.ToDictionary(t => t, _ => new Evidence());
        foreach (var root in roots) {
            uint rootToken = Token(root, "RootTypeToken");
            foreach (var t in root.GetProperty("DeclarationTokens").EnumerateArray()) if (evidence.TryGetValue(t.GetUInt32(), out var e)) e.DeclarationRoots.Add(rootToken);
            foreach (var w in root.GetProperty("BodyWitnesses").EnumerateArray()) {
                foreach (uint t in new[] { Token(w, "ImplementationToken"), Token(w, "ImplementationTypeToken") }.Distinct())
                    if (evidence.TryGetValue(t, out var e)) e.Witnesses.Add(new RootRecord(rootToken, w.Clone()));
            }
            foreach (var b in root.GetProperty("FieldBindings").EnumerateArray()) if (evidence.TryGetValue(Token(b, "FieldToken"), out var e)) e.Bindings.Add(new RootRecord(rootToken, b.Clone()));
            foreach (var u in root.GetProperty("PrintedReferences").EnumerateArray()) {
                if (u.GetProperty("IsDefinition").GetBoolean() || u.GetProperty("IsImplementationAnnotation").GetBoolean() || !paths.Equals(Text(u, "DefinitionModulePath"), group.Key)) continue;
                if (evidence.TryGetValue(Token(u, "DefinitionToken"), out var e)) e.PrintedUses.Add(new PrintedUse(rootToken, Token(u, "OwnerToken"), Text(u, "Text")));
            }
        }
        var machineByMember = new Dictionary<uint, JsonElement>();
        foreach (var machine in states[group.Key].GetProperty("States").EnumerateArray())
            foreach (var t in machine.GetProperty("MemberTokens").EnumerateArray()) if (wanted.Contains(t.GetUInt32())) Require(machineByMember.TryAdd(t.GetUInt32(), machine), "Ambiguous state membership.");
        var filesByRoot = source.GetProperty("Sources").EnumerateArray().Where(s => s.GetProperty("RootToken").ValueKind == JsonValueKind.Number)
            .GroupBy(s => Token(s, "RootToken")).ToDictionary(g => g.Key, g => g.Select(s => s.Clone()).ToArray());
        var nativeDefinitions = native.GetProperty("Definitions").EnumerateArray().ToDictionary(d => Token(d, "Token"));
        foreach (var issue in group) {
            var member = original.ResolveToken(issue.Token) as IMemberDef ?? throw new InvalidDataException("Missing original member.");
            Require(nativeDefinitions.TryGetValue(issue.Token, out var definition) && member.FullName == Text(definition, "FullName"), "Original signature mismatch.");
            var e = evidence[issue.Token];
            var generated = new List<object>();
            for (IMemberDef? cursor = member; cursor != null; cursor = cursor.DeclaringType)
                foreach (var a in cursor.CustomAttributes.Where(a => a.TypeFullName == "System.Runtime.CompilerServices.CompilerGeneratedAttribute"))
                    generated.Add(new { OwnerToken = cursor.MDToken.Raw, OwnerSignature = cursor.FullName, AttributeAssembly = a.AttributeType.DefinitionAssembly.FullName });
            bool hasMachine = machineByMember.TryGetValue(issue.Token, out var machine);
            uint[] machineRoots = hasMachine ? machine.GetProperty("Witnesses").EnumerateArray().Select(w => Token(w, "RootTypeToken")).Distinct().ToArray() : [];
            var observedRoots = e.DeclarationRoots.Concat(e.Witnesses.Select(w => w.RootTypeToken)).Concat(e.Bindings.Select(b => b.RootTypeToken)).Concat(e.PrintedUses.Select(u => u.RootTypeToken)).Concat(machineRoots).Distinct().Order().ToArray();
            var files = observedRoots.SelectMany(t => filesByRoot.GetValueOrDefault(t) ?? []).DistinctBy(f => Text(f, "File")).ToArray();
            bool exact = observedRoots.Length > 0 && observedRoots.All(t => filesByRoot.TryGetValue(t, out var f) && f.Length == 1 && Text(f[0], "Status") == "ExactNativeRootSource");
            int crossUses = cross.TryGetValue(group.Key, out var uses) ? uses.GetValueOrDefault(issue.Token) : 0;
            string classification = e.DeclarationRoots.Count > 0 || e.PrintedUses.Count > 0 || crossUses > 0 ? "RetainedDeclarationOrUse" : hasMachine ? "StateOwnerObserved" : e.Witnesses.Count > 0 ? "BodyOwnerObserved" : e.Bindings.Count > 0 ? "FieldBindingObserved" : "NoDirectSourceEvidence";
            counts[classification] = counts.GetValueOrDefault(classification) + 1;
            rows.Add(new { issue.Module, Sha256 = Text(moduleAudit, "Sha256"), Mvid = Text(moduleAudit, "Mvid"), issue.Token, issue.ParameterSequence, Signature = member.FullName, issue.Message,
                Classification = classification, GeneratedAttributeEvidence = generated, DeclarationRoots = e.DeclarationRoots.Order().ToArray(), BodyWitnesses = e.Witnesses, FieldBindings = e.Bindings,
                LocalPrintedUses = e.PrintedUses.Distinct().ToArray(), CrossModulePrintedUseRecords = crossUses, StateMachine = hasMachine ? machine.Clone() : (JsonElement?)null,
                ObservedRoots = observedRoots, ExactCompiledSourceForAllObservedRoots = exact, CompiledSources = files,
                Disposition = "Unresolved runtime contract; source evidence does not authorize metadata removal or candidate retirement." });
        }
        Require(Hash(reportPath) == Text(moduleAudit, "ReportSha256"), "Native report changed during join.");
        Console.WriteLine($"Joined {group.Count()} differences: {Path.GetRelativePath(Path.GetDirectoryName(group.Key)!, group.Key)}");
    }
    foreach (var pin in pins) Require(Hash(pin.Path) == pin.Sha256, "Join input changed: " + pin.Path);
    using var output = new FileStream(args[3], FileMode.CreateNew, FileAccess.Write);
    JsonSerializer.Serialize(output, new { Format = 1, Kind = "PhysicalSourceAliasDifferenceEvidence", Issues = rows.Count, Counts = counts, Rows = rows, Pins = pins, CandidatesRetired = 0,
        Limits = "Physical module/hash/MVID/token/signature join of strict restored-alias differences to final source observations and compiled files. Compiler-generated attributes, reconstruction witnesses and absent printed uses do not prove reflection, serialization or external runtime safety. All differences remain unresolved; no binaries, source or maps are changed." }, new JsonSerializerOptions { WriteIndented = true });
    Console.WriteLine(JsonSerializer.Serialize(new { Issues = rows.Count, Counts = counts, CandidatesRetired = 0 }));
    return 0;
}
catch (Exception ex) { Console.Error.WriteLine(ex); return 2; }


static string Full(string path) => Path.GetFullPath(path);
static string Text(JsonElement value, string name) => value.GetProperty(name).GetString() ?? "";
static uint Token(JsonElement value, string name) => value.GetProperty(name).GetUInt32();
static void Require(bool condition, string message) { if (!condition) throw new InvalidDataException(message); }
static JsonDocument Read(string path) { using var stream = File.OpenRead(path); return JsonDocument.Parse(stream); }
static string Hash(string path) { using var stream = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(stream)); }
static Issue ParseIssue(string value) {
    var match = Regex.Match(value, @"^(.*) ([0-9A-F]{8})(?: parameter ([0-9]+))?: (.*)$", RegexOptions.CultureInvariant);
    if (!match.Success) throw new InvalidDataException("Unrecognized issue: " + value);
    return new(match.Groups[1].Value, Convert.ToUInt32(match.Groups[2].Value, 16), match.Groups[3].Success ? int.Parse(match.Groups[3].Value) : null, match.Groups[4].Value);
}
record Issue(string Module, uint Token, int? ParameterSequence, string Message);
record Pin(string Path, string Sha256);
record RootRecord(uint RootTypeToken, JsonElement Evidence);
record PrintedUse(uint RootTypeToken, uint OwnerToken, string Text);
sealed class Evidence {
    public HashSet<uint> DeclarationRoots { get; } = [];
    public List<RootRecord> Witnesses { get; } = [];
    public List<RootRecord> Bindings { get; } = [];
    public List<PrintedUse> PrintedUses { get; } = [];
}
