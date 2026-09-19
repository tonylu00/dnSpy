#nullable disable
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using dnlib.DotNet;

// Shared verbatim with dnSpy.Decompiler/MSBuild/MethodContractFamilies.cs.
// Metadata only: groups CLR contracts without renaming or executing inputs.
namespace SourceNameMapping {
    public sealed class MethodContractFamilies {
        public sealed class Family {
            public string Id { get; internal set; }
            public MethodDef[] Methods { get; internal set; }
            public string[] Blockers { get; internal set; }
        }
        sealed class Use {
            public TypeDef Type;
            public IList<TypeSig> Arguments;
            public Use(TypeDef type, IList<TypeSig> arguments = null) { Type = type; Arguments = arguments; }
        }
        readonly HashSet<ModuleDef> modules;
        readonly HashSet<ModuleDef> analysisModules;
        readonly Dictionary<string, ModuleDef[]> identities;
        readonly Func<ModuleDef, string> moduleKey;
        readonly bool useHostResolver;
        readonly Dictionary<MethodDef, MethodDef> parents = new Dictionary<MethodDef, MethodDef>();
        readonly Dictionary<MethodDef, HashSet<string>> blockers = new Dictionary<MethodDef, HashSet<string>>();
        readonly Dictionary<MethodDef, Family> families = new Dictionary<MethodDef, Family>();
        // Signature comparison and reference resolution dominate a large graph;
        // both are pure, so one comparer and a per-caller cache are enough.
        static readonly SigComparer Comparer = new SigComparer();
        readonly Dictionary<(ITypeDefOrRef Reference, ModuleDef Caller), Use> resolves = new Dictionary<(ITypeDefOrRef, ModuleDef), Use>();
        // Tooling hook: the NameCandidates CLI prints per-phase timings when
        // NAMECANDIDATES_TIMING=1; product code leaves this null and pays
        // nothing beyond a field comparison per phase.
        public static Action<string> TimingHook;
        static void Mark(string phase) => TimingHook?.Invoke(phase);
        // The union-find state, the blocker sets and the finished members are
        // the only state shared by the parallel passes, and this gate guards
        // them. The lookup indexes below are only ever touched from the
        // sequential per-type analysis, so they stay unlocked.
        readonly object gate = new object();
        // Method lookup by name and memoized generic substitution: a large graph
        // compares the same contracts against the same hierarchy slots thousands
        // of times, so scanning every method of a type is pure waste.
        readonly Dictionary<TypeDef, Dictionary<string, MethodDef[]>> named = new Dictionary<TypeDef, Dictionary<string, MethodDef[]>>();
        readonly Dictionary<TypeDef, MethodDef[]> overriding = new Dictionary<TypeDef, MethodDef[]>();
        readonly Dictionary<(MethodSig Signature, object Arguments), MethodSig> substituted = new Dictionary<(MethodSig, object), MethodSig>();
        // Explicit implementations are rare; indexing them keeps the interface
        // walk from scanning every method of every hierarchy level.
        MethodDef[] Overriding(TypeDef type) {
            if (!overriding.TryGetValue(type, out var methods))
                overriding[type] = methods = HasMethodImpls(type.Module)
                    ? Methods(type).Where(m => m.Overrides.Count != 0).ToArray() : Array.Empty<MethodDef>();
            return methods;
        }
        // dnlib materialises method rows through a locked lazy list and this
        // walk visits one type from several passes, so the per-type list is
        // read once. The order is the metadata order the rest of the tool
        // depends on; this cache is only touched by the sequential analysis.
        readonly Dictionary<TypeDef, MethodDef[]> methodLists = new Dictionary<TypeDef, MethodDef[]>();
        MethodDef[] Methods(TypeDef type) {
            if (!methodLists.TryGetValue(type, out var methods))
                methodLists[type] = methods = type.Methods.ToArray();
            return methods;
        }
        // Method overrides can only come from MethodImpl rows, and reading
        // MethodDef.Overrides makes dnlib build a MemberRef (and resolve its
        // declaring type) per candidate method. A module without any such row
        // can never contribute one, which skips that work entirely.
        readonly Dictionary<ModuleDef, bool> methodImpls = new Dictionary<ModuleDef, bool>();
        bool HasMethodImpls(ModuleDef module) {
            if (!methodImpls.TryGetValue(module, out bool has)) {
                var md = module as ModuleDefMD;
                var stream = md?.Metadata?.TablesStream;
                methodImpls.Add(module, has = stream == null || stream.MethodImplTable.Rows > 0);
            }
            return has;
        }
        // Extensions.ToTypeSig() resolves a TypeRef through the assembly
        // resolver only to pick a class or value-type signature, and every
        // caller here immediately converts the signature back to its
        // TypeDefOrRef, so the resolution can stay off.
        static TypeSig TypeSigOf(ITypeDefOrRef reference) => reference?.ToTypeSig(resolveToCheckValueType: false);
        MethodDef[] Named(TypeDef type, string name) {
            if (!named.TryGetValue(type, out var index)) named[type] = index = new Dictionary<string, MethodDef[]>(StringComparer.Ordinal);
            if (!index.TryGetValue(name, out var methods))
                index[name] = methods = type.Methods.Where(m => m.Name == name).ToArray();
            return methods;
        }
        MethodSig SubstituteCached(MethodSig signature, IList<TypeSig> arguments) {
            if (signature == null || arguments == null || arguments.Count == 0) return signature;
            if (substituted.TryGetValue((signature, arguments), out var cached)) return cached;
            return substituted[(signature, arguments)] = Substitute(signature, arguments);
        }
        public IEnumerable<Family> Families => families.Values.Distinct().OrderBy(f => f.Id, StringComparer.Ordinal);
        public Family Get(MethodDef method) => families.TryGetValue(method, out var family) ? family : null;
        public static string MethodBlocker(MethodDef method) {
            if (method.IsConstructor) return "constructor";
            if (method.IsRuntimeSpecialName || method.Name.String.StartsWith("op_", StringComparison.Ordinal)) return "accessor-operator-or-runtime-special-name";
            // A property/event accessor is supported when its own row can name it:
            // the obfuscator left the row's readable name, so `get_Foo`/`set_Foo`
            // is the only name C# can bind to it. Accessors whose row was removed
            // or carries no usable name stay blocked.
            if (method.SemanticsAttributes != 0 || PropertyAccessorNames.IsAccessor(method))
                return PropertyAccessorNames.Derive(method) == null ? "accessor-operator-or-runtime-special-name" : null;
            // Obfuscators may remove the property/event row while leaving its
            // method's SpecialName bit. With no syntax contract, this is emitted
            // as an ordinary method; the build task restores the original flag.
            if (method.IsPinvokeImpl || method.IsRuntime) return "native-or-runtime-method";
            if (method.HasOverrides) return "explicit-method-implementation requires qualified source-name restoration";
            if (method.IsStatic && method.IsVirtual) return "static virtual contract";
            return null;
        }
        /// <summary>
        /// <paramref name="analyze"/> restricts which modules initiate contract
        /// analysis. Every input still resolves (so a mapped type's external base
        /// and interface slots resolve normally); modules outside the set are only
        /// ever reached through a mapped type, which is all a map can reference.
        /// </summary>
        public MethodContractFamilies(IEnumerable<ModuleDef> inputs, Func<ModuleDef, string> key, bool useHostResolver = false,
                IEnumerable<ModuleDef> analyze = null) {
            Mark("contract graph: begin");
            modules = new HashSet<ModuleDef>(inputs);
            analysisModules = analyze == null ? modules : new HashSet<ModuleDef>(analyze);
            moduleKey = key;
            this.useHostResolver = useHostResolver;
            // dnlib's ModuleDef.Find/TypeDefFinder rescans every type of the
            // target module for each lookup unless its finder cache is on
            // (the default), and the reference, MemberRef and host-resolver
            // paths in this graph all route through it. The graph only reads
            // metadata, so the cache can stay enabled; it never makes a
            // lookup return a different type.
            foreach (var module in modules) module.EnableTypeDefFindCache = true;
            identities = modules.Where(m => m.Assembly != null).GroupBy(m => m.Assembly.FullName, StringComparer.Ordinal)
                .ToDictionary(g => g.Key, g => g.ToArray(), StringComparer.Ordinal);
            if (analyze != null) ExtendAnalysisClosure();
            Mark($"contract graph: {analysisModules.Count} modules after implementation closure");
            var types = analysisModules.SelectMany(m => m.GetTypes()).ToArray();
            Mark($"contract graph: {modules.Count} modules, {types.Length} analyzed types");
            // Both passes are independent per type; the union-find, the blocker
            // sets and the shared indexes are the only shared state and are
            // serially guarded, so the outcome stays identical.
            System.Threading.Tasks.Parallel.ForEach(types, type => {
                foreach (var method in type.Methods)
                    if (method.IsVirtual || method.HasOverrides) Root(method);
            });
            Mark($"contract graph: {parents.Count} virtual roots");
            void Analyze(TypeDef type) {
                // A type without interfaces, inherited virtual slots or explicit
                // implementations cannot contribute a contract of its own.
                var methods = Methods(type);
                if (!type.IsInterface && type.Interfaces.Count == 0 &&
                    !methods.Any(m => m.IsVirtual && !m.IsNewSlot) && !methods.Any(m => m.HasOverrides)) return;
                var hierarchy = Hierarchy(new Use(type)).ToArray();
                foreach (var method in methods.Where(m => m.IsVirtual && !m.IsNewSlot)) {
                    bool found = false;
                    foreach (var parent in hierarchy.Skip(1)) {
                        var matches = Named(parent.Type, method.Name).Where(m => m.IsVirtual && Same(m, parent.Arguments, method, null)).ToArray();
                        if (matches.Length > 1) { Block(method, "ambiguous base slot"); break; }
                        if (matches.Length == 1) { Join(method, matches[0]); found = true; break; }
                    }
                    if (!found) Block(method, "unresolved or external base slot");
                }
                foreach (var method in methods.Where(m => m.HasOverrides)) foreach (var implementation in method.Overrides) {
                    var declaration = implementation.MethodDeclaration;
                    var use = Resolve(declaration.DeclaringType, type.Module);
                    if (use == null) { Block(method, "unresolved explicit contract"); continue; }
                    var matches = Named(use.Type, declaration.Name).Where(m =>
                        Comparer.Equals(SubstituteCached(m.MethodSig, use.Arguments), SubstituteCached(declaration.MethodSig, use.Arguments))).ToArray();
                    if (matches.Length == 1) Join(method, matches[0]); else Block(method, "ambiguous explicit contract");
                }
                if (type.IsInterface) return;
                var visited = new HashSet<string>(StringComparer.Ordinal);
                foreach (var owner in hierarchy) foreach (var item in owner.Type.Interfaces)
                    VisitInterface(Substitute(TypeSigOf(item.Interface), owner.Arguments)?.ToTypeDefOrRef(), owner.Type.Module, hierarchy, visited, type);
            }
            // The per-type walk shares too many small indexes (resolutions,
            // name lookup, union-find) for several threads to pay off, so it
            // stays sequential; the passes around it scale cleanly.
            foreach (var type in types) Analyze(type);
            Mark("contract graph: contracts joined");
            System.Threading.Tasks.Parallel.ForEach(parents.Keys.ToArray().GroupBy(Root).ToArray(), group => {
                var members = group.OrderBy(m => moduleKey(m.Module), StringComparer.Ordinal).ThenBy(m => m.MDToken.Raw).ToArray();
                string evidence = string.Join("\n", members.Select(m => moduleKey(m.Module).Replace('\\', '/') + "|" + m.MDToken.Raw.ToString("X8")));
                string id;
                using (var hasher = SHA256.Create())
                    id = BitConverter.ToString(hasher.ComputeHash(Encoding.UTF8.GetBytes(evidence))).Replace("-", "");
                var reasons = members.Select(MethodBlocker).Where(s => s != null)
                    .Concat(members.SelectMany(m => blockers.TryGetValue(m, out var set) ? set : Enumerable.Empty<string>()))
                    .Distinct().OrderBy(s => s, StringComparer.Ordinal).ToArray();
                var family = new Family { Id = id, Methods = members, Blockers = reasons };
                lock (gate) foreach (var method in members) families.Add(method, family);
            });
            Mark($"contract graph: {families.Count} family members grouped");
        }
        MethodDef Root(MethodDef method) {
            lock (gate) {
                if (!parents.TryGetValue(method, out var parent)) {
                    parents.Add(method, method); return method;
                }
                return parent == method ? method : parents[method] = Root(parent);
            }
        }
        // A contract family can include members that live in a module the caller
        // did not name: an interface implemented by another assembly, a base slot
        // overridden there, or an explicit implementation. Renaming a family
        // without those members would break the implementations, so every module
        // whose types derive from, implement or override an analysed type is
        // analysed as well, transitively. Only the reference identity already
        // loaded here is consulted; the host resolver is never used as a fallback
        // because that walk is what makes a large graph slow.
        void ExtendAnalysisClosure() {
            var analyzedTypes = new HashSet<TypeDef>();
            var references = new Dictionary<ModuleDef, HashSet<TypeDef>>();
            void Include(ModuleDef module) {
                analysisModules.Add(module);
                foreach (var type in module.GetTypes()) analyzedTypes.Add(type);
                references.Remove(module);
            }
            foreach (var module in analysisModules.ToArray()) Include(module);
            foreach (var module in modules.ToArray()) {
                if (analysisModules.Contains(module)) continue;
                references[module] = ReferencedTypes(module);
            }
            for (bool changed = true; changed;) {
                changed = false;
                foreach (var pair in references.ToArray().Where(p => p.Value.Overlaps(analyzedTypes)).ToArray()) {
                    Include(pair.Key);
                    changed = true;
                }
            }
        }
        // The types a module names through base types, interfaces and explicit
        // implementations, read straight from the metadata tables: the per-type
        // lazy lists materialise every type of every module instead.
        HashSet<TypeDef> ReferencedTypes(ModuleDef module) {
            var result = new HashSet<TypeDef>();
            var md = module as ModuleDefMD;
            var tables = md?.Metadata?.TablesStream;
            if (tables == null) {
                // Synthetic or cloned modules have no tables and few types.
                foreach (var type in module.GetTypes()) {
                    AddReference(type.BaseType, module, result);
                    foreach (var implementation in type.Interfaces) AddReference(implementation.Interface, module, result);
                    foreach (var method in type.Methods) if (method.HasOverrides)
                        foreach (var implementation in method.Overrides) AddReference(implementation.MethodDeclaration?.DeclaringType, module, result);
                }
                return result;
            }
            for (uint rid = 1; rid <= tables.TypeDefTable.Rows; rid++)
                if (tables.TryReadTypeDefRow(rid, out var typeRow) && typeRow.Extends != 0)
                    AddReference(md.ResolveTypeDefOrRef(typeRow.Extends), module, result);
            for (uint rid = 1; rid <= tables.InterfaceImplTable.Rows; rid++)
                if (tables.TryReadInterfaceImplRow(rid, out var implementationRow))
                    AddReference(md.ResolveTypeDefOrRef(implementationRow.Interface), module, result);
            for (uint rid = 1; rid <= tables.MethodImplTable.Rows; rid++)
                if (tables.TryReadMethodImplRow(rid, out var overrideRow))
                    AddReference(md.ResolveMethodDefOrRef(overrideRow.MethodDeclaration)?.DeclaringType, module, result);
            return result;
        }
        void AddReference(ITypeDefOrRef reference, ModuleDef caller, HashSet<TypeDef> result) {
            var type = FindReference(reference, caller);
            if (type != null) result.Add(type);
        }
        // Name-based lookup inside the modules that are already inputs, using the
        // same same-directory tie-break as ResolveCore; a duplicate identity that
        // is still ambiguous is never guessed.
        TypeDef FindReference(ITypeDefOrRef reference, ModuleDef caller) {
            if (reference is TypeDef definition) return definition;
            if (reference is TypeSpec spec) {
                if (!(spec.TypeSig.RemovePinnedAndModifiers() is GenericInstSig generic)) return null;
                reference = generic.GenericType.TypeDefOrRef;
            }
            if (reference == null) return null;
            var assembly = reference.DefinitionAssembly;
            if (assembly == null || !identities.TryGetValue(assembly.FullName, out var candidates)) return null;
            if (candidates.Length > 1) {
                string directory = Path.GetDirectoryName(moduleKey(caller));
                var local = candidates.Where(m => string.Equals(Path.GetDirectoryName(moduleKey(m)), directory,
                    Path.DirectorySeparatorChar == '\\' ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal)).ToArray();
                if (local.Length == 1) candidates = local;
                else return null;
            }
            return FindInModule(candidates[0], reference.FullName);
        }
        void Block(MethodDef method, string reason) {
            lock (gate) {
                Root(method);
                if (!blockers.TryGetValue(method, out var reasons))
                    blockers[method] = reasons = new HashSet<string>(StringComparer.Ordinal);
                reasons.Add(reason);
            }
        }
        void Join(MethodDef left, MethodDef right) {
            lock (gate) {
                if (!modules.Contains(right.Module)) { Block(left, "external contract: " + right.FullName); return; }
                var a = Root(left); var b = Root(right);
                if (a != b) parents[b] = a;
            }
        }
        IEnumerable<Use> Hierarchy(Use current) {
            var seen = new HashSet<TypeDef>();
            for (; current != null && seen.Add(current.Type); current = Resolve(Substitute(TypeSigOf(current.Type.BaseType), current.Arguments)?.ToTypeDefOrRef(), current.Type.Module))
                yield return current;
        }
        void VisitInterface(ITypeDefOrRef reference, ModuleDef caller, Use[] hierarchy, HashSet<string> visited, TypeDef implementingType) {
            if (reference == null || !visited.Add((reference.DefinitionAssembly?.FullName ?? "") + "|" + reference.FullName)) return;
            var use = Resolve(reference, caller);
            if (use == null) {
                // An unresolved interface could bind any public virtual slot on
                // this hierarchy. Keep those families visible but uneditable.
                foreach (var method in hierarchy.SelectMany(t => Methods(t.Type)).Where(m => m.IsPublic && m.IsVirtual && modules.Contains(m.Module)))
                    Block(method, "unresolved interface: " + reference.FullName);
                return;
            }
            foreach (var contract in Methods(use.Type).Where(m => !m.IsStatic)) {
                bool explicitMatch = hierarchy.Any(h => Overriding(h.Type).Any(m => m.Overrides.Any(o => {
                    var declaration = o.MethodDeclaration;
                    if (declaration.Name != contract.Name) return false;
                    var declaredUse = Resolve(Substitute(TypeSigOf(declaration.DeclaringType), h.Arguments)?.ToTypeDefOrRef(), h.Type.Module);
                    return declaredUse?.Type == contract.DeclaringType && Comparer.Equals(
                        SubstituteCached(declaration.MethodSig, declaredUse.Arguments), SubstituteCached(contract.MethodSig, use.Arguments));
                })));
                if (explicitMatch) continue;
                bool found = false;
                foreach (var owner in hierarchy) {
                    var matches = Named(owner.Type, contract.Name).Where(m => m.IsPublic && !m.IsStatic && Same(m, owner.Arguments, contract, use.Arguments)).ToArray();
                    if (matches.Length > 1) { if (modules.Contains(contract.Module)) Block(contract, "ambiguous implicit implementation: " + implementingType.FullName); found = true; break; }
                    if (matches.Length == 1) {
                        if (modules.Contains(matches[0].Module)) Join(matches[0], contract);
                        else if (modules.Contains(contract.Module)) Block(contract, "external inherited implementation: " + matches[0].FullName);
                        found = true; break;
                    }
                }
                if (!found && !implementingType.IsAbstract && modules.Contains(contract.Module)) Block(contract, "missing implementation: " + implementingType.FullName);
            }
            foreach (var parent in use.Type.Interfaces)
                VisitInterface(Substitute(TypeSigOf(parent.Interface), use.Arguments)?.ToTypeDefOrRef(), use.Type.Module, hierarchy, visited, implementingType);
        }
        Use Resolve(ITypeDefOrRef reference, ModuleDef caller) {
            if (reference == null) return null;
            if (resolves.TryGetValue((reference, caller), out var cached)) return cached;
            return resolves[(reference, caller)] = ResolveCore(reference, caller);
        }
        Use ResolveCore(ITypeDefOrRef reference, ModuleDef caller) {
            IList<TypeSig> arguments = null;
            if (reference is TypeSpec spec) {
                if (!(spec.TypeSig.RemovePinnedAndModifiers() is GenericInstSig generic)) return null;
                arguments = generic.GenericArguments; reference = generic.GenericType.TypeDefOrRef;
            }
            if (reference is TypeDef definition) return new Use(definition, arguments);
            // A host context owns the physical identity of a reference and wins
            // over the name match below, but it is only consulted in that mode:
            // ResolveTypeDef() makes dnlib walk every type of the target
            // assembly (counting and enumerating nested types through its
            // locked lazy lists), which costs milliseconds per reference and
            // dominates a large graph. The identity map below answers the same
            // lookup from modules that are already loaded.
            TypeDef resolved = null;
            if (useHostResolver) {
                resolved = reference.ResolveTypeDef();
                if (resolved != null && modules.Contains(resolved.Module)) return new Use(resolved, arguments);
            }
            if (reference.DefinitionAssembly != null && identities.TryGetValue(reference.DefinitionAssembly.FullName, out var candidates)) {
                if (candidates.Length > 1) {
                    string directory = Path.GetDirectoryName(moduleKey(caller));
                    var local = candidates.Where(m => string.Equals(Path.GetDirectoryName(moduleKey(m)), directory,
                        Path.DirectorySeparatorChar == '\\' ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal)).ToArray();
                    if (local.Length == 1) candidates = local;
                    else return null; // Never choose a duplicate identity by enumeration order.
                }
                var type = FindInModule(candidates[0], reference.FullName);
                return type == null ? null : new Use(type, arguments);
            }
            if (resolved == null) resolved = ResolveExternal(reference, caller);
            return resolved == null ? null : new Use(resolved, arguments);
        }
        // dnlib's TypeRef.ResolveTypeDef() walks every type of the target
        // assembly through its module finder because
        // ModuleDef.EnableTypeDefFindCache defaults to false; with a contract
        // reference that is milliseconds per reference and it dominated a
        // large graph. The reference's definition assembly comes from the
        // module context, and the type is then answered from the same
        // type-name index the identity path above uses. Anything the index
        // cannot see - an exported-type forwarder, a module or nested-module
        // scope, a reference without an assembly scope - still goes through
        // dnlib, so the outcome is unchanged.
        TypeDef ResolveExternal(ITypeDefOrRef reference, ModuleDef caller) {
            if (!(reference is TypeRef typeRef)) return reference.ResolveTypeDef();
            var scope = typeRef;
            for (int i = 0; i < 1000 && scope.ResolutionScope is TypeRef parent; i++) scope = parent;
            if (!(scope.ResolutionScope is AssemblyRef assemblyRef)) return reference.ResolveTypeDef();
            var sourceModule = typeRef.Module ?? caller;
            var definition = sourceModule?.Context?.AssemblyResolver?.Resolve(assemblyRef, sourceModule);
            if (definition == null) return reference.ResolveTypeDef();
            foreach (var module in definition.Modules) {
                var type = FindInModule(module, typeRef.FullName);
                if (type != null) return type;
            }
            return reference.ResolveTypeDef();
        }
        // ModuleDef.Find(fullName) rescans every type of the module, nested
        // types included, and builds a full name for each candidate; a large
        // hierarchy resolves the same module thousands of times, so index the
        // module's types once. The index matches dnlib's first-match lookup:
        // GetTypes() enumerates the same types in the same order.
        readonly Dictionary<ModuleDef, Dictionary<string, TypeDef>> typeNames = new Dictionary<ModuleDef, Dictionary<string, TypeDef>>();
        TypeDef FindInModule(ModuleDef module, string fullName) {
            if (!typeNames.TryGetValue(module, out var index)) {
                index = new Dictionary<string, TypeDef>(StringComparer.Ordinal);
                foreach (var type in module.GetTypes())
                    if (!index.ContainsKey(type.FullName)) index.Add(type.FullName, type);
                typeNames.Add(module, index);
            }
            return index.TryGetValue(fullName, out var match) ? match : null;
        }
        bool Same(MethodDef left, IList<TypeSig> leftArguments, MethodDef right, IList<TypeSig> rightArguments) =>
            Comparer.Equals(SubstituteCached(left.MethodSig, leftArguments), SubstituteCached(right.MethodSig, rightArguments));
        static MethodSig Substitute(MethodSig sig, IList<TypeSig> arguments) {
            if (sig == null || arguments == null || arguments.Count == 0) return sig;
            var result = new MethodSig(sig.CallingConvention) { GenParamCount = sig.GenParamCount, RetType = Substitute(sig.RetType, arguments) };
            foreach (var parameter in sig.Params) result.Params.Add(Substitute(parameter, arguments));
            if (sig.ParamsAfterSentinel != null) result.ParamsAfterSentinel = sig.ParamsAfterSentinel.Select(t => Substitute(t, arguments)).ToList();
            return result;
        }
        static TypeSig Substitute(TypeSig sig, IList<TypeSig> arguments, int depth = 0) {
            if (sig == null || arguments == null || arguments.Count == 0) return sig;
            if (depth > 100) throw new InvalidDataException("Cyclic generic contract signature.");
            if (sig is GenericVar variable) return variable.Number < arguments.Count ? arguments[(int)variable.Number] : sig;
            TypeSig Next() => Substitute(sig.Next, arguments, depth + 1);
            if (sig is GenericInstSig generic) return new GenericInstSig(generic.GenericType, generic.GenericArguments.Select(a => Substitute(a, arguments, depth + 1)).ToArray());
            if (sig is SZArraySig) return new SZArraySig(Next());
            if (sig is ArraySig array) return new ArraySig(Next(), array.Rank, array.Sizes, array.LowerBounds);
            if (sig is ByRefSig) return new ByRefSig(Next());
            if (sig is PtrSig) return new PtrSig(Next());
            if (sig is CModReqdSig required) return new CModReqdSig(required.Modifier, Next());
            if (sig is CModOptSig optional) return new CModOptSig(optional.Modifier, Next());
            if (sig is PinnedSig) return new PinnedSig(Next());
            if (sig is FnPtrSig || sig is ValueArraySig || sig is ModuleSig) throw new InvalidDataException("Unsupported generic contract signature element.");
            return sig;
        }
    }
}
