using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Text.Json;
using dnlib.DotNet;

// Portable metadata-only resolver. Paths and complete identities are explicit;
// physically distinct twins are never collapsed into a dnlib identity cache.
internal sealed class PinnedSourceContext : IAssemblyResolver, IDisposable {
    public sealed record Entry(string Path, string Identity, string Mvid, string Sha256, bool ExportInput = false);
    public sealed record Binding(string Source, string Identity, string Target, string? RequestedIdentity = null);
    public sealed record SourceSearchContext(string Source, string[] Directories);
    public sealed record Resolution(string Source, string Identity, string? Target, string Status, string? EffectiveIdentity = null, string? ConfigPath = null);
    public sealed record SourceConfig(string Source, string Path, string Sha256);
    sealed class Manifest {
        public int Format { get; set; }
        public string? InputDirectory { get; set; }
        public Entry[] Assemblies { get; set; } = [];
        public Binding[] Bindings { get; set; } = [];
        public SourceConfig[] Configs { get; set; } = [];
        public SourceSearchContext[] Contexts { get; set; } = [];
        public bool RequireSourceContexts { get; set; }
    }
    static readonly StringComparer Paths = OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal;
    readonly Dictionary<string, ModuleDefMD> modules = new(Paths);
    readonly Dictionary<(ModuleDef Source, string Identity), ModuleDefMD> bindings = new();
    readonly Dictionary<ModuleDef, ConfiguredResolver> configs = new();
    readonly Dictionary<ModuleDef, string[]> searchContexts = new();
    Dictionary<string, ModuleDefMD[]> identities = new(StringComparer.Ordinal);
    readonly ConcurrentDictionary<(ModuleDef? Source, string Identity), Resolution> resolutions = new();
    public string? ManifestPath { get; }
    public string? ManifestHash { get; }
    public string? InputDirectory { get; }
    public Entry[] Entries { get; } = [];
    public SourceConfig[] ConfigEntries { get; } = [];
    public SourceSearchContext[] SearchContexts { get; } = [];
    public bool RequireSourceContexts { get; }
    public ModuleContext Context { get; }
    public IEnumerable<ModuleDef> ExportInputs => Entries.Where(e => e.ExportInput).Select(e => modules[e.Path]);
    public Resolution[] Resolutions => resolutions.Values.OrderBy(r => r.Source, Paths).ThenBy(r => r.Identity, StringComparer.Ordinal).ToArray();
    public ModuleDefMD? FindModule(string path) => modules.TryGetValue(Path.GetFullPath(path), out var found) ? found : null;

