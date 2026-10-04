using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Diagnostics;
using System.Reflection;
using System.Runtime.Loader;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text;
using System.Threading;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler.Ast;

internal static class Program {
    static string runtime = "";
    static readonly Dictionary<string, string> dependencies = new(StringComparer.OrdinalIgnoreCase);
    static readonly JsonSerializerOptions json = new() { WriteIndented = true };

    static int Main(string[] args) {
        try {
            if (args.Length < 4) throw new ArgumentException("Usage: GeneratedSourceInspection <actual-plugin-runtime> <input> <new-report> <inspect|self-test> [--root=0xTOKEN|--method=0xTOKEN] [--no-async|--no-yield|--no-anon-methods|--show-all|--declare-state-machines]");
            runtime = Path.GetFullPath(args[0]);
            foreach (string name in new[] { "dnlib", "dnSpy.Contracts.Logic", "ICSharpCode.Decompiler" }) {
                string path = Path.Combine(runtime, name + ".dll");
                if (Hash(path) != Hash(Path.Combine(AppContext.BaseDirectory, name + ".dll")))
                    throw new InvalidDataException("Host references must be byte-identical to actual plugin dependencies: " + name);
                dependencies[path] = Hash(path);
            }
            AssemblyLoadContext.Default.Resolving += (_, name) => {
                string path = Path.Combine(runtime, name.Name + ".dll");
                if (!File.Exists(path) || AssemblyName.GetAssemblyName(path).FullName != name.FullName) return null;
                dependencies[path] = Hash(path);
                return AssemblyLoadContext.Default.LoadFromAssemblyPath(path);
            };
            int result = 1;
            Exception? error = null;
            // Match exporter stack sizing; deep generic/AST traversal must not
            // depend on the host's small default stack. One physical module at a time.
            var worker = new Thread(() => { try { result = Run(args); } catch (Exception ex) { error = ex; } }, 64 * 1024 * 1024);
            worker.Start(); worker.Join();
            if (error != null) throw error;
            return result;
        }
        catch (Exception ex) { Console.Error.WriteLine(ex); return 1; }
    }

