using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Nodes;
using dnlib.DotNet;

if (args.Length != 1 || Directory.Exists(args[0])) throw new ArgumentException("Choose a fresh synthetic context regression directory.");
string output = Path.GetFullPath(args[0]); Directory.CreateDirectory(output);
string Hash(string path) { using var stream = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(stream)); }
string Emit(string file, string name, int version, string? dependency = null) {
    string path = Path.GetFullPath(Path.Combine(output, file));
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
var redirectedBinding = configured.DeepClone();
redirectedBinding["Bindings"] = JsonSerializer.SerializeToNode(new[] { new { Source = first, Identity = redirected, Target = newer, RequestedIdentity = requested } });
using (var context = new PinnedSourceContext(Save(redirectedBinding))) {
    Check(context.Resolve(new AssemblyNameInfo(requested), context.FindModule(first))?.ManifestModule.Location == newer, "redirected physical binding");
    Check(context.Resolutions.Single(r => r.Identity == requested).Status == "explicit-physical-binding", "redirected binding provenance");
}
string emptyDirectory = Path.Combine(output, "empty"); Directory.CreateDirectory(emptyDirectory);
var scoped = manifest.DeepClone();
scoped["Contexts"] = JsonSerializer.SerializeToNode(new[] { new { Source = first, Directories = new[] { emptyDirectory } } });
using (var context = new PinnedSourceContext(Save(scoped))) {
    Check(context.Resolve(new AssemblyNameInfo(redirected), context.FindModule(first)) == null, "unique identity outside source context must not resolve");
    Check(context.Resolutions.Single().Status == "missing-in-source-context", "outside-context provenance");
}
var allScoped = manifest.DeepClone();
allScoped["RequireSourceContexts"] = true;
allScoped["Contexts"] = JsonSerializer.SerializeToNode(new[] { left, right, newer, first, second }.Select(p => new { Source = p, Directories = new[] { output } }));
using (var context = new PinnedSourceContext(Save(allScoped))) {
    Check(context.Resolve(new AssemblyNameInfo(redirected), context.FindModule(first))?.ManifestModule.Location == newer, "scoped unique target");
    Check(context.Resolve(new AssemblyNameInfo(requested), context.FindModule(first)) == null, "same-directory twins remain ambiguous");
    Check(context.Resolutions.Single(r => r.Identity == requested).Status == "ambiguous-in-source-context", "scoped ambiguity provenance");
    Check(context.Resolve(new AssemblyNameInfo(redirected), null) == null, "required context must not bypass caller scope");
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
    ["duplicate-config"] = n => n["Configs"] = JsonSerializer.SerializeToNode(Enumerable.Repeat(new { Source = first, Path = config, Sha256 = Hash(config) }, 2)),
    ["redirect-binding-without-config"] = n => n["Bindings"] = redirectedBinding["Bindings"]!.DeepClone(),
    ["wrong-redirect-request"] = n => { n["Configs"] = configured["Configs"]!.DeepClone(); n["Bindings"] = redirectedBinding["Bindings"]!.DeepClone(); n["Bindings"]![0]!["RequestedIdentity"] = redirected; },
    ["binding-outside-context"] = n => { n["Contexts"] = scoped["Contexts"]!.DeepClone(); n["Bindings"] = bound["Bindings"]!.DeepClone(); },
    ["required-context-missing"] = n => n["RequireSourceContexts"] = true,
    ["duplicate-context"] = n => n["Contexts"] = JsonSerializer.SerializeToNode(Enumerable.Repeat(new { Source = first, Directories = new[] { output } }, 2)),
    ["duplicate-search-directory"] = n => n["Contexts"] = JsonSerializer.SerializeToNode(new[] { new { Source = first, Directories = new[] { output, output + Path.DirectorySeparatorChar } } }),
    ["null-search-contexts"] = n => n["Contexts"] = null
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
// Exercise preparation with competing physical identities and explicit config
// overrides. Additional metadata must never silently become source inputs.
string preparationRoot = Path.Combine(output, "preparation-input"), compatibility = Path.Combine(preparationRoot, "compat"), framework = Path.Combine(output, "framework");
Directory.CreateDirectory(compatibility); Directory.CreateDirectory(framework);
string host = Emit("preparation-input/host.dll", "Host", 1, requested);
string oldDependency = Emit("preparation-input/old.dll", "Shared", 1);
string oldTwin = Emit("preparation-input/twin.dll", "Shared", 1);
string compatHost = Emit("preparation-input/compat/host.dll", "CompatHost", 1, requested);
string compatDependency = Emit("preparation-input/compat/shared.dll", "Shared", 1);
string frameworkDependency = Emit("framework/shared.dll", "Shared", 3);
string netModule = Path.Combine(framework, "standalone.dll");
using (var module = new ModuleDefUser("standalone") { Mvid = Guid.NewGuid(), Kind = ModuleKind.NetModule }) module.Write(netModule);
string loaderXml = Path.Combine(output, "loaders.xml");
var loaders = new System.Xml.Linq.XDocument(new System.Xml.Linq.XElement("AssemblyContexts",
    new System.Xml.Linq.XElement("Context", new System.Xml.Linq.XAttribute("Source", compatHost), new System.Xml.Linq.XAttribute("Directory", compatibility))));
loaders.Save(loaderXml);
JsonNode PrepPin(string path, bool export) { var node = JsonSerializer.SerializeToNode(Pin(path))!; node["ExportInput"] = export; return node; }
var prepSeed = JsonSerializer.SerializeToNode(new { Format = 1, InputDirectory = preparationRoot,
    Assemblies = new[] { PrepPin(host, true), PrepPin(compatHost, true), PrepPin(oldDependency, false) },
    Bindings = new[] { new { Source = host, Identity = requested, Target = oldDependency } } })!;
string prepSeedPath = Save(prepSeed), prepared = Path.Combine(output, "prepared.json");
string[] prepOptions = ["--contexts=" + loaderXml, "--app-config=" + config, "--framework=" + framework];
var prepHashes = new[] { host, compatHost, oldDependency, oldTwin, compatDependency, frameworkDependency, netModule }.ToDictionary(p => p, Hash);
Check(PhysicalContextPreparation.Run(prepSeedPath, prepared, prepOptions) == 0, "native preparation succeeds");
using (var context = new PinnedSourceContext(prepared)) {
    Check(context.ExportInputs.Count() == 2 && context.Entries.Length == 6, "only seed source inputs export; new metadata remains read-only");
    Check(context.RequireSourceContexts && context.SearchContexts.Length == 6, "all prepared physical assemblies scoped");
    Check(context.Resolve(new AssemblyNameInfo(requested), context.FindModule(host))?.ManifestModule.Location == frameworkDependency, "pinned main redirect precedes identity target selection");
    Check(context.Resolve(new AssemblyNameInfo(requested), context.FindModule(compatHost))?.ManifestModule.Location == compatDependency, "explicit no-config compatibility source overrides main config");
    Check(context.ConfigEntries.All(c => c.Source != compatHost && c.Source != compatDependency), "compatibility no-config directory inheritance");
    Check(context.Resolve(new AssemblyNameInfo(requested), context.FindModule(compatDependency))?.ManifestModule.Location == compatDependency, "compatibility physical self remains distinct");
}
using (var report = JsonDocument.Parse(File.ReadAllBytes(prepared + ".preparation.json"))) {
    Check(report.RootElement.GetProperty("RetainedNetModules").GetArrayLength() == 1, "netmodule retained outside assembly resolver candidates");
    Check(report.RootElement.GetProperty("OutputSha256").GetString() == Hash(prepared), "published manifest hash bound to preparation evidence");
    Check(report.RootElement.GetProperty("Requests").EnumerateArray().Any(r => r.GetProperty("Target").ValueKind == JsonValueKind.Null), "missing framework metadata stays explicit");
}
Check(prepHashes.All(p => Hash(p.Key) == p.Value), "preparation leaves all fixture binaries untouched");
// A previously proven twin binding must survive when its original host has no
// redirect. The same source under a different config is a distinct preparation.
var unconfiguredLoaders = new System.Xml.Linq.XDocument(loaders);
unconfiguredLoaders.Root!.Add(new System.Xml.Linq.XElement("Context", new System.Xml.Linq.XAttribute("Source", host), new System.Xml.Linq.XAttribute("Directory", preparationRoot)));
unconfiguredLoaders.Save(loaderXml);
string preserved = Path.Combine(output, "preserved.json");
PhysicalContextPreparation.Run(prepSeedPath, preserved, prepOptions);
using (var context = new PinnedSourceContext(preserved)) {
    Check(context.Resolve(new AssemblyNameInfo(requested), context.FindModule(host))?.ManifestModule.Location == oldDependency, "proven exact twin binding retained");
    Check(context.Entries.Single(p => p.Path == oldTwin).ExportInput == false, "same-identity twin not conflated with source scope");
}
void RejectPreparation(string message, string seed, string target, string[] options) {
    bool rejected = false;
    try { PhysicalContextPreparation.Run(seed, target, options); } catch (Exception ex) when (ex is InvalidDataException or IOException or ArgumentException or System.Xml.XmlException) { rejected = true; }
    Check(rejected, "preparation rejects " + message);
    Check(!File.Exists(target) && !File.Exists(target + ".pending") && !File.Exists(target + ".preparation.json"), "no publication after " + message);
}
RejectPreparation("inside-input output", prepSeedPath, Path.Combine(preparationRoot, "forbidden.json"), prepOptions);
var staleSeed = prepSeed.DeepClone(); staleSeed["Assemblies"]![0]!["Sha256"] = new string('0', 64);
RejectPreparation("stale seed", Save(staleSeed), Path.Combine(output, "stale-prepared.json"), prepOptions);
RejectPreparation("missing search directory", prepSeedPath, Path.Combine(output, "missing-directory.json"), prepOptions.Concat(["--support=" + Path.Combine(output, "absent")]).ToArray());
RejectPreparation("unknown option", prepSeedPath, Path.Combine(output, "unknown-option.json"), prepOptions.Concat(["--unknown=true"]).ToArray());
unconfiguredLoaders.Root!.Add(new System.Xml.Linq.XElement(unconfiguredLoaders.Root.Elements().First())); unconfiguredLoaders.Save(loaderXml);
RejectPreparation("duplicate loader source", prepSeedPath, Path.Combine(output, "duplicate-loader.json"), prepOptions);
File.WriteAllText(loaderXml, "<!DOCTYPE AssemblyContexts [<!ENTITY x SYSTEM 'file:///missing'>]><AssemblyContexts>&x;</AssemblyContexts>");
RejectPreparation("DTD", prepSeedPath, Path.Combine(output, "dtd.json"), prepOptions);
string existingHash = Hash(prepared); bool replacementRejected = false;
try { PhysicalContextPreparation.Run(prepSeedPath, prepared, prepOptions); } catch (IOException) { replacementRejected = true; }
Check(replacementRejected && Hash(prepared) == existingHash, "existing preparation preserved");
File.WriteAllText(Path.Combine(output, "proof.json"), JsonSerializer.Serialize(new { Checks = checks, Manifest = manifest, ToolSha256 = Hash(typeof(PinnedSourceContext).Assembly.Location) }, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine($"PASS: {checks} pinned physical-context and redirect guards.");