    public PinnedSourceContext(string? path) {
        Context = new ModuleContext(this);
        if (path == null) return;
        ManifestPath = Path.GetFullPath(path);
        ManifestHash = Hash(ManifestPath);
        var manifest = JsonSerializer.Deserialize<Manifest>(File.ReadAllBytes(ManifestPath));
        if (manifest?.Format != 1 || manifest.Assemblies == null || manifest.Bindings == null || manifest.Configs == null || manifest.Contexts == null) throw new InvalidDataException("Expected reference manifest Format=1.");
        if (manifest.Contexts.Any(c => c == null || c.Directories == null)) throw new InvalidDataException("Invalid source search context directories.");
        string directory = Path.GetDirectoryName(ManifestPath)!;
        InputDirectory = manifest.InputDirectory == null ? null : Path.GetFullPath(manifest.InputDirectory, directory);
        Entries = manifest.Assemblies.Select(e => e with { Path = Path.GetFullPath(e.Path, directory) }).ToArray();
        ConfigEntries = manifest.Configs.Select(e => e with { Source = Path.GetFullPath(e.Source, directory), Path = Path.GetFullPath(e.Path, directory) }).ToArray();
        RequireSourceContexts = manifest.RequireSourceContexts;
        SearchContexts = manifest.Contexts.Select(e => e with { Source = Path.GetFullPath(e.Source, directory), Directories = e.Directories.Select(d => Path.TrimEndingDirectorySeparator(Path.GetFullPath(d, directory))).ToArray() }).ToArray();
        try {
            foreach (var entry in Entries) {
                if (modules.ContainsKey(entry.Path)) throw new InvalidDataException("Duplicate physical reference path: " + entry.Path);
                if (entry.ExportInput && (InputDirectory == null || !Within(InputDirectory, entry.Path)))
                    throw new InvalidDataException("Export input outside pinned input directory: " + entry.Path);
                if (!StringComparer.OrdinalIgnoreCase.Equals(Hash(entry.Path), entry.Sha256)) throw new InvalidDataException("Stale reference hash: " + entry.Path);
                var loaded = ModuleDefMD.Load(entry.Path, Context);
                if (loaded.Assembly?.FullName != entry.Identity || loaded.Mvid != Guid.Parse(entry.Mvid)) {
                    loaded.Dispose(); throw new InvalidDataException("Invalid/duplicate reference identity: " + entry.Path);
                }
                loaded.EnableTypeDefFindCache = true;
                modules.Add(entry.Path, loaded);
            }
            identities = modules.Values.GroupBy(m => m.Assembly.FullName, StringComparer.Ordinal).ToDictionary(g => g.Key, g => g.ToArray(), StringComparer.Ordinal);
            foreach (var scope in SearchContexts) {
                var source = FindModule(scope.Source);
                if (source == null || scope.Directories.Length == 0 || scope.Directories.Distinct(Paths).Count() != scope.Directories.Length ||
                    scope.Directories.Any(d => !Directory.Exists(d)) || !searchContexts.TryAdd(source, scope.Directories))
                    throw new InvalidDataException("Invalid/duplicate source search context: " + scope.Source);
            }
            if (RequireSourceContexts && modules.Values.Any(m => !searchContexts.ContainsKey(m))) throw new InvalidDataException("Missing required source search context.");
            foreach (var config in ConfigEntries) {
                var source = FindModule(config.Source);
                if (source == null || Hash(config.Path) != config.Sha256 || !configs.TryAdd(source,
                    new ConfiguredResolver(this, config.Path)))
                    throw new InvalidDataException("Invalid/duplicate pinned source config: " + config.Source);
            }
            foreach (var binding in manifest.Bindings) {
                var source = FindModule(Path.GetFullPath(binding.Source, directory));
                var target = FindModule(Path.GetFullPath(binding.Target, directory));
                var request = source?.GetAssemblyRefs().FirstOrDefault(a => a.FullName == (binding.RequestedIdentity ?? binding.Identity));
                string? effective = request == null ? null : configs.TryGetValue(source!, out var configured) ? configured.GetEffectiveIdentity(request).FullName : request.FullName;
                if (source == null || target == null || target.Assembly.FullName != binding.Identity || effective != binding.Identity ||
                    searchContexts.TryGetValue(source, out var paths) && !paths.Contains(Path.GetDirectoryName(target.Location)!, Paths) ||
                    !bindings.TryAdd((source, binding.Identity), target))
                    throw new InvalidDataException("Invalid/duplicate physical context binding: " + binding.Source + " -> " + binding.Identity);
            }
            Verify();
        }
        catch { Dispose(); throw; }
    }

