using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using dnlib.DotNet;
using dnlib.DotNet.Emit;

// Portable metadata/observation join. This does not rename, restore, or retire
// symbols. The caller must first validate complete physical source coverage.
internal static class StateMachineSourceCoverage {
    static readonly StringComparer PathComparer = OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal;
    internal sealed record Owner(uint Token, string Signature, string Evidence, string Kind);
    internal sealed record Witness(uint RootTypeToken, string Kind, uint OwnerToken, uint ImplementationToken, uint ImplementationTypeToken);
    internal sealed record Field(uint Token, string Signature, bool Declared, uint[] PrintedOwners, Binding[] SourceBindings);
    internal sealed record Binding(uint OwnerToken, string SourceName);
    internal sealed record Entry(uint TypeToken, string Signature, string Status, Owner[] Owners, Witness[] Witnesses,
        uint[][] CanonicalOwnerPaths, uint[] MemberTokens, uint[] DeclaredMembers, uint[] PrintedMembers, uint[] CrossModulePrintedMembers, Field[] Fields);

    static uint Token(JsonElement value, string name) => value.GetProperty(name).GetUInt32();
    static bool Framework(IAssembly? assembly) {
        string name = assembly?.Name.String ?? "", key = assembly?.PublicKeyOrToken?.Token?.ToString() ?? "";
        return name == "mscorlib" && key == "b77a5c561934e089" ||
            name == "System.Runtime" && key == "b03f5f7f11d50a3a" ||
            name == "netstandard" && key == "cc7b13ffcd2ddd51" ||
            name == "System.Private.CoreLib" && key == "7cec85d7bea7798e";
    }
    static string? Kind(CustomAttribute attribute) => attribute.TypeFullName switch {
        "System.Runtime.CompilerServices.AsyncStateMachineAttribute" => "AsyncMethod",
        "System.Runtime.CompilerServices.IteratorStateMachineAttribute" => "IteratorMethod",
        "System.Runtime.CompilerServices.AsyncIteratorStateMachineAttribute" => "AsyncIteratorMethod",
        _ => null
    };
    static TypeDef? Local(TypeSig? signature, ModuleDef module) {
        var target = signature is GenericInstSig generic ? generic.GenericType.TypeDefOrRef : (signature as TypeDefOrRefSig)?.TypeDefOrRef;
        // Do not resolve a same-name TypeRef through a global assembly resolver.
        return target is TypeDef type && type.Module == module ? type : null;
    }
    static void Require(bool condition, string message) { if (!condition) throw new InvalidDataException(message); }

