using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json;
using dnlib.DotNet;

// A focused original-metadata join for immutable, complete-root observations.
// Complete application coverage and cross-module escapes remain audit-scope gates.
internal static class StateSourceCoverageInspection {
    static readonly StringComparer Paths = OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal;
    static string Hash(string path) { using var stream = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(stream)); }
    static void Require(bool value, string message) { if (!value) throw new InvalidDataException(message); }

    internal static int Run(string input, string observation, string producer, string output) {
        input = Path.GetFullPath(input); observation = Path.GetFullPath(observation);
        producer = Path.GetFullPath(producer); output = Path.GetFullPath(output);
        Require(!File.Exists(output) && !Directory.Exists(output) && !output.StartsWith(Path.GetDirectoryName(input)! + Path.DirectorySeparatorChar,
            OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal), "Choose a fresh coverage output outside the input tree.");
        var pins = new Dictionary<string,string>(Paths);
        void Pin(string path, string expected) {
            path = Path.GetFullPath(path);
            Require(Hash(path) == expected, "Observation artifact hash mismatch: " + path);
            if (pins.TryGetValue(path,out var previous)) Require(previous == expected,"Conflicting observation artifact pin.");
            pins[path] = expected;
        }
        Pin(observation,Hash(observation));
        using var document = JsonDocument.Parse(File.ReadAllText(observation));
        var report = document.RootElement;
        Require(report.GetProperty("Format").GetInt32() == 1 && report.GetProperty("Mode").GetString() is "RawMetadataFinalCSharpAst" or "MappedFinalCSharpAst",
            "Coverage requires a native final-source observation report.");
        Require(Paths.Equals(input,report.GetProperty("Input").GetString()),"Observation physical input path mismatch.");
        Pin(input,report.GetProperty("InputSha256").GetString()!);
        Pin(producer,report.GetProperty("ToolSha256").GetString()!);
        foreach (var dependency in report.GetProperty("Dependencies").EnumerateArray())
            Pin(dependency.GetProperty("Path").GetString()!,dependency.GetProperty("Sha256").GetString()!);
        foreach (var (path,hash) in new[] {("Map","MapSha256"),("SdkNameWhitelist","SdkNameWhitelistSha256"),("ReferenceManifest","ReferenceManifestSha256")})
            if (report.GetProperty(path).ValueKind == JsonValueKind.String) Pin(report.GetProperty(path).GetString()!,report.GetProperty(hash).GetString()!);
        if (report.GetProperty("SourceOutput").ValueKind == JsonValueKind.String) {
            var hashes = report.GetProperty("SourceHashes").EnumerateArray().ToArray();
            Require(hashes.Length == 1,"Single printed source output requires one source hash.");
            Pin(report.GetProperty("SourceOutput").GetString()!,hashes[0].GetProperty("SourceSha256").GetString()!);
        }
        using var module = ModuleDefMD.Load(input);
        Require(report.GetProperty("Mvid").GetGuid() == module.Mvid && report.GetProperty("AssemblyIdentity").GetString() == module.Assembly?.FullNameToken,
            "Observation physical MVID/assembly identity mismatch.");
        var roots = report.GetProperty("Roots").EnumerateArray().ToArray();
        Require(roots.Length != 0 && roots.All(r=>r.GetProperty("CompleteTypeScope").GetBoolean()),"Coverage requires complete observed roots.");
        var rootTokens = roots.Select(r=>r.GetProperty("RootTypeToken").GetUInt32()).ToHashSet();
        Require(rootTokens.Count == roots.Length && rootTokens.All(t=>module.ResolveToken(t) is TypeDef),"Observed physical root mismatch.");
        bool Inside(TypeDef type) {
            for (var current=type;current!=null;current=current.DeclaringType) if(rootTokens.Contains(current.MDToken.Raw)) return true;
            return false;
        }
        var witnessed = roots.SelectMany(r=>r.GetProperty("BodyWitnesses").EnumerateArray()).Select(w=>w.GetProperty("ImplementationTypeToken").GetUInt32()).ToHashSet();
        var states = StateMachineSourceCoverage.Observe(module,report).Where(e=>witnessed.Contains(e.TypeToken) ||
            Inside((TypeDef)module.ResolveToken(e.TypeToken)) || e.Owners.Any(o=>module.ResolveToken(o.Token) is MethodDef method && Inside(method.DeclaringType))).ToArray();
        foreach(var pin in pins) Require(Hash(pin.Key)==pin.Value,"Observation artifact changed during coverage join.");
        var auditor = Assembly.GetExecutingAssembly().Location;
        var result = new { Format=1,Kind="CompleteObservedRootStateSourceCoverage",Input=input,InputSha256=pins[input],module.Mvid,
            AssemblyIdentity=module.Assembly?.FullNameToken,Observation=observation,ObservationSha256=pins[observation],Producer=producer,ProducerSha256=pins[producer],
            Auditor=auditor,AuditorSha256=Hash(auditor),RootTypeTokens=rootTokens.OrderBy(t=>t).ToArray(),States=states,
            Counts=states.GroupBy(s=>s.Status).ToDictionary(g=>g.Key,g=>g.Count()),CandidatesRetired=0,ArtifactSha256=pins,
            Limits="Exact original metadata joined to complete observed roots only. Shared printed contexts retain all corroborated occurrence paths and one original metadata owner; no guessed canonical owner. Other application roots and cross-module printed uses are outside this focused join. No semantic naming retirement, runtime restoration, compilation or ETS/App compatibility proof." };
        Directory.CreateDirectory(Path.GetDirectoryName(output)!);
        using(var stream=new FileStream(output,FileMode.CreateNew,FileAccess.Write)) JsonSerializer.Serialize(stream,result,new JsonSerializerOptions {WriteIndented=true});
        Console.WriteLine($"PASS: {roots.Length} complete observed roots, {states.Length} original state types; no candidates retired.");
        return 0;
    }
}