    static int Run(string[] args) {
        string input = Path.GetFullPath(args[1]), output = Path.GetFullPath(args[2]);
        if (File.Exists(output) || Directory.Exists(output)) throw new IOException("Choose a new report path.");
        if (StringComparer.OrdinalIgnoreCase.Equals(input, output) || output.StartsWith(Path.GetDirectoryName(input)! + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
            throw new IOException("Write reports outside the inspected application tree.");
        string initialHash = Hash(input);
        var stopwatch = Stopwatch.StartNew();
        // Only explicitly pinned physical references; no ambient/GAC/name-only fallback.
        string[] options = args.Skip(4).ToArray();
        string? sourceOutput = options.SingleOrDefault(o => o.StartsWith("--source="))?[9..];
        if (sourceOutput != null) {
            sourceOutput = Path.GetFullPath(sourceOutput);
            if (File.Exists(sourceOutput) || Directory.Exists(sourceOutput) || StringComparer.OrdinalIgnoreCase.Equals(sourceOutput, output) ||
                sourceOutput.StartsWith(Path.GetDirectoryName(input)! + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                throw new IOException("Choose a new source output outside the inspected application tree.");
        }
        using var references = new PinnedReferences(options.SingleOrDefault(o => o.StartsWith("--references="))?[13..]);
        using var module = ModuleDefMD.Load(input, new ModuleCreationOptions(references.Context));
        var originals = module.GetTypes().SelectMany(t => new IMemberDef[] { t }.Concat(t.Methods).Concat(t.Fields).Concat(t.Properties).Concat(t.Events))
            .OrderBy(d => d.MDToken.Raw).Select(d => new { Token = d.MDToken.Raw, d.FullName, OriginalName = d.Name.String }).ToArray();
        var decompiler = CreateDecompiler();
        foreach (string option in options.Where(o => !o.StartsWith("--root=") && !o.StartsWith("--method=") && !o.StartsWith("--references=") && !o.StartsWith("--source="))) {
            bool value = !option.StartsWith("--no-");
            string name = option[(value ? 2 : 5)..];
            (decompiler.Settings.TryGetOption(name) ?? throw new ArgumentException("Unknown option: " + option)).Value = value;
        }
        var reports = new List<GeneratedSourceEvidence>();
        var sourceHashes = new List<object>();
        string? savedSource = null;
        void Record((string Source, GeneratedSourceEvidence? Evidence) result) {
            if (sourceOutput != null && reports.Count != 0) throw new ArgumentException("Source output requires a single selected root/member or self-test.");
            reports.Add(result.Evidence!);
            sourceHashes.Add(new { result.Evidence!.RootTypeToken, SourceSha256 = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(result.Source))), Characters = result.Source.Length });
            if (sourceOutput != null) savedSource = result.Source;
        }
        int checks = 0;
        void Check(bool condition, string message) { checks++; if (!condition) throw new Exception(message); }
        if (args[3] == "self-test") {
            if (options.Any(o => !o.StartsWith("--references=") && !o.StartsWith("--source="))) throw new ArgumentException("Self-test takes no filtering options.");
            var root = module.Types.Single(t => t.Name == "GeneratedSourceFixture" || t.Name == "StateMachineDeclarationFixture");
            var ordinary = Decompile(decompiler, root, false);
            var observed = Decompile(decompiler, root, true);
            var proof = observed.Evidence!;
            Check(ordinary.Evidence == null, "Default decompilation must not collect evidence.");
            Check(ordinary.Source == observed.Source, "Opt-in changed generated source.");
            var sharedContext = new DecompilationContext { AsyncMethodBodyDecompilation = false };
            var sharedFirst = Decompile(decompiler, root, false, sharedContext);
            var sharedObserved = Decompile(decompiler, root, true, sharedContext);
            var sharedLast = Decompile(decompiler, root, false, sharedContext);
            Check(sharedFirst.Evidence == null && sharedLast.Evidence == null, "Evidence leaked through a reused request/cache context.");
            Check(sharedFirst.Source == observed.Source && sharedObserved.Source == observed.Source && sharedLast.Source == observed.Source, "Reused opt-in context changed source.");
            Check(JsonSerializer.Serialize(sharedObserved.Evidence, json) == JsonSerializer.Serialize(proof, json), "Reused cache lost reconstruction annotations.");
            Check(proof.CompleteTypeScope && proof.RootTypeToken == root.MDToken.Raw && proof.ModuleMvid == module.Mvid, "Full physical root scope lost.");
            var witnesses = proof.BodyWitnesses;
            Check(witnesses.Any(w => w.Kind == "AsyncMethod"), "No successful async body observed.");
            Check(witnesses.Any(w => w.Kind == "AnonymousMethod"), "No successful lambda body observed.");
            Check(witnesses.All(w => module.ResolveToken(w.ImplementationToken) is MethodDef && module.ResolveToken(w.OwnerToken) is IMemberDef), "Witness tokens are not physical definitions.");
            var awaitOwner = root.Methods.First(m => m.Name == "Await" || m.Name == "Remove");
            var partial = Decompile(decompiler, awaitOwner, true).Evidence!;
            Check(!partial.CompleteTypeScope && partial.BodyWitnesses.Any(w => w.OwnerToken == awaitOwner.MDToken.Raw), "Member-only decompilation claimed complete scope or lost positive witness.");
            decompiler.Settings.TryGetOption("async")!.Value = false;
            Check(!Decompile(decompiler, root, true).Evidence!.BodyWitnesses.Any(w => w.Kind == "AsyncMethod"), "Disabled reconstruction produced a witness.");
            decompiler.Settings.TryGetOption("async")!.Value = true;
            decompiler.Settings.TryGetOption("anon-methods")!.Value = false;
            Check(!Decompile(decompiler, root, true).Evidence!.BodyWitnesses.Any(w => w.Kind == "AnonymousMethod"), "Disabled lambda reconstruction produced a witness.");
            decompiler.Settings.TryGetOption("anon-methods")!.Value = true;
            decompiler.Settings.TryGetOption("show-all")!.Value = true;
            var retained = Decompile(decompiler, root, true).Evidence!;
            Check(retained.BodyWitnesses.Any(w => retained.DeclarationTokens.Contains(w.ImplementationTypeToken)), "Explicit retained implementation declarations disappeared from evidence.");
            decompiler.Settings.TryGetOption("show-all")!.Value = false;
            if (root.Name == "GeneratedSourceFixture") {
                Check(witnesses.Any(w => w.Kind == "IteratorMethod"), "No iterator rewrite observed.");
                var fake = root.NestedTypes.Single(t => t.Name == "State_NotGenerated");
                Check(proof.DeclarationTokens.Contains(fake.MDToken.Raw) && !witnesses.Any(w => w.ImplementationTypeToken == fake.MDToken.Raw), "Generated-looking spelling counted as reconstruction.");
                var capture = root.Methods.Single(m => m.Name == "Capture");
                Check(proof.FieldBindings.Any(f => f.OwnerToken == capture.MDToken.Raw && f.SourceName == "offset"), "Captured field-to-source parameter evidence lost.");
                var anonymousAsync = module.GetTypes().SelectMany(t => t.Methods)
                    .Where(m => m.CustomAttributes.Any(a => a.TypeFullName == "System.Runtime.CompilerServices.AsyncStateMachineAttribute"))
                    .Single(m => m.Name.String.Contains("AsyncLambda"));
                Check(witnesses.Any(w => w.Kind == "AsyncMethod" && w.OwnerToken == anonymousAsync.MDToken.Raw), "Compressed async lambda lost body witness.");
                decompiler.Settings.TryGetOption("yield")!.Value = false;
                Check(!Decompile(decompiler, root, true).Evidence!.BodyWitnesses.Any(w => w.Kind == "IteratorMethod"), "Disabled iterator rewrite produced a witness.");
                decompiler.Settings.TryGetOption("yield")!.Value = true;
                var recursive = root.Methods.Single(m => m.Name == "Recursive");
                Check(proof.FieldBindings.Any(f => f.OwnerToken == recursive.MDToken.Raw && f.SourceName == "recurse"), "Recursive delegate storage binding lost.");
                // Synthetic metadata only: reject similar Dispose bodies with
                // a different state, field or additional side effect.
                var iterate = root.Methods.Single(m => m.Name == "Iterate");
                var machine = ((TypeSig)iterate.CustomAttributes.Single(a => a.TypeFullName.EndsWith("IteratorStateMachineAttribute")).ConstructorArguments[0].Value).ToTypeDefOrRef().ResolveTypeDef();
                var dispose = machine.Methods.Single(m => m.Name.String.EndsWith("IDisposable.Dispose"));
                var constant = dispose.Body.Instructions.Single(i => i.IsLdcI4());
                var originalCode = constant.OpCode;
                var originalOperand = constant.Operand;
                constant.OpCode = OpCodes.Ldc_I4; constant.Operand = -3;
                Check(!Decompile(CreateDecompiler(), root, true).Evidence!.BodyWitnesses.Any(w => w.Kind == "IteratorMethod" && w.OwnerToken == iterate.MDToken.Raw), "Different terminal state accepted as no-cleanup Dispose.");
                constant.OpCode = originalCode; constant.Operand = originalOperand;
                var store = dispose.Body.Instructions.Single(i => i.OpCode == OpCodes.Stfld);
                var originalField = store.Operand;
                store.Operand = machine.Fields.First(f => f != originalField && f.FieldType.ElementType == ElementType.I4);
                Check(!Decompile(CreateDecompiler(), root, true).Evidence!.BodyWitnesses.Any(w => w.Kind == "IteratorMethod" && w.OwnerToken == iterate.MDToken.Raw), "Different target field accepted as state write.");
                store.Operand = originalField;
                var sideEffect = Instruction.Create(OpCodes.Call, new MemberRefUser(module, "WriteLine", MethodSig.CreateStatic(module.CorLibTypes.Void), new TypeRefUser(module, "System", "Console", module.CorLibTypes.AssemblyRef)));
                dispose.Body.Instructions.Insert(0, sideEffect);
                Check(!Decompile(CreateDecompiler(), root, true).Evidence!.BodyWitnesses.Any(w => w.Kind == "IteratorMethod" && w.OwnerToken == iterate.MDToken.Raw), "Additional Dispose side effect discarded.");
                dispose.Body.Instructions.Remove(sideEffect);
            }
            else {
                foreach (string name in new[] { "KeepType", "KeepMember", "KeepSignature", "KeepShared", "KeepPublic" }) {
                    var type = root.NestedTypes.Single(t => t.Name == "State_" + name);
                    Check(proof.DeclarationTokens.Contains(type.MDToken.Raw), "Required retained declaration not reported: " + name);
                }
                var fallback = root.Methods.Single(m => m.Name == "SharedFallback");
                Check(!witnesses.Any(w => w.Kind == "AsyncMethod" && w.OwnerToken == fallback.MDToken.Raw), "Fallback body counted as successful reconstruction.");
                foreach (string name in new[] { "Remove", "RemoveGeneric" }) {
                    var method = root.Methods.Single(m => m.Name == name);
                    var witness = witnesses.Single(w => w.Kind == "AsyncMethod" && w.OwnerToken == method.MDToken.Raw);
                    Check(!proof.DeclarationTokens.Contains(witness.ImplementationTypeToken), "Redundant implementation falsely reported retained.");
                }
            }
            var repeat = Decompile(decompiler, root, true);
            Check(JsonSerializer.Serialize(proof, json) == JsonSerializer.Serialize(repeat.Evidence, json), "Repeated capture is not deterministic.");
            Check(observed.Source == repeat.Source, "Repeated capture mutated AST/source settings.");
            Record(observed);
        }
        else if (args[3] == "inspect") {
            uint? rootToken = ParseToken(options, "--root="), methodToken = ParseToken(options, "--method=");
            if (rootToken != null && methodToken != null) throw new ArgumentException("Choose type or member scope.");
            if (methodToken != null) Record(Decompile(decompiler, (MethodDef)module.ResolveToken(methodToken.Value), true));
            else foreach (var root in rootToken != null ? new[] { (TypeDef)module.ResolveToken(rootToken.Value) } : module.Types.Where(t => !t.IsGlobalModuleType))
                Record(Decompile(decompiler, root, true));
        }
        else throw new ArgumentException("Unknown command.");
        foreach (var pair in dependencies) if (Hash(pair.Key) != pair.Value) throw new InvalidDataException("Decompiler dependency changed: " + pair.Key);
        references.Verify();
        if (Hash(input) != initialHash) throw new InvalidDataException("Physical input changed.");
        var report = new {
            Format = 1, Mode = "RawMetadataFinalCSharpAst", Input = input, InputSha256 = initialHash, module.Mvid,
            AssemblyIdentity = module.Assembly?.FullNameToken, MapApplied = false,
            ToolSha256 = Hash(Assembly.GetExecutingAssembly().Location), Options = options,
            ReferenceManifest = references.ManifestPath, ReferenceManifestSha256 = references.ManifestHash,
            PinnedReferences = references.Entries,
            Dependencies = dependencies.OrderBy(p => p.Key, StringComparer.OrdinalIgnoreCase).Select(p => new { Path = p.Key, Sha256 = p.Value }).ToArray(),
            Definitions = originals, Roots = reports, SourceHashes = sourceHashes, SourceOutput = sourceOutput, Checks = checks, ElapsedSeconds = stopwatch.Elapsed.TotalSeconds,
            PeakWorkingSetBytes = Process.GetCurrentProcess().PeakWorkingSet64,
            Limitations = "Read-only AST observations; no application-wide merge verdict, semantic naming, compilation or runtime proof. Only manifest-pinned external dependency resolution."
        };
        Directory.CreateDirectory(Path.GetDirectoryName(output)!);
        if (sourceOutput != null) {
            Directory.CreateDirectory(Path.GetDirectoryName(sourceOutput)!);
            using var sourceStream = new FileStream(sourceOutput, FileMode.CreateNew, FileAccess.Write);
            sourceStream.Write(Encoding.UTF8.GetBytes(savedSource!));
        }
        using (var stream = new FileStream(output, FileMode.CreateNew, FileAccess.Write)) JsonSerializer.Serialize(stream, report, json);
        Console.WriteLine($"PASS: {checks} checks; {reports.Count} roots; {reports.Sum(r => r.BodyWitnesses.Count)} body witnesses; {reports.Sum(r => r.FieldBindings.Count)} field bindings; {stopwatch.Elapsed.TotalSeconds:F2}s.");
        return 0;
    }

    static uint? ParseToken(string[] args, string prefix) {
        var values = args.Where(a => a.StartsWith(prefix)).ToArray();
        if (values.Length > 1) throw new ArgumentException("Duplicate filter: " + prefix);
        return values.Length == 0 ? null : Convert.ToUInt32(values[0][prefix.Length..].Replace("0x", ""), 16);
    }
    static IDecompiler CreateDecompiler() {
        string path = Path.Combine(runtime, "dnSpy.Decompiler.ILSpy.Core.dll");
        dependencies[path] = Hash(path);
        var frontend = Assembly.LoadFrom(path);
        var type = frontend.GetType("dnSpy.Decompiler.ILSpy.Core.CSharp.DecompilerProvider", true)!;
        return ((IDecompilerProvider)Activator.CreateInstance(type)!).Create().First();
    }
    static (string Source, GeneratedSourceEvidence? Evidence) Decompile(IDecompiler decompiler, IMemberDef definition, bool capture, DecompilationContext? sharedContext = null) {
        var writer = new StringWriter();
        var output = new EvidenceOutput(writer);
        var context = sharedContext ?? new DecompilationContext { AsyncMethodBodyDecompilation = false };
        context.CaptureGeneratedSourceEvidence = capture;
        if (definition is TypeDef type) decompiler.Decompile(type, output, context);
        else if (definition is MethodDef method) decompiler.Decompile(method, output, context);
        else throw new ArgumentException("Expected type or method.");
        if (capture && output.Evidence == null) throw new InvalidDataException("Actual C# plugin did not provide evidence.");
        return (writer.ToString(), output.Evidence);
    }
    static string Hash(string path) { using var stream = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(stream)); }
    sealed class PinnedReferences : IAssemblyResolver, IDisposable {
        public sealed record Entry(string Path, string Identity, string Mvid, string Sha256);
        sealed class Manifest { public int Format { get; set; } public Entry[] Assemblies { get; set; } = []; }
        public string? ManifestPath { get; }
        public string? ManifestHash { get; }
        public Entry[] Entries { get; } = [];
        public ModuleContext Context { get; }
        readonly Dictionary<string, ModuleDefMD> modules = new(StringComparer.Ordinal);
        public PinnedReferences(string? path) {
            Context = new ModuleContext(this);
            if (path == null) return;
            ManifestPath = Path.GetFullPath(path);
            ManifestHash = Hash(ManifestPath);
            var manifest = JsonSerializer.Deserialize<Manifest>(File.ReadAllBytes(ManifestPath));
            if (manifest?.Format != 1) throw new InvalidDataException("Expected reference manifest Format=1.");
            Entries = manifest.Assemblies.Select(e => e with { Path = Path.GetFullPath(e.Path, Path.GetDirectoryName(ManifestPath)!) }).ToArray();
            try {
                foreach (var entry in Entries) {
                    byte[] bytes = File.ReadAllBytes(entry.Path);
                    if (!StringComparer.OrdinalIgnoreCase.Equals(Convert.ToHexString(SHA256.HashData(bytes)), entry.Sha256)) throw new InvalidDataException("Stale reference hash: " + entry.Path);
                    var loaded = ModuleDefMD.Load(bytes, Context);
                    if (loaded.Assembly?.FullName != entry.Identity || loaded.Mvid != Guid.Parse(entry.Mvid) || modules.ContainsKey(entry.Identity)) {
                        loaded.Dispose(); throw new InvalidDataException("Invalid/duplicate reference identity: " + entry.Path);
                    }
                    loaded.EnableTypeDefFindCache = true;
                    modules.Add(entry.Identity, loaded);
                }
            }
            catch { Dispose(); throw; }
        }
        public AssemblyDef? Resolve(IAssembly assembly, ModuleDef? sourceModule) => assembly != null && modules.TryGetValue(assembly.FullName, out var found) ? found.Assembly : null;
        public void Verify() {
            if (ManifestPath != null && Hash(ManifestPath) != ManifestHash) throw new InvalidDataException("Reference manifest changed.");
            foreach (var entry in Entries) if (!StringComparer.OrdinalIgnoreCase.Equals(Hash(entry.Path), entry.Sha256)) throw new InvalidDataException("Physical reference changed: " + entry.Path);
        }
        public void Dispose() { foreach (var module in modules.Values) module.Dispose(); modules.Clear(); }
    }
    sealed class EvidenceOutput : TextWriterDecompilerOutput, IDecompilerOutput {
        public GeneratedSourceEvidence? Evidence { get; private set; }
        public EvidenceOutput(TextWriter writer) : base(writer) { }
        bool IDecompilerOutput.UsesCustomData => true;
        void IDecompilerOutput.AddCustomData<T>(string id, T data) {
            if (id != PredefinedCustomDataIds.GeneratedSourceEvidence) return;
            if (Evidence != null || data is not GeneratedSourceEvidence evidence) throw new InvalidDataException("Invalid/duplicate evidence payload.");
            Evidence = evidence;
        }
    }
}