    internal static Entry[] Observe(ModuleDefMD module, JsonElement report) {
        var roots = report.GetProperty("Roots").EnumerateArray().ToArray();
        Require(roots.All(r => r.GetProperty("CompleteTypeScope").GetBoolean()), "State coverage requires complete type scopes.");
        var declarations = roots.SelectMany(r => r.GetProperty("DeclarationTokens").EnumerateArray()).Select(v => v.GetUInt32()).ToHashSet();
        bool writerCoverage = roots.All(r => r.TryGetProperty("PrintedReferenceCoverage", out var value) && value.GetBoolean());
        var printed = new Dictionary<uint, HashSet<uint>>();
        var fields = new Dictionary<uint, List<Binding>>();
        var witnesses = new List<Witness>();
        foreach (var root in roots) {
            uint rootToken = Token(root, "RootTypeToken");
            foreach (var witness in root.GetProperty("BodyWitnesses").EnumerateArray()) {
                var item = new Witness(rootToken, witness.GetProperty("Kind").GetString()!, Token(witness, "OwnerToken"),
                    Token(witness, "ImplementationToken"), Token(witness, "ImplementationTypeToken"));
                Require((item.OwnerToken == 0 || module.ResolveToken(item.OwnerToken) is IMemberDef) && module.ResolveToken(item.ImplementationToken) is MethodDef method &&
                    method.Module == module && method.DeclaringType.MDToken.Raw == item.ImplementationTypeToken, "State source witness physical definition mismatch.");
                witnesses.Add(item);
            }
            foreach (var binding in root.GetProperty("FieldBindings").EnumerateArray()) {
                uint token = Token(binding, "FieldToken");
                Require(module.ResolveToken(token) is FieldDef field && field.Module == module, "State source binding is not a local field.");
                if (!fields.TryGetValue(token, out var bindings)) fields[token] = bindings = new();
                bindings.Add(new(Token(binding, "OwnerToken"), binding.GetProperty("SourceName").GetString()!));
            }
            if (!root.TryGetProperty("PrintedReferences", out var uses)) continue;
            foreach (var use in uses.EnumerateArray()) {
                if (use.GetProperty("IsDefinition").GetBoolean() || use.GetProperty("IsImplementationAnnotation").GetBoolean()) continue;
                uint token = Token(use, "DefinitionToken");
                if (token == 0 || !PathComparer.Equals(use.GetProperty("DefinitionModulePath").GetString(), module.Location)) continue;
                if (!printed.TryGetValue(token, out var owners)) printed[token] = owners = new();
                owners.Add(Token(use, "OwnerToken"));
            }
        }
        var machines = new Dictionary<TypeDef, List<Owner>>();
        void Add(TypeDef type, MethodDef method, string evidence, string kind) {
            if (!machines.TryGetValue(type, out var owners)) machines[type] = owners = new();
            owners.Add(new(method.MDToken.Raw, method.FullName, evidence, kind));
        }
        foreach (var method in module.GetTypes().SelectMany(t => t.Methods)) {
            foreach (var attribute in method.CustomAttributes) {
                string? kind = Kind(attribute);
                if (kind == null) continue;
                bool trusted = Framework(attribute.AttributeType.DefinitionAssembly) || kind == "AsyncIteratorMethod" &&
                    attribute.AttributeType.DefinitionAssembly?.Name == "Microsoft.Bcl.AsyncInterfaces" &&
                    attribute.AttributeType.DefinitionAssembly.PublicKeyOrToken?.Token?.ToString() == "cc7b13ffcd2ddd51";
                if (trusted && attribute.ConstructorArguments.Count == 1 && attribute.ConstructorArguments[0].Value is TypeSig signature &&
                    Local(signature, module) is TypeDef machine) Add(machine, method, "TrustedStateMachineAttribute", kind);
            }
            if (!method.HasBody) continue;
            foreach (var instruction in method.Body.Instructions) {
                if (instruction.OpCode.Code is not (Code.Call or Code.Callvirt) || instruction.Operand is not MethodSpec spec ||
                    spec.Method.Name != "Start" || !Framework(spec.Method.DeclaringType.DefinitionAssembly)) continue;
                var builder = spec.Method.DeclaringType is TypeSpec { TypeSig: GenericInstSig generic } ? generic.GenericType.TypeDefOrRef : spec.Method.DeclaringType;
                if (builder.Namespace != "System.Runtime.CompilerServices" || builder.Name.String is not
                    ("AsyncTaskMethodBuilder" or "AsyncTaskMethodBuilder`1" or "AsyncVoidMethodBuilder" or "AsyncValueTaskMethodBuilder" or "AsyncValueTaskMethodBuilder`1") ||
                    spec.Method.MethodSig?.GenParamCount != 1 || spec.Method.MethodSig.Params.Count != 1 ||
                    spec.Method.MethodSig.Params[0] is not ByRefSig { Next: GenericMVar { Number: 0 } } ||
                    spec.Method.MethodSig.RetType.ElementType != ElementType.Void || spec.GenericInstMethodSig.GenericArguments.Count != 1) continue;
                if (Local(spec.GenericInstMethodSig.GenericArguments[0], module) is { IsValueType: true } machine)
                    Add(machine, method, "TrustedFrameworkBuilderStart", "AsyncMethod");
            }
        }
        // Attribute-free older iterators still produce a physical rewrite witness.
        // Keep them visible, without manufacturing an independent metadata edge.
        foreach (var witness in witnesses.Where(w => w.Kind is "AsyncMethod" or "IteratorMethod" or "AsyncIteratorMethod")) {
            var type = (TypeDef)module.ResolveToken(witness.ImplementationTypeToken);
            if (!machines.ContainsKey(type)) machines[type] = new();
        }
        var parents = witnesses.GroupBy(w => w.ImplementationToken).ToDictionary(g => g.Key, g => g.Select(w => w.OwnerToken).Distinct().OrderBy(t => t).ToArray());
        // Source accessors are owned by their declared property/event row.
        foreach (var type in module.GetTypes()) {
            foreach (var property in type.Properties) foreach (var method in property.GetMethods.Concat(property.SetMethods).Concat(property.OtherMethods))
                AddParent(method.MDToken.Raw, property.MDToken.Raw);
            foreach (var evt in type.Events) foreach (var method in new[] { evt.AddMethod, evt.RemoveMethod, evt.InvokeMethod }.Where(m => m != null).Concat(evt.OtherMethods))
                AddParent(method!.MDToken.Raw, evt.MDToken.Raw);
        }
        void AddParent(uint child, uint parent) {
            parents.TryGetValue(child, out var existing);
            parents[child] = (existing ?? Array.Empty<uint>()).Append(parent).Distinct().OrderBy(t => t).ToArray();
        }
        uint[][] Paths(uint owner) {
            // Bound by the finite physical definition graph. Cyclic and ambiguous
            // rewrite chains never become guessed canonical owners.
            var queue = new Queue<uint[]>(); queue.Enqueue(new[] { owner });
            var found = new List<uint[]>(); var visited = new HashSet<uint>();
            while (queue.Count != 0) {
                var path = queue.Dequeue(); uint current = path[^1];
                if (!visited.Add(current)) continue;
                if (declarations.Contains(current)) { found.Add(path); continue; }
                if (parents.TryGetValue(current, out var next)) foreach (uint parent in next) queue.Enqueue(path.Append(parent).ToArray());
            }
            return found.OrderBy(p => p[^1]).ToArray();
        }
        return machines.OrderBy(p => p.Key.MDToken.Raw).Select(pair => {
            TypeDef type = pair.Key;
            var owners = pair.Value.Distinct().OrderBy(o => o.Token).ThenBy(o => o.Evidence, StringComparer.Ordinal).ToArray();
            var observed = witnesses.Where(w => w.ImplementationTypeToken == type.MDToken.Raw && w.Kind is "AsyncMethod" or "IteratorMethod" or "AsyncIteratorMethod")
                .Distinct().OrderBy(w => w.RootTypeToken).ThenBy(w => w.OwnerToken).ToArray();
            var matched = observed.Where(w => owners.Any(o => o.Token == w.OwnerToken && o.Kind == w.Kind)).ToArray();
            uint[] members = new IMemberDef[] { type }.Concat(type.Methods).Concat(type.Fields).Concat(type.Properties).Concat(type.Events).Select(d => d.MDToken.Raw).ToArray();
            uint[] declared = members.Where(declarations.Contains).OrderBy(t => t).ToArray(), uses = members.Where(printed.ContainsKey).OrderBy(t => t).ToArray();
            var paths = matched.SelectMany(w => Paths(w.OwnerToken)).DistinctBy(p => string.Join(",", p)).ToArray();
            string status = !writerCoverage ? "MissingWriterCoverage" : declared.Length != 0 ? "RetainedDeclaration" : uses.Length != 0 ? "SurvivingSourceUse" :
                owners.Length == 0 ? "MissingIndependentOwnerEvidence" : owners.Select(o => o.Token).Distinct().Count() != 1 ? "AmbiguousMetadataOwners" :
                matched.Length == 0 ? "MissingMatchingBodyWitness" : observed.Any(w => !matched.Contains(w)) ? "UnmatchedBodyWitness" :
                paths.Length == 0 ? "UnresolvedCanonicalOwner" : paths.Select(p => p[^1]).Distinct().Count() != 1 ? "AmbiguousCanonicalOwners" : "MergedSourceObserved";
            var stateFields = type.Fields.OrderBy(f => f.MDToken.Raw).Select(f => new Field(f.MDToken.Raw, f.FullName, declarations.Contains(f.MDToken.Raw),
                printed.TryGetValue(f.MDToken.Raw, out var printedOwners) ? printedOwners.OrderBy(t => t).ToArray() : Array.Empty<uint>(),
                fields.TryGetValue(f.MDToken.Raw, out var bindings) ? bindings.Distinct().OrderBy(b => b.OwnerToken).ThenBy(b => b.SourceName, StringComparer.Ordinal).ToArray() : Array.Empty<Binding>())).ToArray();
            return new Entry(type.MDToken.Raw, type.FullName, status, owners, observed, paths, members.OrderBy(t => t).ToArray(), declared, uses, Array.Empty<uint>(), stateFields);
        }).ToArray();
    }

    internal static Entry JoinCrossModuleUses(Entry entry, Func<uint, bool> used) {
        var members = entry.MemberTokens.Where(used).ToArray();
        return entry with { CrossModulePrintedMembers = members,
            Status = members.Length != 0 && entry.Status == "MergedSourceObserved" ? "SurvivingCrossModuleSourceUse" : entry.Status };
    }
}
