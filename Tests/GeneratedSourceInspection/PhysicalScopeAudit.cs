using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text.Json;
using System.Xml;
using System.Xml.Linq;
using dnlib.DotNet;

// Validates observation coverage against original metadata, never against name
// spelling or absence of a declaration in one root. No naming decisions/writes.
internal static class PhysicalScopeAudit {
    static readonly StringComparer Paths = OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal;
    static string Hash(string path) { using var stream = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(stream)); }
    static string Text(JsonElement value, string name) => value.GetProperty(name).GetString() ?? throw new InvalidDataException("Missing " + name);
    static uint Token(JsonElement value, string name) => value.GetProperty(name).GetUInt32();
    static void Require(bool condition, string message) { if (!condition) throw new InvalidDataException(message); }
    static JsonDocument Read(string path) => JsonDocument.Parse(File.ReadAllText(path));

    public static int Run(string summaryPath, string output) {
        summaryPath = Path.GetFullPath(summaryPath); output = Path.GetFullPath(output);
        Require(!File.Exists(output) && !Directory.Exists(output), "Choose a fresh scope audit output.");
        string summaryHash = Hash(summaryPath);
        using var summaryDocument = Read(summaryPath);
        var summary = summaryDocument.RootElement;
        Require(Text(summary, "Kind") == "MappedPhysicalScopeFinalAstObservations" && Text(summary, "Status") == "complete", "Scope observations are incomplete.");
        string manifestPath = Path.GetFullPath(Text(summary, "ReferenceManifest")), mapPath = Path.GetFullPath(Text(summary, "SourceMap"));
        var pins = summary.GetProperty("Pins").EnumerateObject().ToDictionary(p => Path.GetFullPath(p.Name), p => p.Value.GetString()!, Paths);
        void VerifyPins() { foreach (var pin in pins) Require(Hash(pin.Key) == pin.Value, "Scope tool/map/context pin changed: " + pin.Key); }
        VerifyPins();
        Require(pins.ContainsKey(manifestPath) && pins.ContainsKey(mapPath), "Missing scope map/context pins.");
        using var references = new PinnedSourceContext(manifestPath);
        Require(references.RequireSourceContexts && references.InputDirectory != null, "Scope audit requires pinned source contexts/root.");
        string relativeOutput = Path.GetRelativePath(references.InputDirectory!, output);
        Require(Path.IsPathRooted(relativeOutput) || relativeOutput == ".." || relativeOutput.StartsWith(".." + Path.DirectorySeparatorChar), "Write audit outside application inputs.");
        using var reader = XmlReader.Create(mapPath, new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null });
        var map = XDocument.Load(reader).Root ?? throw new InvalidDataException("Missing map root.");
        Require(Paths.Equals(Path.GetFullPath((string?)map.Attribute("InputDirectory") ?? ""), references.InputDirectory), "Map/context root mismatch.");
        string? whitelist = (string?)map.Attribute("SdkNameWhitelist");
        if (whitelist != null) whitelist = Path.GetFullPath(whitelist, Path.GetDirectoryName(mapPath)!);
        string? whitelistHash = whitelist == null ? null : Hash(whitelist);
        var export = references.Entries.Where(p => p.ExportInput).ToDictionary(p => p.Path, Paths);
        var results = summary.GetProperty("Results").EnumerateArray().ToArray();
        Require(export.Count == results.Length && summary.GetProperty("ExpectedModules").GetInt32() == export.Count && summary.GetProperty("CompletedModules").GetInt32() == export.Count, "Physical module coverage mismatch.");
        var seen = new HashSet<string>(Paths);
        var audits = new List<object>();
        var crossModuleReferences = new Dictionary<(string Path, uint Token), int>();
        var unpinned = new List<object>();
        string? normalizedMapHash = null;
        int rootCount = 0, witnessCount = 0, fieldCount = 0, unresolvedCount = 0, nonlocalCount = 0, unknownOwnerCount = 0;
        foreach (var result in results) {
            string input = Path.GetFullPath(Text(result, "Input"));
            Require(export.TryGetValue(input, out var pin) && seen.Add(input), "Foreign/duplicate physical module.");
            string reportPath = Path.GetFullPath(Text(result, "Report"));
            Require(Hash(reportPath) == Text(result, "ReportSha256"), "Native report changed.");
            using var reportDocument = Read(reportPath);
            var report = reportDocument.RootElement;
            var module = references.FindModule(input)!;
            Require(Text(report, "InputSha256") == pin!.Sha256 && Guid.Parse(Text(report, "Mvid")) == module.Mvid && Text(report, "AssemblyIdentity") == pin.Identity, "Native physical module mismatch.");
            Require(Text(report, "Mode") == "MappedFinalCSharpAst" && report.GetProperty("MapApplied").GetBoolean() && report.GetProperty("RestoreMetadataOnlyFields").GetBoolean(), "Expected mapped SDK C# observations.");
            Require(Text(report, "MapSha256") == pins[mapPath] && Text(report, "ReferenceManifestSha256") == pins[manifestPath], "Native map/context pin mismatch.");
            Require(whitelistHash == null || Text(report, "SdkNameWhitelistSha256") == whitelistHash, "Native SDK whitelist changed.");
            string normalized = Text(report, "NormalizedMapSha256");
            normalizedMapHash ??= normalized;
            Require(normalized == normalizedMapHash, "Native normalized mapping differs across physical modules.");
            foreach (var dependency in report.GetProperty("Dependencies").EnumerateArray()) Require(Hash(Text(dependency, "Path")) == Text(dependency, "Sha256"), "Native tool dependency changed.");
            var options = report.GetProperty("Options").EnumerateArray().Select(v => v.GetString()!).ToArray();
            Require(options.Length == 3 && options.Contains("--sdk-source") && options.Any(o => o.StartsWith("--references=")) && options.Any(o => o.StartsWith("--map=")), "Filtered/unsupported module observation.");
            var definitions = module.GetTypes().SelectMany(t => new IMemberDef[] { t }.Concat(t.Methods).Concat(t.Fields).Concat(t.Properties).Concat(t.Events)).ToDictionary(d => d.MDToken.Raw);
            var reportedDefinitions = report.GetProperty("Definitions").EnumerateArray().ToArray();
            Require(reportedDefinitions.Length == definitions.Count, "Incomplete original definition inventory.");
            var definitionTokens = new HashSet<uint>();
            foreach (var definition in reportedDefinitions) {
                uint token = Token(definition, "Token");
                Require(definitionTokens.Add(token) && definitions.TryGetValue(token, out var original) && original.FullName == Text(definition, "FullName") && original.Name.String == Text(definition, "OriginalName"), "Original physical definition changed.");
            }
            var expectedRoots = module.Types.Where(t => !t.IsGlobalModuleType).Select(t => t.MDToken.Raw).ToHashSet();
            var actualRoots = new HashSet<uint>();
            int localWitnesses = 0, localFields = 0, localNonlocal = 0, localUnresolved = 0;
            foreach (var root in report.GetProperty("Roots").EnumerateArray()) {
                uint rootToken = Token(root, "RootTypeToken");
                Require(actualRoots.Add(rootToken) && expectedRoots.Contains(rootToken) && root.GetProperty("CompleteTypeScope").GetBoolean() && Guid.Parse(Text(root, "ModuleMvid")) == module.Mvid, "Foreign/duplicate/incomplete AST root.");
                // GenericParam (and parameter) annotations are valid original
                // metadata definitions but are not ordinary map member rows.
                foreach (string name in new[] { "DeclarationTokens", "ReferenceTokens" }) foreach (var token in root.GetProperty(name).EnumerateArray()) Require(module.ResolveToken(token.GetUInt32()) is IMemberDef local && local.Module == module, $"AST token is not an original local definition: {input}, root 0x{rootToken:X8}, {name} 0x{token.GetUInt32():X8}.");
                void Owner(JsonElement use) { uint token = Token(use, "OwnerToken"); if (token == 0) unknownOwnerCount++; else Require(definitions.ContainsKey(token), "AST owner is not a local definition."); }
                foreach (var witness in root.GetProperty("BodyWitnesses").EnumerateArray()) {
                    Owner(witness);
                    Require(definitions.TryGetValue(Token(witness, "ImplementationToken"), out var implementation) && implementation is MethodDef method && method.DeclaringType.MDToken.Raw == Token(witness, "ImplementationTypeToken"), "Body witness implementation/type mismatch.");
                    localWitnesses++;
                }
                foreach (var field in root.GetProperty("FieldBindings").EnumerateArray()) {
                    Owner(field); Require(definitions.TryGetValue(Token(field, "FieldToken"), out var definition) && definition is FieldDef, "Hoisted binding is not an original field.");
                    Require(!string.IsNullOrEmpty(Text(field, "SourceName")), "Empty hoisted source variable name."); localFields++;
                }
                foreach (var use in root.GetProperty("NonlocalReferences").EnumerateArray()) {
                    Owner(use); uint token = Token(use, "DefinitionToken");
                    if (token == 0) { localUnresolved++; continue; }
                    string targetPath = Text(use, "DefinitionModulePath");
                    var target = references.FindModule(targetPath);
                    if (target == null) { unpinned.Add(new { Input = input, RootTypeToken = rootToken, Target = targetPath, Token = token }); continue; }
                    Require(target.Mvid == Guid.Parse(Text(use, "DefinitionModuleMvid")) && target.Assembly.FullName == Text(use, "DefinitionAssemblyIdentity") && target.ResolveToken(token) is IMemberDef definition && definition.FullName == Text(use, "DefinitionSignature"), "Nonlocal pinned definition mismatch.");
                    localNonlocal++;
                    if (export.ContainsKey(target.Location)) {
                        var key = (target.Location, token); crossModuleReferences.TryGetValue(key, out int count); crossModuleReferences[key] = count + 1;
                    }
                }
            }
            Require(expectedRoots.SetEquals(actualRoots), "Missing original top-level AST roots.");
            var sourceRoots = new HashSet<uint>();
            foreach (var source in report.GetProperty("SourceHashes").EnumerateArray()) {
                string sourceHash = Text(source, "SourceSha256");
                Require(sourceRoots.Add(Token(source, "RootTypeToken")) && sourceHash.Length == 64 && sourceHash.All(Uri.IsHexDigit) && source.GetProperty("Characters").GetInt32() >= 0, "Invalid/duplicate printed source hash.");
            }
            Require(sourceRoots.SetEquals(expectedRoots), "Printed source hash coverage differs from metadata roots.");
            audits.Add(new { Input = input, pin.Identity, pin.Mvid, pin.Sha256, Report = reportPath, ReportSha256 = Text(result, "ReportSha256"), Roots = actualRoots.Count, Definitions = definitions.Count, BodyWitnesses = localWitnesses, FieldBindings = localFields, PinnedNonlocalUses = localNonlocal, UnresolvedNonlocalUses = localUnresolved });
            rootCount += actualRoots.Count; witnessCount += localWitnesses; fieldCount += localFields; nonlocalCount += localNonlocal; unresolvedCount += localUnresolved;
            Require(Hash(reportPath) == Text(result, "ReportSha256"), "Native report changed during audit.");
        }
        references.Verify(); VerifyPins();
        Require(Hash(summaryPath) == summaryHash && (whitelist == null || Hash(whitelist) == whitelistHash), "Scope/whitelist input changed during audit.");
        Directory.CreateDirectory(Path.GetDirectoryName(output)!);
        var audit = new { Format = 1, Kind = "PhysicalScopeFinalAstCoverageAudit", Summary = summaryPath, SummarySha256 = summaryHash, ReferenceManifest = manifestPath, ReferenceManifestSha256 = pins[manifestPath], SourceMap = mapPath, SourceMapSha256 = pins[mapPath], SdkWhitelist = whitelist, SdkWhitelistSha256 = whitelistHash, NormalizedMapSha256 = normalizedMapHash, Modules = audits, TotalModules = audits.Count, Roots = rootCount, BodyWitnesses = witnessCount, FieldBindings = fieldCount, PinnedNonlocalUses = nonlocalCount, UnresolvedNonlocalUses = unresolvedCount, UnpinnedDefinitions = unpinned, UnknownOwnerRecords = unknownOwnerCount,
            CrossModuleFirstPartyDefinitions = crossModuleReferences.OrderBy(p => p.Key.Path, Paths).ThenBy(p => p.Key.Token).Select(p => new { Module = p.Key.Path, Token = p.Key.Token, UseRecords = p.Value }).ToArray(), CandidatesRetired = 0,
            Limits = "Complete supplied physical export-input/root/definition/source-hash observation coverage, verified against original metadata. Final AST witnesses and nonlocal uses are observations only; unpinned, unresolved and unknown-owner records remain explicit. No semantic naming verdict, source retirement, restoration-contract completeness, compiling ETS export or runtime compatibility proof." };
        using (var stream = new FileStream(output, FileMode.CreateNew, FileAccess.Write)) JsonSerializer.Serialize(stream, audit, new JsonSerializerOptions { WriteIndented = true });
        Console.WriteLine($"PASS: {audits.Count} physical modules, {rootCount} original roots, {witnessCount} body witnesses, {nonlocalCount} pinned nonlocal uses. No candidates retired.");
        return 0;
    }
}