    public AssemblyDef? Resolve(IAssembly assembly, ModuleDef? sourceModule) {
        if (sourceModule != null && configs.TryGetValue(sourceModule, out var configured)) return configured.Resolve(assembly, sourceModule);
        return ResolveUnredirected(assembly, sourceModule);
    }
    AssemblyDef? ResolveUnredirected(IAssembly assembly, ModuleDef? sourceModule) {
        if (assembly == null) return null;
        string identity = assembly.FullName;
        ModuleDef? selected = null;
        string status;
        if (sourceModule?.Assembly?.FullName == identity) { selected = sourceModule; status = "self"; }
        else if (sourceModule != null && bindings.TryGetValue((sourceModule, identity), out var bound)) { selected = bound; status = "explicit-physical-binding"; }
        else if (sourceModule != null && searchContexts.TryGetValue(sourceModule, out var directories)) {
            status = "missing-in-source-context";
            if (identities.TryGetValue(identity, out var scopedCandidates)) foreach (string directory in directories) {
                var matches = scopedCandidates.Where(m => Paths.Equals(Path.GetDirectoryName(m.Location), directory)).ToArray();
                if (matches.Length == 0) continue;
                if (matches.Length == 1) { selected = matches[0]; status = "source-context-pinned-identity"; }
                else status = "ambiguous-in-source-context";
                break;
            }
        }
        else if (RequireSourceContexts) status = "missing-required-source-context";
        else if (identities.TryGetValue(identity, out var candidates) && candidates.Length == 1) { selected = candidates[0]; status = "unique-pinned-identity"; }
        else status = identities.ContainsKey(identity) ? "ambiguous-physical-identity" : "missing-pinned-identity";
        resolutions.TryAdd((sourceModule, identity), new Resolution(sourceModule?.Location ?? "", identity, selected?.Location, status));
        return selected?.Assembly;
    }
    public void Verify() {
        if (ManifestPath != null && Hash(ManifestPath) != ManifestHash) throw new InvalidDataException("Reference manifest changed.");
        foreach (var entry in Entries) if (!StringComparer.OrdinalIgnoreCase.Equals(Hash(entry.Path), entry.Sha256)) throw new InvalidDataException("Physical reference changed: " + entry.Path);
        foreach (var config in ConfigEntries) if (Hash(config.Path) != config.Sha256) throw new InvalidDataException("Pinned source config changed: " + config.Path);
    }
    public void Dispose() { foreach (var module in modules.Values) module.Dispose(); modules.Clear(); }
    static bool Within(string root, string path) {
        string relative = Path.GetRelativePath(root, path);
        return !Path.IsPathRooted(relative) && relative != ".." && !relative.StartsWith(".." + Path.DirectorySeparatorChar, StringComparison.Ordinal);
    }
    static string Hash(string path) { using var stream = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(stream)); }
    // Retain both requested and effective identities. A redirect is evidence of
    // one pinned host configuration, never general assembly equivalence.
    sealed class ConfiguredResolver : IAssemblyResolver {
        readonly PinnedSourceContext owner;
        readonly string path;
        readonly dnSpy_Console.ApplicationConfigResolver parser;
        readonly UnredirectedResolver raw;
        public ConfiguredResolver(PinnedSourceContext owner, string path) {
            this.owner = owner; this.path = path;
            raw = new UnredirectedResolver(owner);
            parser = new dnSpy_Console.ApplicationConfigResolver(raw, path);
        }
        public IAssembly GetEffectiveIdentity(IAssembly assembly) => parser.GetEffectiveIdentity(assembly);
        public AssemblyDef? Resolve(IAssembly assembly, ModuleDef? sourceModule) {
            lock (raw) {
                raw.LastIdentity = null;
                var result = parser.Resolve(assembly, sourceModule!);
                string effective = raw.LastIdentity ?? assembly.FullName;
                var observed = owner.resolutions[(sourceModule, effective)];
                owner.resolutions[(sourceModule, assembly.FullName)] = observed with {
                    Identity = assembly.FullName, EffectiveIdentity = effective, ConfigPath = path
                };
                return result;
            }
        }
    }
    sealed class UnredirectedResolver : IAssemblyResolver {
        readonly PinnedSourceContext owner;
        public string? LastIdentity;
        public UnredirectedResolver(PinnedSourceContext owner) => this.owner = owner;
        public AssemblyDef? Resolve(IAssembly assembly, ModuleDef? sourceModule) {
            LastIdentity = assembly.FullName;
            return owner.ResolveUnredirected(assembly, sourceModule);
        }
    }
}

namespace dnSpy_Console { sealed class ErrorException : Exception { public ErrorException(string message) : base(message) { } } }
