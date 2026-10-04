using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Nodes;
using dnlib.DotNet;

if (args.Length != 1 || Directory.Exists(args[0])) throw new ArgumentException("Choose a fresh synthetic context regression directory.");
string output = Path.GetFullPath(args[0]); Directory.CreateDirectory(output);
string Hash(string path) { using var stream = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(stream)); }
string Emit(string file, string name, int version, string? dependency = null) {
    string path = Path.Combine(output, file);
    using var module = new ModuleDefUser(file) { Mvid = Guid.NewGuid(), Kind = ModuleKind.Dll };
    new AssemblyDefUser(name, new Version(version, 0, 0, 0)).Modules.Add(module);
    var type = new TypeDefUser("Fixture", "Value", module.CorLibTypes.Object.TypeDefOrRef); module.Types.Add(type);
    if (dependency != null) type.Fields.Add(new FieldDefUser("dependency", new FieldSig(new ClassSig(new TypeRefUser(module, "Fixture", "Value", new AssemblyRefUser(new AssemblyNameInfo(dependency)))))));
    module.Write(path); return path;
}
const string requested = "Shared, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null";
const string redirected = "Shared, Version=3.0.0.0, Culture=neutral, PublicKeyToken=null";
string left = Emit("left.dll", "Shared", 1), right = Emit("right.dll", "Shared", 1), newer = Emit("newer.dll", "Shared", 3);
string first = Emit("first.dll", "First", 1, requested), second = Emit("second.dll", "Second", 1, requested);
string config = Path.Combine(output, "host.config");
File.WriteAllText(config, "<configuration><runtime><assemblyBinding xmlns=\"urn:schemas-microsoft-com:asm.v1\"><dependentAssembly><assemblyIdentity name=\"Shared\" culture=\"neutral\" publicKeyToken=\"null\"/><bindingRedirect oldVersion=\"0.0.0.0-2.0.0.0\" newVersion=\"3.0.0.0\"/></dependentAssembly></assemblyBinding></runtime></configuration>");
object Pin(string path) { using var module = ModuleDefMD.Load(path); return new { Path = path, Identity = module.Assembly.FullName, Mvid = module.Mvid, Sha256 = Hash(path), ExportInput = true }; }
var manifest = JsonSerializer.SerializeToNode(new { Format = 1, InputDirectory = output, Assemblies = new[] { left, right, newer, first, second }.Select(Pin), Bindings = Array.Empty<object>(), Configs = Array.Empty<object>() })!;
int checks = 0, serial = 0;
void Check(bool condition, string message) { checks++; if (!condition) throw new Exception(message); }
string Save(JsonNode value) { string path = Path.Combine(output, $"context-{serial++}.json"); File.WriteAllText(path, value.ToJsonString()); return path; }
using (var context = new PinnedSourceContext(Save(manifest))) {
    var source = context.FindModule(first)!;
    Check(context.ExportInputs.Count() == 5, "exact export input objects");
    Check(context.Resolve(new AssemblyNameInfo(requested), source) == null, "twins must remain ambiguous");
    Check(context.Resolutions.Single().Status == "ambiguous-physical-identity", "ambiguity provenance");
    Check(context.Resolve(new AssemblyNameInfo(redirected), source)?.ManifestModule.Location == newer, "unique full identity");
    Check(context.Resolve(new AssemblyNameInfo(requested), context.FindModule(left))?.ManifestModule.Location == left, "left physical self");
    Check(context.Resolve(new AssemblyNameInfo(requested), context.FindModule(right))?.ManifestModule.Location == right, "right physical self");
    Check(context.Resolve(new AssemblyNameInfo("Shared, Version=2.0.0.0, Culture=neutral, PublicKeyToken=null"), source) == null, "no implicit version equivalence");
    Check(context.Resolve(new AssemblyNameInfo("Shared, Version=3.0.0.0, Culture=neutral, PublicKeyToken=1234567890123456"), source) == null, "no signing equivalence");
    using var user = new ModuleDefUser("self"); new AssemblyDefUser("Self", new Version(1, 0, 0, 0)).Modules.Add(user);
    Check(context.Resolve(user.Assembly, user) == user.Assembly, "in-memory physical self"); context.Verify();
}
var bound = manifest.DeepClone();
bound["Bindings"] = JsonSerializer.SerializeToNode(new[] { new { Source = first, Identity = requested, Target = left }, new { Source = second, Identity = requested, Target = right } });
using (var context = new PinnedSourceContext(Save(bound))) {
    Check(context.Resolve(new AssemblyNameInfo(requested), context.FindModule(first))?.ManifestModule.Location == left, "first exact physical target");
    Check(context.Resolve(new AssemblyNameInfo(requested), context.FindModule(second))?.ManifestModule.Location == right, "second exact physical target");
    Check(context.Resolutions.All(r => r.Status == "explicit-physical-binding"), "binding provenance");
}
var configured = manifest.DeepClone();
configured["Configs"] = JsonSerializer.SerializeToNode(new[] { new { Source = first, Path = config, Sha256 = Hash(config) } });
using (var context = new PinnedSourceContext(Save(configured))) {
    var source = context.FindModule(first);
    Check(context.Resolve(new AssemblyNameInfo(requested), source)?.ManifestModule.Location == newer, "explicit source redirect");
    var record = context.Resolutions.Single(r => r.Identity == requested);
    Check(record.EffectiveIdentity == redirected && record.ConfigPath == config && record.Target == newer, "requested/effective/config provenance");
    Check(context.Resolve(new AssemblyNameInfo(requested), context.FindModule(second)) == null, "host config did not escape source context");
    Check(context.Resolve(new AssemblyNameInfo("Shared, Version=1.0.0.0, Culture=fr, PublicKeyToken=null"), source) == null, "redirect culture guard");
    Check(context.Resolve(new AssemblyNameInfo("Shared, Version=1.0.0.0, Culture=neutral, PublicKeyToken=1234567890123456"), source) == null, "redirect signing guard");
    Check(context.Resolve(new AssemblyNameInfo("Shared, Version=4.0.0.0, Culture=neutral, PublicKeyToken=null"), source) == null, "redirect range guard");
    string original = File.ReadAllText(config); File.AppendAllText(config, " ");
    bool rejected = false; try { context.Verify(); } catch (InvalidDataException) { rejected = true; }
    Check(rejected, "config changed during inspection"); File.WriteAllText(config, original);
}
var mutations = new Dictionary<string, Action<JsonNode>> {
    ["stale-hash"] = n => n["Assemblies"]![0]!["Sha256"] = new string('0', 64),
    ["stale-mvid"] = n => n["Assemblies"]![0]!["Mvid"] = Guid.Empty.ToString(),
    ["wrong-identity"] = n => n["Assemblies"]![0]!["Identity"] = redirected,
    ["duplicate-path"] = n => n["Assemblies"]!.AsArray().Add(n["Assemblies"]![0]!.DeepClone()),
    ["root-escape"] = n => n["InputDirectory"] = Path.Combine(output, "child"),
    ["null-configs"] = n => n["Configs"] = null,
    ["wrong-binding-target"] = n => n["Bindings"] = JsonSerializer.SerializeToNode(new[] { new { Source = first, Identity = requested, Target = newer } }),
    ["undeclared-binding-request"] = n => n["Bindings"] = JsonSerializer.SerializeToNode(new[] { new { Source = first, Identity = redirected, Target = newer } }),
    ["missing-binding-source"] = n => n["Bindings"] = JsonSerializer.SerializeToNode(new[] { new { Source = "missing.dll", Identity = requested, Target = left } }),
    ["duplicate-binding"] = n => n["Bindings"] = JsonSerializer.SerializeToNode(Enumerable.Repeat(new { Source = first, Identity = requested, Target = left }, 2)),
    ["stale-config"] = n => n["Configs"] = JsonSerializer.SerializeToNode(new[] { new { Source = first, Path = config, Sha256 = new string('0', 64) } }),
    ["duplicate-config"] = n => n["Configs"] = JsonSerializer.SerializeToNode(Enumerable.Repeat(new { Source = first, Path = config, Sha256 = Hash(config) }, 2))
};
foreach (var mutation in mutations) {
    var bad = manifest.DeepClone(); mutation.Value(bad); bool rejected = false;
    try { using var context = new PinnedSourceContext(Save(bad)); } catch (InvalidDataException) { rejected = true; }
    Check(rejected, "reject " + mutation.Key);
}
string manifestPath = Save(manifest);
using (var context = new PinnedSourceContext(manifestPath)) {
    File.AppendAllText(manifestPath, " "); bool rejected = false;
    try { context.Verify(); } catch (InvalidDataException) { rejected = true; }
    Check(rejected, "manifest changed during inspection");
}
// Modify only this synthetic fixture and restore after the memory map closes.
byte[] originalBytes = File.ReadAllBytes(left);
using (var context = new PinnedSourceContext(Save(manifest))) {
    File.AppendAllText(left, " "); bool rejected = false;
    try { context.Verify(); } catch (InvalidDataException) { rejected = true; }
    Check(rejected, "physical module changed during inspection");
}
File.WriteAllBytes(left, originalBytes);
File.WriteAllText(Path.Combine(output, "proof.json"), JsonSerializer.Serialize(new { Checks = checks, Manifest = manifest, ToolSha256 = Hash(typeof(PinnedSourceContext).Assembly.Location) }, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine($"PASS: {checks} pinned physical-context and redirect guards.");
