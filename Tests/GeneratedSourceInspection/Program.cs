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
using System.Xml;
using System.Xml.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
using dnSpy.Contracts.Decompiler;
using ICSharpCode.Decompiler.Ast;

internal static class Program {
    static string runtime = "";
    static bool restoreMetadataOnlyFields;
    static readonly Dictionary<string, string> dependencies = new(StringComparer.OrdinalIgnoreCase);
    static readonly JsonSerializerOptions json = new() { WriteIndented = true };

    static int Main(string[] args) {
        try {
            if (args.Length < 4) throw new ArgumentException("Usage: GeneratedSourceInspection <actual-plugin-runtime> <input-or-seed-or-scope-summary> <new-report> <inspect|self-test|metadata|prepare-context|audit-scope>. Inspection: [--references=<manifest>] [--map=<source-map>] [--sdk-source] [--root=0xTOKEN|--method=0xTOKEN] [--no-async|--no-yield|--no-anon-methods|--show-all|--declare-state-machines]. Preparation: --contexts=<loader-xml> --app-config=<config> --framework=<directory> [--support=<directory>]. Scope audit: complete scope summary and fresh output only.");
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
        if (args[3] == "report-summary") {
            if (args.Length != 4) throw new ArgumentException("Report summary accepts one immutable native report and a fresh header output.");
            return ObservationReportSummary.Run(args[1], args[2]);
        }
        if (args[3] == "audit-scope") {
            if (args.Length != 4) throw new ArgumentException("Scope audit accepts one complete scope summary and a fresh output.");
            return PhysicalScopeAudit.Run(args[1], args[2]);
        }
        if (args[3] == "state-coverage") {
            if (args.Length != 6) throw new ArgumentException("State coverage accepts an original input, fresh output, immutable native source observation and its producing inspector DLL.");
            return StateSourceCoverageInspection.Run(args[1],args[4],args[5],args[2]);
        }
        if (args[3] == "prepare-context") return PhysicalContextPreparation.Run(args[1], args[2], args.Skip(4).ToArray());
        string input = Path.GetFullPath(args[1]), output = Path.GetFullPath(args[2]);
        if (File.Exists(output) || Directory.Exists(output)) throw new IOException("Choose a new report path.");
        if (StringComparer.OrdinalIgnoreCase.Equals(input, output) || output.StartsWith(Path.GetDirectoryName(input)! + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
            throw new IOException("Write reports outside the inspected application tree.");
        string initialHash = Hash(input);
        var stopwatch = Stopwatch.StartNew();
        // Only explicitly pinned physical references; no ambient/GAC/name-only fallback.
        string[] options = args.Skip(4).ToArray();
        restoreMetadataOnlyFields = options.Contains("--sdk-source");
        string? sourceOutput = options.SingleOrDefault(o => o.StartsWith("--source="))?[9..];
        if (sourceOutput != null) {
            sourceOutput = Path.GetFullPath(sourceOutput);
            if (File.Exists(sourceOutput) || Directory.Exists(sourceOutput) || StringComparer.OrdinalIgnoreCase.Equals(sourceOutput, output) ||
                sourceOutput.StartsWith(Path.GetDirectoryName(input)! + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                throw new IOException("Choose a new source output outside the inspected application tree.");
        }
        using var references = new PinnedSourceContext(options.SingleOrDefault(o => o.StartsWith("--references="))?[13..]);
        using var standaloneModule = references.FindModule(input) == null ? ModuleDefMD.Load(input, new ModuleCreationOptions(references.Context)) : null;
        var module = references.FindModule(input) ?? standaloneModule!;
        var originals = module.GetTypes().SelectMany(t => new IMemberDef[] { t }.Concat(t.Methods).Concat(t.Fields).Concat(t.Properties).Concat(t.Events))
            .OrderBy(d => d.MDToken.Raw).Select(d => new { Token = d.MDToken.Raw, d.FullName, OriginalName = d.Name.String }).ToArray();
        var decompiler = CreateDecompiler();
        string? mapPath = options.SingleOrDefault(o => o.StartsWith("--map="))?[6..];
        string? mapHash = null, normalizedMapHash = null, whitelistPath = null, whitelistHash = null;
        if (mapPath != null) {
            if (args[3] != "inspect" || !references.ExportInputs.Contains(module)) throw new InvalidDataException("Mapped inspection requires an exact pinned export input and inspect mode.");
            mapPath = Path.GetFullPath(mapPath); mapHash = Hash(mapPath);
            using var reader = XmlReader.Create(mapPath, new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null });
            var map = XDocument.Load(reader).Root ?? throw new InvalidDataException("Missing source map root.");
            if (Path.GetFullPath((string?)map.Attribute("InputDirectory") ?? "") != references.InputDirectory) throw new InvalidDataException("Source map/pinned input directory mismatch.");
            whitelistPath = (string?)map.Attribute("SdkNameWhitelist");
            if (whitelistPath != null) { whitelistPath = Path.GetFullPath(whitelistPath, Path.GetDirectoryName(mapPath)!); whitelistHash = Hash(whitelistPath); }
            string applierPath = Path.Combine(runtime, "dnSpy.Decompiler.dll"); dependencies[applierPath] = Hash(applierPath);
            var applier = Assembly.LoadFrom(applierPath).GetType("dnSpy.Decompiler.MSBuild.SourceNameMap", true)!.GetMethod("Apply", BindingFlags.Public | BindingFlags.Static)!;
            string normalized = (string)applier.Invoke(null, new object[] { mapPath, references.ExportInputs.ToArray() })!;
            normalizedMapHash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(normalized)));
        }
        foreach (string option in options.Where(o => !o.StartsWith("--root=") && !o.StartsWith("--method=") && !o.StartsWith("--references=") && !o.StartsWith("--source=") && !o.StartsWith("--map=") && o != "--sdk-source")) {
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
            Check(proof.PrintedReferenceCoverage, "Actual C# token writer did not report reference coverage.");
            Check(proof.PrintedReferences.Any(r => r.IsDefinition && r.DefinitionToken == root.MDToken.Raw), "Printed type declaration was not distinguished from a use.");
            Check(proof.PrintedReferences.Where(r => r.DefinitionModulePath == input).All(r =>
                r.DefinitionModuleMvid == module.Mvid && module.ResolveToken(r.DefinitionToken) is IMemberDef), "Printed local bindings lost physical metadata identity.");
            var witnesses = proof.BodyWitnesses;
            Check(witnesses.Any(w => w.Kind == "AsyncMethod"), "No successful async body observed.");
            Check(witnesses.Any(w => w.Kind == "AnonymousMethod"), "No successful lambda body observed.");
            Check(witnesses.All(w => module.ResolveToken(w.ImplementationToken) is MethodDef && module.ResolveToken(w.OwnerToken) is IMemberDef), "Witness tokens are not physical definitions.");
            Check(witnesses.All(w => w.SourceOwnerPath.Count != 0 && w.SourceOwnerPath.All(t => module.ResolveToken(t) is IMemberDef)), "Printed occurrence owner path lost physical definitions.");
            Check(witnesses.All(w => proof.DeclarationTokens.Contains(w.SourceOwnerPath[0])), "Printed occurrence path is not anchored in an emitted declaration.");
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
                Check(!proof.PrintedReferenceTokens.Contains(awaitOwner.MDToken.Raw), "An async owner declaration was counted as a printed method use.");
                Check(witnesses.Any(w => w.Kind == "IteratorMethod"), "No iterator rewrite observed.");
                var fake = root.NestedTypes.Single(t => t.Name == "State_NotGenerated");
                Check(proof.DeclarationTokens.Contains(fake.MDToken.Raw) && !witnesses.Any(w => w.ImplementationTypeToken == fake.MDToken.Raw), "Generated-looking spelling counted as reconstruction.");
                var ordinaryField = fake.Fields.Single(f => f.Name == "field_1");
                Check(proof.PrintedReferenceTokens.Contains(ordinaryField.MDToken.Raw), "A real printed field access was discarded.");
                Check(!proof.PrintedReferenceTokens.Contains(fake.Methods.Single(m => m.Name == "MoveNext").MDToken.Raw), "A method declaration was counted as a printed call.");
                var capture = root.Methods.Single(m => m.Name == "Capture");
                var captureImplementation = witnesses.Single(w => w.Kind == "AnonymousMethod" && w.OwnerToken == capture.MDToken.Raw);
                Check(proof.ReferenceTokens.Contains(captureImplementation.ImplementationToken) && !proof.PrintedReferenceTokens.Contains(captureImplementation.ImplementationToken), "Inlined lambda metadata was confused with a printed implementation call.");
                Check(proof.FieldBindings.Any(f => f.OwnerToken == capture.MDToken.Raw && f.SourceName == "offset"), "Captured field-to-source parameter evidence lost.");
                var anonymousAsync = module.GetTypes().SelectMany(t => t.Methods)
                    .Where(m => m.CustomAttributes.Any(a => a.TypeFullName == "System.Runtime.CompilerServices.AsyncStateMachineAttribute"))
                    .Single(m => m.Name.String.Contains("<AsyncLambda>"));
                Check(witnesses.Any(w => w.Kind == "AsyncMethod" && w.OwnerToken == anonymousAsync.MDToken.Raw), "Compressed async lambda lost body witness.");
                Check(witnesses.Where(w => w.Kind == "AsyncMethod" && w.OwnerToken == anonymousAsync.MDToken.Raw)
                    .All(w => w.SourceOwnerPath[0] == root.Methods.Single(m => m.Name == "AsyncLambda").MDToken.Raw && w.SourceOwnerPath[^1] == anonymousAsync.MDToken.Raw),
                    "Compressed async lambda lost its printed/logical occurrence owners.");
                var nestedAsync = root.Methods.Single(m => m.Name == "NestedAsyncLambda");
                var nestedWitnesses = witnesses.Where(w => w.Kind == "AsyncMethod" && w.SourceOwnerPath[0] == nestedAsync.MDToken.Raw).ToArray();
                Check(nestedWitnesses.Length == 1 && nestedWitnesses[0].SourceOwnerPath.Count == 3 && nestedWitnesses[0].SourceOwnerPath[^1] == nestedWitnesses[0].OwnerToken,
                    "Nested async lambda lost its enclosing implementation chain.");
                decompiler.Settings.TryGetOption("yield")!.Value = false;
                Check(!Decompile(decompiler, root, true).Evidence!.BodyWitnesses.Any(w => w.Kind == "IteratorMethod"), "Disabled iterator rewrite produced a witness.");
                decompiler.Settings.TryGetOption("yield")!.Value = true;
                var recursive = root.Methods.Single(m => m.Name == "Recursive");
                Check(proof.PrintedReferences.Any(r => r.OwnerToken == recursive.MDToken.Raw && r.IsImplementationAnnotation && r.Form == "Keyword" && r.Text == "delegate"), "Anonymous delegate implementation link was not explicitly classified.");
                Check(proof.PrintedReferences.Where(r => r.IsImplementationAnnotation).All(r => !proof.PrintedReferenceTokens.Contains(r.DefinitionToken)), "Anonymous implementation links counted as printed calls.");
                var referenceValue = root.NestedTypes.Single(t => t.Name == "ReferenceValue");
                var sourceReferences = proof.PrintedReferences.Where(r => !r.IsDefinition && !r.IsImplementationAnnotation).ToArray();
                uint Token(string name) => referenceValue.Methods.Single(m => m.Name == name).MDToken.Raw;
                Check(sourceReferences.Any(r => r.DefinitionToken == Token("Read") && r.Form == "Identifier"), "Named method-group reference lost.");
                Check(sourceReferences.Any(r => r.DefinitionToken == Token(".ctor") && r.Form == "Keyword" && r.Text == "new"), "Constructor keyword binding lost.");
                Check(sourceReferences.Any(r => r.DefinitionToken == Token("op_Addition") && r.Form == "Token" && r.Text == "+"), "Printed operator binding lost.");
                Check(sourceReferences.Any(r => r.DefinitionToken == referenceValue.Properties.Single().MDToken.Raw && r.SourceNodeKind == "IndexerExpression"), "Printed indexer binding lost.");
                Check(sourceReferences.Any(r => r.Kind == "Method" && r.RequestedSignature.Contains("::Invoke(") && r.SourceNodeKind == "InvocationExpression" && r.Form == "Token"), "Delegate invocation punctuation binding lost.");
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
        else if (args[3] == "metadata") {
            if (sourceOutput != null || mapPath != null || options.Any(o => !o.StartsWith("--references=")))
                throw new ArgumentException("Metadata inspection accepts only pinned references and no source output/map.");
        }
        else throw new ArgumentException("Unknown command.");
        int pinnedNonlocal = 0, unresolvedNonlocal = 0;
        var unpinnedNonlocal = new List<object>();
        foreach (var root in reports) foreach (var use in root.NonlocalReferences) {
            if (use.OwnerToken != 0 && module.ResolveToken(use.OwnerToken) is not IMemberDef)
                throw new InvalidDataException("Nonlocal reference owner is not an exact local definition.");
            if (use.DefinitionToken == 0) { unresolvedNonlocal++; continue; }
            var target = string.IsNullOrEmpty(use.DefinitionModulePath) ? null : references.FindModule(use.DefinitionModulePath);
            if (target == null) {
                unpinnedNonlocal.Add(new { root.RootTypeToken, use.OwnerToken, use.RequestedSignature, use.DefinitionModulePath, use.DefinitionToken, Reason = "resolved metadata definition is outside the pinned physical context" });
                continue;
            }
            if (target.Mvid != use.DefinitionModuleMvid || target.Assembly.FullName != use.DefinitionAssemblyIdentity ||
                target.ResolveToken(use.DefinitionToken) is not IMemberDef definition || definition.FullName != use.DefinitionSignature)
                throw new InvalidDataException("Nonlocal reference does not match its exact pinned physical definition.");
            pinnedNonlocal++;
        }
        int printedLocal = 0, printedNonlocal = 0, printedUnresolved = 0, printedUnknownOwner = 0;
        var unpinnedPrinted = new List<object>();
        foreach (var root in reports) {
            if (!root.PrintedReferenceCoverage) throw new InvalidDataException("Actual C# writer reference coverage missing.");
            var localUses = new HashSet<uint>();
            foreach (var use in root.PrintedReferences) {
                if (use.OwnerToken == 0) printedUnknownOwner++;
                else if (module.ResolveToken(use.OwnerToken) is not IMemberDef owner || owner.Module != module)
                    throw new InvalidDataException("Printed reference owner is not a local definition.");
                if (use.DefinitionToken == 0) { printedUnresolved++; continue; }
                var target = use.DefinitionModulePath == module.Location ? module :
                    string.IsNullOrEmpty(use.DefinitionModulePath) ? null : references.FindModule(use.DefinitionModulePath);
                if (target == null) {
                    unpinnedPrinted.Add(new { root.RootTypeToken, use.OwnerToken, use.RequestedSignature, use.DefinitionModulePath, use.DefinitionToken });
                    continue;
                }
                if (target.Mvid != use.DefinitionModuleMvid || target.Assembly.FullName != use.DefinitionAssemblyIdentity ||
                    target.ResolveToken(use.DefinitionToken) is not IMemberDef definition || definition.FullName != use.DefinitionSignature)
                    throw new InvalidDataException("Printed reference does not match its exact physical definition.");
                if (target == module) {
                    if (!use.IsDefinition && !use.IsImplementationAnnotation) { printedLocal++; localUses.Add(use.DefinitionToken); }
                }
                else printedNonlocal++;
            }
            if (!localUses.SetEquals(root.PrintedReferenceTokens)) throw new InvalidDataException("Printed local use token classification mismatch.");
        }
        foreach (var pair in dependencies) if (Hash(pair.Key) != pair.Value) throw new InvalidDataException("Decompiler dependency changed: " + pair.Key);
        references.Verify();
        if (mapPath != null && (Hash(mapPath) != mapHash || whitelistPath != null && Hash(whitelistPath) != whitelistHash)) throw new InvalidDataException("Source map/whitelist changed.");
        if (Hash(input) != initialHash) throw new InvalidDataException("Physical input changed.");
        var methods = module.GetTypes().SelectMany(t => t.Methods).OrderBy(m => m.MDToken.Raw).ToArray();
        var report = new {
            Format = 1, Mode = args[3] == "metadata" ? "PhysicalMetadataOnly" : mapPath == null ? "RawMetadataFinalCSharpAst" : "MappedFinalCSharpAst", Input = input, InputSha256 = initialHash, module.Mvid,
            AssemblyIdentity = module.Assembly?.FullNameToken, MapApplied = mapPath != null,
            AssemblyReferences = module.GetAssemblyRefs().Select(a => new { Token = a.MDToken.Raw, Identity = a.FullName }).ToArray(),
            TypeReferences = args[3] == "metadata" ? module.GetTypeRefs().Select(t => new { Token = t.MDToken.Raw, t.FullName, AssemblyIdentity = t.DefinitionAssembly?.FullName }).ToArray() : null,
            MemberReferences = args[3] == "metadata" ? module.GetMemberRefs().Select(m => new { Token = m.MDToken.Raw, m.FullName, AssemblyIdentity = m.DeclaringType?.DefinitionAssembly?.FullName }).ToArray() : null,
            Map = mapPath, MapSha256 = mapHash, NormalizedMapSha256 = normalizedMapHash,
            SdkNameWhitelist = whitelistPath, SdkNameWhitelistSha256 = whitelistHash,
            RestoreMetadataOnlyFields = restoreMetadataOnlyFields,
            ToolSha256 = Hash(Assembly.GetExecutingAssembly().Location), Options = options,
            ReferenceManifest = references.ManifestPath, ReferenceManifestSha256 = references.ManifestHash,
            PinnedReferences = references.Entries,
            SourceConfigs = references.ConfigEntries,
            SourceSearchContexts = references.SearchContexts,
            RequireSourceContexts = references.RequireSourceContexts,
            PhysicalResolutions = references.Resolutions,
            Dependencies = dependencies.OrderBy(p => p.Key, StringComparer.OrdinalIgnoreCase).Select(p => new { Path = p.Key, Sha256 = p.Value }).ToArray(),
            Definitions = originals, Roots = reports, SourceHashes = sourceHashes, SourceOutput = sourceOutput, Checks = checks, ElapsedSeconds = stopwatch.Elapsed.TotalSeconds,
            NonlocalReferenceAudit = new { PinnedDefinitions = pinnedNonlocal, UnresolvedUses = unresolvedNonlocal, UnpinnedDefinitions = unpinnedNonlocal, Limits = "Final AST use records only. Pinned definitions have matching path/MVID/assembly identity/token/signature; this is not proof of complete source coverage or runtime contracts." },
            PrintedReferenceAudit = new { Records = reports.Sum(r => r.PrintedReferences.Count), LocalUseRecords = printedLocal,
                PinnedNonlocalRecords = printedNonlocal, UnresolvedRecords = printedUnresolved, UnpinnedDefinitions = unpinnedPrinted,
                UnknownOwnerRecords = printedUnknownOwner, Definitions = reports.Sum(r => r.PrintedReferences.Count(u => u.IsDefinition)),
                ImplementationAnnotations = reports.Sum(r => r.PrintedReferences.Count(u => u.IsImplementationAnnotation)),
                Limits = "Actual C# token-writer metadata bindings. Definitions and anonymous implementation links are separate from source uses. Comments/debug spans and compiler-inferred implicit bindings are outside this observation; absence alone cannot retire a symbol." },
            SourceAliases = module.GetTypes().SelectMany(t => new IMemberDef[] { t }.Concat(t.Methods).Concat(t.Fields)).Where(d => SourceNameAliases.Get(d) != null)
                .Select(d => new { Token = d.MDToken.Raw, Alias = SourceNameAliases.Get(d), AliasNamespace = d is TypeDef type ? SourceNameAliases.GetAliasNamespace(type) : null }).ToArray(),
            ParameterAliases = methods.SelectMany(m => m.Parameters.Where(p => p.IsNormalMethodParameter).Select(p => new { MethodToken = m.MDToken.Raw, Sequence = p.MethodSigIndex + 1, OriginalName = p.Name, Alias = SourceNameAliases.GetParameter(p) })).Where(p => p.Alias != null).ToArray(),
            LocalAliases = methods.Where(m => m.HasBody).SelectMany(m => m.Body.Variables.Select((v, i) => new { MethodToken = m.MDToken.Raw, Index = i, OriginalName = v.Name, Type = v.Type.FullName, Alias = SourceNameAliases.GetLocal(v) })).Where(v => v.Alias != null).ToArray(),
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
        context.RestoreMetadataOnlyFields = restoreMetadataOnlyFields;
        if (definition is TypeDef type) decompiler.Decompile(type, output, context);
        else if (definition is MethodDef method) decompiler.Decompile(method, output, context);
        else throw new ArgumentException("Expected type or method.");
        if (capture && output.Evidence == null) throw new InvalidDataException("Actual C# plugin did not provide evidence.");
        return (writer.ToString(), output.Evidence);
    }
    static string Hash(string path) { using var stream = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(stream)); }
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
