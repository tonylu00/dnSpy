#nullable disable
using System;
using System.Collections.Generic;
using System.Linq;
using dnlib.DotNet;

// Shared verbatim with dnSpy.Decompiler/MSBuild/MemberNameScope.cs.
namespace SourceNameMapping {
    /// <summary>Conservative C# declaration scopes for source method, type and field aliases.</summary>
    public sealed class MemberNameScope {
        readonly Dictionary<TypeDef, HashSet<TypeDef>> related = new Dictionary<TypeDef, HashSet<TypeDef>>();
        readonly Dictionary<TypeDef, HashSet<TypeDef>> bases = new Dictionary<TypeDef, HashSet<TypeDef>>();
        readonly Dictionary<string, ModuleDef[]> identities;
        readonly bool useHostResolver;
        /// <summary>
        /// <paramref name="analyze"/> restricts which modules contribute their own
        /// declarations. Every input still resolves, so a scoped type's external
        /// base chain is still walked; third-party and satellite assemblies only
        /// matter when a mapped type reaches them.
        /// </summary>
        public MemberNameScope(IEnumerable<ModuleDef> inputs, bool useHostResolver = false, IEnumerable<ModuleDef> analyze = null) {
            this.useHostResolver = useHostResolver;
            var modules = (inputs ?? Enumerable.Empty<ModuleDef>()).Where(m => m != null).Distinct().ToArray();
            var analyzed = analyze == null ? modules : analyze.Where(m => m != null).Distinct().ToArray();
            identities = modules.Where(m => m.Assembly != null).GroupBy(m => m.Assembly.FullName, StringComparer.Ordinal)
                .ToDictionary(g => g.Key, g => g.ToArray(), StringComparer.Ordinal);
            foreach (var type in analyzed.SelectMany(m => m.GetTypes())) {
                var ancestors = new HashSet<TypeDef>();
                var queue = new Queue<TypeDef>(); queue.Enqueue(type);
                while (queue.Count != 0) {
                    var next = queue.Dequeue();
                    if (!ancestors.Add(next)) continue;
                    foreach (var parent in Parents(next)) queue.Enqueue(parent);
                }
                bases[type] = ancestors;
                foreach (var ancestor in ancestors) {
                    if (!related.TryGetValue(ancestor, out var descendants)) related[ancestor] = descendants = new HashSet<TypeDef>();
                    descendants.Add(type);
                }
            }
        }
        // Inherited names hide through the base chain. References in a derived
        // body bind to the derived member, so both directions stay reserved.
        IEnumerable<TypeDef> Parents(TypeDef type) {
            var reference = type.BaseType;
            if (reference is TypeSpec spec) reference = spec.TypeSig.RemovePinnedAndModifiers().ToTypeDefOrRef();
            if (reference is TypeSpec genericSpec && genericSpec.TypeSig.RemovePinnedAndModifiers() is GenericInstSig generic)
                reference = generic.GenericType.TypeDefOrRef;
            if (reference == null) yield break;
            if (reference is TypeDef definition) { yield return definition; yield break; }
            if (useHostResolver) {
                var resolved = reference.ResolveTypeDef();
                if (resolved != null) { yield return resolved; yield break; }
            }
            if (reference.DefinitionAssembly != null && identities.TryGetValue(reference.DefinitionAssembly.FullName, out var candidates)) {
                // Ambiguous compatibility inputs contribute reservations only.
                // This never binds a reference to a guessed physical file.
                foreach (var module in candidates) {
                    var candidate = module.Find(reference.FullName, false);
                    if (candidate != null) yield return candidate;
                }
            }
        }
        /// <summary>Types that share a C# member scope through declaration or inheritance.</summary>
        public HashSet<TypeDef> Types(TypeDef type) {
            var result = new HashSet<TypeDef>();
            if (type == null) return result;
            if (bases.TryGetValue(type, out var ancestors)) result.UnionWith(ancestors);
            if (related.TryGetValue(type, out var descendants)) result.UnionWith(descendants);
            result.Add(type);
            return result;
        }
        static IEnumerable<IMemberDef> Members(TypeDef type) {
            foreach (var nested in type.NestedTypes) yield return nested;
            foreach (var field in type.Fields) yield return field;
            foreach (var method in type.Methods) yield return method;
            foreach (var property in type.Properties) yield return property;
            foreach (var evt in type.Events) yield return evt;
        }
        /// <summary>The type's simple name inside an alias, e.g. <c>Ns.Type`1</c> to <c>Type</c>.</summary>
        internal static string AliasLeaf(string alias) {
            if (string.IsNullOrEmpty(alias)) return alias;
            int index = alias.LastIndexOf('.');
            return index < 0 ? alias : alias.Substring(index + 1);
        }
        /// <summary>
        /// The namespace a type is declared in once aliases are applied. The
        /// metadata namespace is the fallback; a type alias carries the
        /// namespace the obfuscator flattened away, and two types only collide
        /// once their aliases put them into the same source namespace.
        /// </summary>
        internal static string SourceNamespace(TypeDef type, Func<IMemberDef, string> alias) {
            if (type == null) return "";
            while (type.DeclaringType != null) type = type.DeclaringType;
            if (alias != null && alias(type) is string name && name.Length != 0) {
                int dot = name.LastIndexOf('.');
                return dot < 0 ? "" : name.Substring(0, dot);
            }
            return type.Namespace.String ?? "";
        }
        static IEnumerable<TypeDef> Siblings(TypeDef type, Func<IMemberDef, string> alias) {
            if (type.DeclaringType != null) { foreach (var nested in type.DeclaringType.NestedTypes) yield return nested; yield break; }
            if (type.Module == null) yield break;
            string scope = SourceNamespace(type, alias);
            foreach (var other in type.Module.GetTypes())
                if (other.DeclaringType == null && SourceNamespace(other, alias) == scope) yield return other;
        }
        IEnumerable<TypeDef> ScopeTypes(IMemberDef member) {
            if (member is TypeDef type) {
                for (var owner = type; owner != null; owner = owner.DeclaringType) yield return owner;
                yield break;
            }
            if (member.DeclaringType == null) yield break;
            foreach (var owner in Types(member.DeclaringType)) yield return owner;
        }
        /// <summary>Every member whose source name shares the declaration scope of the requested member.</summary>
        public IEnumerable<IMemberDef> ScopeMembers(IMemberDef member, Func<IMemberDef, string> alias = null) {
            if (member == null) yield break;
            if (member is TypeDef type) {
                // Type names live in their namespace or inside their enclosing type.
                foreach (var sibling in Siblings(type, alias)) yield return sibling;
                for (var owner = type.DeclaringType; owner != null; owner = owner.DeclaringType) {
                    yield return owner;
                    foreach (var nested in Members(owner)) yield return nested;
                }
                yield break;
            }
            if (member.DeclaringType == null) yield break;
            foreach (var owner in Types(member.DeclaringType)) {
                yield return owner;
                foreach (var nested in Members(owner)) yield return nested;
            }
        }
        /// <summary>Names already occupied in the member's declaration scope.</summary>
        public HashSet<string> Reserved(IMemberDef member, Func<IMemberDef, string> alias) {
            var used = new HashSet<string>(StringComparer.Ordinal);
            foreach (var other in ScopeMembers(member, alias).Concat(OwnMembers(member))) {
                if (other == member) continue;
                used.Add(SimpleName(other.Name.String));
                if (alias != null && alias(other) is string requested && requested.Length != 0)
                    used.Add(other is TypeDef ? SimpleName(AliasLeaf(requested)) : requested);
            }
            foreach (var type in ScopeTypes(member)) {
                used.UnionWith(SourceNamespace(type, alias).Split('.'));
                used.UnionWith(type.GenericParameters.Select(p => p.Name.String));
                used.UnionWith(type.Methods.SelectMany(m => m.GenericParameters).Select(p => p.Name.String));
            }
            return used;
        }
        /// <summary>Members of the declaration scope that already own one name.</summary>
        public IEnumerable<IMemberDef> Occupants(IMemberDef member, string name, Func<IMemberDef, string> alias) {
            foreach (var other in ScopeMembers(member, alias).Concat(OwnMembers(member))) {
                if (other == member) continue;
                if (SimpleName(other.Name.String) == name) { yield return other; continue; }
                if (alias != null && alias(other) is string requested && (other is TypeDef ? SimpleName(AliasLeaf(requested)) : requested) == name) yield return other;
            }
        }
        /// <summary>Whether two methods are the same C# overload slot.</summary>
        public static bool SameSignature(MethodDef left, MethodDef right) {
            var first = left?.MethodSig;
            var second = right?.MethodSig;
            if (first == null || second == null) return first == second;
            if (first.GenParamCount != second.GenParamCount || first.Params.Count != second.Params.Count) return false;
            for (int i = 0; i < first.Params.Count; i++)
                if (first.Params[i].FullName != second.Params[i].FullName) return false;
            return true;
        }
        // A member name cannot equal the name of its own enclosing type, so a
        // renamed type reserves its own declarations as well as its siblings.
        static IEnumerable<IMemberDef> OwnMembers(IMemberDef member) => member is TypeDef type ? Members(type) : Enumerable.Empty<IMemberDef>();
        /// <summary>Types whose method bodies can name the member by its source name.</summary>
        public IEnumerable<TypeDef> BodyScopeTypes(IMemberDef member) {
            var types = new HashSet<TypeDef>();
            if (member is TypeDef type) {
                types.UnionWith(Types(type));
                for (var owner = type.DeclaringType; owner != null; owner = owner.DeclaringType) types.Add(owner);
            } else if (member.DeclaringType != null) {
                if (related.TryGetValue(member.DeclaringType, out var descendants)) types.UnionWith(descendants);
                else types.Add(member.DeclaringType);
            }
            // A nested type's body can still name the outer declaration simply.
            var pending = new Queue<TypeDef>(types);
            while (pending.Count != 0)
                foreach (var nested in pending.Dequeue().NestedTypes)
                    if (types.Add(nested)) pending.Enqueue(nested);
            return types;
        }
        /// <summary>Removes the metadata generic-arity suffix used in C# identifiers.</summary>
        public static string SimpleName(string name) {
            if (string.IsNullOrEmpty(name)) return name;
            int index = name.LastIndexOf('`');
            return index >= 0 && index + 1 < name.Length && name.Skip(index + 1).All(char.IsDigit) ? name.Substring(0, index) : name;
        }
        /// <summary>The type's own generic arity, excluding the enclosing type's.</summary>
        internal static int TypeArity(TypeDef type) =>
            Math.Max(0, type.GenericParameters.Count - (type.DeclaringType?.GenericParameters.Count ?? 0));
    }
    /// <summary>Scoped source alias claims; one contract family may share a name.</summary>
    public sealed class MemberNameClaims {
        readonly MemberNameScope scope;
        readonly Dictionary<IMemberDef, string> aliases = new Dictionary<IMemberDef, string>();
        readonly Dictionary<IMemberDef, string> families = new Dictionary<IMemberDef, string>();
        public MemberNameClaims(MemberNameScope scope) => this.scope = scope;
        public string Alias(IMemberDef member) => member != null && aliases.TryGetValue(member, out var name) ? name : null;
        /// <summary>Whether another declaration in the same C# scope owns the name.</summary>
        public bool Conflicts(IMemberDef member, string alias, string family) {
            if (member == null || string.IsNullOrEmpty(alias)) return true;
            // Sharing is legal only inside one contract family: every other
            // occupant reserves the name, including another family's alias and
            // every declaration that carries no source alias at all.
            if (!scope.Reserved(member, other => IsFamily(other, family) ? null : Alias(other)).Contains(alias)) return false;
            // C# allows overloads: two methods of one type may share a name when
            // their parameter lists differ, and the restore instruction carries
            // the signature so each overload still restores independently.
            var occupants = scope.Occupants(member, alias, Alias).Where(other => !IsFamily(other, family)).ToArray();
            if (occupants.Length == 0) return true;   // namespace, generic parameter or unmodified declaration
            // C# also distinguishes types by generic arity, so one declaration
            // space may hold IIoTTaskState and IIoTTaskState<T> at once - the
            // pair the ETS 6.4 build declares. Only that shape is exempt: a
            // nested type still cannot repeat its enclosing type's leaf, and a
            // same-arity sibling still collides.
            if (member is TypeDef candidate && candidate.DeclaringType == null &&
                occupants.All(other => other is TypeDef occupant && occupant.DeclaringType == null &&
                    MemberNameScope.TypeArity(occupant) != MemberNameScope.TypeArity(candidate)))
                return false;
            if (!(member is MethodDef method)) return true;
            foreach (var other in occupants)
                if (!(other is MethodDef otherMethod) || MemberNameScope.SameSignature(method, otherMethod)) return true;
            return false;
        }
        bool IsFamily(IMemberDef member, string family) =>
            family != null && families.TryGetValue(member, out var otherFamily) && otherFamily == family;
        public void Claim(IMemberDef member, string alias, string family) {
            aliases[member] = alias;
            if (family == null) families.Remove(member); else families[member] = family;
        }
    }
}
