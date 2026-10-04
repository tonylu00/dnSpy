using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Xml;
using System.Xml.Linq;
using dnlib.DotNet;

// Read-only metadata preparation. Only manifests/reports are written; no
// application source, assembly, map or resource is rewritten.
internal static class PhysicalContextPreparation {
    sealed record Metadata(PinnedSourceContext.Entry Pin, string[] Requests);
    sealed record LoaderContext(string Source, string Directory, string? Config);
    sealed record RetainedFile(string Path, string Sha256, Guid? Mvid, string Reason);
    static readonly StringComparer Paths = OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal;
    static readonly JsonSerializerOptions Json = new() { WriteIndented = true };
    static string Hash(string path) { using var stream = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(stream)); }
    static string DirectoryPath(string path) => Path.TrimEndingDirectorySeparator(Path.GetFullPath(path));
    static bool Within(string root, string path) {
        string relative = Path.GetRelativePath(root, path);
        return !Path.IsPathRooted(relative) && relative != ".." && !relative.StartsWith(".." + Path.DirectorySeparatorChar, StringComparison.Ordinal);
    }
    public static int Run(string seedPath, string output, string[] options) {
        var watch = Stopwatch.StartNew();
        seedPath = Path.GetFullPath(seedPath); output = Path.GetFullPath(output);
        string reportPath = output + ".preparation.json", pending = output + ".pending";
        if (new[] { output, reportPath, pending }.Any(p => File.Exists(p) || Directory.Exists(p))) throw new IOException("Choose a fresh context/report path.");
        string? Option(string name) => options.SingleOrDefault(o => o.StartsWith(name, StringComparison.Ordinal))?[name.Length..];
        string contextsPath = Path.GetFullPath(Option("--contexts=") ?? throw new ArgumentException("Supply the explicit loader context manifest."));
        string rootConfig = Path.GetFullPath(Option("--app-config=") ?? throw new ArgumentException("Supply the explicit main application config."));
        string[] framework = options.Where(o => o.StartsWith("--framework=")).Select(o => DirectoryPath(o[12..])).Distinct(Paths).ToArray();
        string[] support = options.Where(o => o.StartsWith("--support=")).Select(o => DirectoryPath(o[10..])).Distinct(Paths).ToArray();
        if (framework.Length == 0 || options.Any(o => !new[] { "--contexts=", "--app-config=", "--framework=", "--support=" }.Any(o.StartsWith))) throw new ArgumentException("Unknown/missing context preparation option.");
        string seedHash = Hash(seedPath), contextsHash = Hash(contextsPath), rootConfigHash = Hash(rootConfig);
        string root;
        PinnedSourceContext.Entry[] initial;
        using (var seed = new PinnedSourceContext(seedPath)) {
            root = seed.InputDirectory ?? throw new InvalidDataException("Seed must pin the application input directory."); initial = seed.Entries;
            seed.Verify();
        }
        if (Within(root, output) || Within(root, reportPath)) throw new IOException("Write context evidence outside the application input tree.");
        using var reader = XmlReader.Create(contextsPath, new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null });
        var xml = XDocument.Load(reader).Root;
        if (xml?.Name != "AssemblyContexts") throw new InvalidDataException("Expected AssemblyContexts root.");
        string xmlDirectory = Path.GetDirectoryName(contextsPath)!;
        string Full(XElement e, string name) => Path.GetFullPath((string?)e.Attribute(name) ?? throw new InvalidDataException("Missing loader context " + name), xmlDirectory);
        var loaders = new Dictionary<string, LoaderContext>(Paths);
        foreach (var row in xml.Elements()) {
            if (row.Name != "Context") throw new InvalidDataException("Unknown loader context element.");
            var context = new LoaderContext(Full(row, "Source"), DirectoryPath(Full(row, "Directory")), row.Attribute("Config") == null ? null : Full(row, "Config"));
            if (!Within(root, context.Source) || !Within(root, context.Directory) || !Directory.Exists(context.Directory) || !loaders.TryAdd(context.Source, context)) throw new InvalidDataException("Invalid/duplicate loader context source.");
        }
        var files = new HashSet<string>(initial.Select(e => e.Path), Paths);
        var nativeFiles = new List<RetainedFile>();
        var netModules = new List<RetainedFile>();
        void Scan(string directory, bool recursive) {
            if (!Directory.Exists(directory)) throw new DirectoryNotFoundException(directory);
            foreach (string path in Directory.EnumerateFiles(directory, "*", new EnumerationOptions { RecurseSubdirectories = recursive, AttributesToSkip = System.IO.FileAttributes.ReparsePoint, IgnoreInaccessible = false }))
                if (Path.GetExtension(path).Equals(".dll", StringComparison.OrdinalIgnoreCase) || Path.GetExtension(path).Equals(".exe", StringComparison.OrdinalIgnoreCase)) files.Add(Path.GetFullPath(path));
        }
        Scan(root, true); foreach (string path in framework) Scan(path, true); foreach (string path in support) Scan(path, false);
        var initialPins = initial.ToDictionary(e => e.Path, Paths);
        var modules = new Dictionary<string, Metadata>(Paths);
        foreach (string path in files.OrderBy(p => p, Paths)) {
            string before = Hash(path);
            using (var pe = new dnlib.PE.PEImage(path)) {
                if ((uint)pe.ImageNTHeaders.OptionalHeader.DataDirectories[14].VirtualAddress == 0) {
                    nativeFiles.Add(new(path, before, null, "native PE retained; not an assembly resolver candidate")); continue;
                }
            }
            using var module = ModuleDefMD.Load(path);
            if (module.Assembly == null) {
                if (Hash(path) != before) throw new InvalidDataException("Netmodule changed during preparation: " + path);
                netModules.Add(new(path, before, module.Mvid, "standalone netmodule has no assembly identity; retained, not an assembly resolver candidate"));
                continue;
            }
            if (module.Mvid == null) throw new InvalidDataException("Managed dependency lacks MVID: " + path);
            var pin = new PinnedSourceContext.Entry(path, module.Assembly.FullName, module.Mvid.Value.ToString(), before, initialPins.TryGetValue(path, out var original) && original.ExportInput);
            if (original != null && (original.Identity != pin.Identity || Guid.Parse(original.Mvid) != module.Mvid || !StringComparer.OrdinalIgnoreCase.Equals(original.Sha256, pin.Sha256))) throw new InvalidDataException("Seed physical input changed: " + path);
            if (Hash(path) != before) throw new InvalidDataException("Metadata input changed during preparation: " + path);
            modules.Add(path, new Metadata(pin, module.GetAssemblyRefs().Select(a => a.FullName).Distinct(StringComparer.Ordinal).OrderBy(i => i, StringComparer.Ordinal).ToArray()));
        }
        if (initial.Any(e => !modules.ContainsKey(e.Path)) || loaders.Keys.Any(p => !modules.ContainsKey(p))) throw new InvalidDataException("Seed/loader source is not an exact inventoried assembly.");
        string[] shared = new[] { root }.Concat(support).Concat(framework.SelectMany(p => new[] { p, Path.Combine(p, "Facades") }.Where(Directory.Exists))).Distinct(Paths).ToArray();
        var scopes = new List<PinnedSourceContext.SourceSearchContext>();
        var configs = new List<PinnedSourceContext.SourceConfig>();
        var configParsers = new Dictionary<string, dnSpy_Console.ApplicationConfigResolver>(Paths);
        var unresolvedContexts = new List<object>();
        foreach (var module in modules.Values.OrderBy(m => m.Pin.Path, Paths)) {
            string ownDirectory = Path.GetDirectoryName(module.Pin.Path)!;
            string? config = null;
            string directory = ownDirectory;
            if (loaders.TryGetValue(module.Pin.Path, out var loader)) { directory = loader.Directory; config = loader.Config; }
            else if (Paths.Equals(ownDirectory, root)) config = rootConfig;
            else if (Within(root, module.Pin.Path)) {
                var possible = loaders.Values.Where(l => Paths.Equals(l.Directory, ownDirectory)).Select(l => l.Config).Distinct(Paths).ToArray();
                if (possible.Length == 1) config = possible[0];
                else if (possible.Length > 1) unresolvedContexts.Add(new { Source = module.Pin.Path, Reason = "multiple explicit host configurations in physical dependency directory" });
            }
            scopes.Add(new PinnedSourceContext.SourceSearchContext(module.Pin.Path, new[] { directory }.Concat(shared).Distinct(Paths).ToArray()));
            if (config != null) {
                string hash = Hash(config);
                configs.Add(new PinnedSourceContext.SourceConfig(module.Pin.Path, config, hash));
                if (!configParsers.ContainsKey(config)) configParsers.Add(config, new dnSpy_Console.ApplicationConfigResolver(new NoResolver(), config));
            }
        }
        // Preserve previously proven physical bindings; select new targets only
        // from the ordered explicitly configured directories and full identities.
        using var seedReader = JsonDocument.Parse(File.ReadAllBytes(seedPath));
        string seedDirectory = Path.GetDirectoryName(seedPath)!;
        var proven = seedReader.RootElement.TryGetProperty("Bindings", out var oldBindings) ? JsonSerializer.Deserialize<PinnedSourceContext.Binding[]>(oldBindings.GetRawText())!
            .Select(b => b with { Source = Path.GetFullPath(b.Source, seedDirectory), Target = Path.GetFullPath(b.Target, seedDirectory) }).ToArray() : [];
        var identities = modules.Values.GroupBy(m => m.Pin.Identity, StringComparer.Ordinal).ToDictionary(g => g.Key, g => g.ToArray(), StringComparer.Ordinal);
        var configBySource = configs.ToDictionary(c => c.Source, Paths);
        var bindings = new Dictionary<(string Source, string Identity), PinnedSourceContext.Binding>();
        foreach (var scope in scopes) foreach (string requested in modules[scope.Source].Requests) {
            string effective = configBySource.TryGetValue(scope.Source, out var config) ? configParsers[config.Path].GetEffectiveIdentity(new AssemblyNameInfo(requested)).FullName : requested;
            string? target = proven.Where(b => Paths.Equals(b.Source, scope.Source) && b.Identity == effective && (b.RequestedIdentity ?? b.Identity) == requested).Select(b => Path.GetFullPath(b.Target)).SingleOrDefault();
            if (target == null && identities.TryGetValue(effective, out var candidates)) foreach (string directory in scope.Directories) {
                var matches = candidates.Where(m => Paths.Equals(Path.GetDirectoryName(m.Pin.Path), directory)).ToArray();
                if (matches.Length == 0) continue;
                if (matches.Length == 1) target = matches[0].Pin.Path;
                break;
            }
            if (target == null || effective == modules[scope.Source].Pin.Identity) continue;
            var binding = new PinnedSourceContext.Binding(scope.Source, effective, target, effective == requested ? null : requested);
            if (bindings.TryGetValue((scope.Source, effective), out var existing) && existing.Target != target) throw new InvalidDataException("Conflicting physical dependency targets.");
            bindings.TryAdd((scope.Source, effective), binding);
        }
        var manifest = new { Format = 1, InputDirectory = root, RequireSourceContexts = true, Assemblies = modules.Values.Select(m => m.Pin).OrderBy(p => p.Path, Paths).ToArray(), Contexts = scopes, Configs = configs, Bindings = bindings.Values.OrderBy(b => b.Source, Paths).ThenBy(b => b.Identity, StringComparer.Ordinal).ToArray() };
        Directory.CreateDirectory(Path.GetDirectoryName(output)!);
        try {
            using (var stream = new FileStream(pending, FileMode.CreateNew, FileAccess.Write)) JsonSerializer.Serialize(stream, manifest, Json);
            PinnedSourceContext.Resolution[] resolutions;
            using (var check = new PinnedSourceContext(pending)) {
                foreach (var metadata in modules.Values) foreach (string request in metadata.Requests) check.Resolve(new AssemblyNameInfo(request), check.FindModule(metadata.Pin.Path));
                check.Verify(); resolutions = check.Resolutions;
            }
            if (Hash(seedPath) != seedHash || Hash(contextsPath) != contextsHash || Hash(rootConfig) != rootConfigHash) throw new InvalidDataException("Context preparation input changed.");
            foreach (var retained in nativeFiles.Concat(netModules)) if (Hash(retained.Path) != retained.Sha256) throw new InvalidDataException("Retained physical input changed: " + retained.Path);
            string preparedHash = Hash(pending);
            var report = new { Format = 1, Kind = "PhysicalSourceContextPreparation", Seed = seedPath, SeedSha256 = seedHash, LoaderContexts = contextsPath, LoaderContextsSha256 = contextsHash, RootConfig = rootConfig, RootConfigSha256 = rootConfigHash, FrameworkDirectories = framework, SupportDirectories = support, Output = output, OutputSha256 = preparedHash, Assemblies = manifest.Assemblies.Length, ExportInputs = manifest.Assemblies.Count(p => p.ExportInput), NativeFiles = nativeFiles, RetainedNetModules = netModules, Configs = configs, UnresolvedSourceContexts = unresolvedContexts, Requests = resolutions, ElapsedSeconds = watch.Elapsed.TotalSeconds, PeakWorkingSetBytes = Process.GetCurrentProcess().PeakWorkingSet64, Limits = "Physical metadata only; explicit ordered search directories and pinned redirects. No GAC/ambient/name-only resolution, exports, map changes or source/binary patches. Missing/ambiguous requests remain explicit; no whole-application merge or runtime verdict." };
            using (var stream = new FileStream(reportPath, FileMode.CreateNew, FileAccess.Write)) JsonSerializer.Serialize(stream, report, Json);
            File.Move(pending, output);
            Console.WriteLine($"PASS: {manifest.Assemblies.Length} physical assemblies, {manifest.Assemblies.Count(p => p.ExportInput)} export inputs, {resolutions.Count(r => r.Target == null)} unresolved requests; {watch.Elapsed.TotalSeconds:F2}s.");
            return 0;
        }
        finally { if (File.Exists(pending)) File.Delete(pending); }
    }
    sealed class NoResolver : IAssemblyResolver { public AssemblyDef? Resolve(IAssembly assembly, ModuleDef? sourceModule) => null; }
}
