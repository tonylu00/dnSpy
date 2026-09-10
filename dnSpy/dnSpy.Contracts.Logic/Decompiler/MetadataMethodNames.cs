using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Runtime.CompilerServices;
using dnlib.DotNet;

namespace dnSpy.Contracts.Decompiler {
	/// <summary>Stable C# method aliases and reversible runtime-name instructions.</summary>
	public static class MetadataMethodNames {
		/// <summary>Assembly instructions for restoring aliased methods.</summary>
		public const string Prefix = "dnSpy.metadata.method-name.v1|";
		/// <summary>Evidence that two original private definitions share their complete signature.</summary>
		public static bool HasOriginalDuplicate(MethodDef method) => method.IsPrivate && !method.IsVirtual && !method.HasOverrides &&
			method.DeclaringType.Methods.Any(other => other != method && other.IsPrivate && !other.IsVirtual && !other.HasOverrides &&
				other.Name == method.Name && new SigComparer().Equals(other.MethodSig, method.MethodSig));
		/// <summary>Returns the source identifier from the resolved declaring module.</summary>
		public static string GetName(MethodDef method) => SourceNameAliases.Get(method) ?? (method.Module != null && names.GetValue(method.Module, Find).TryGetValue(method, out var alias) ? alias : method.Name.String);
		static readonly ConditionalWeakTable<ModuleDef, string[]> mappings = new ConditionalWeakTable<ModuleDef, string[]>();
		/// <summary>Instructions use resolved assembly context and source owner/alias pairs.</summary>
		public static string[] GetMappings(ModuleDef module) => mappings.GetValue(module, CreateMappings);
		static string[] CreateMappings(ModuleDef module) {
			var localTypes = module.GetTypes().ToArray();
			var usedMethods = new HashSet<MethodDef>(localTypes.SelectMany(t => t.Methods));
			foreach (var reference in module.GetMemberRefs().Where(r => r.IsMethodRef)) {
				var method = reference.ResolveMethodDef();
				if (method != null) usedMethods.Add(method);
			}
			var types = new HashSet<TypeDef>(localTypes);
			foreach (var reference in module.GetTypeRefs()) {
				var type = reference.ResolveTypeDef();
				if (type != null) types.Add(type);
			}
			foreach (var method in usedMethods) types.Add(method.DeclaringType);
			var result = new HashSet<string>(StringComparer.Ordinal);
			Func<string, string> encode = value => Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes(value));
			foreach (var type in types.Where(t => t?.Module?.Assembly != null)) {
				var visited = new HashSet<TypeDef>();
				for (var owner = type; owner != null && visited.Add(owner); owner = owner.BaseType?.ResolveTypeDef()) {
					foreach (var method in owner.Methods.Where(usedMethods.Contains)) {
						var alias = GetName(method);
						if (alias == method.Name.String) continue;
						// C# may encode a method reference through an inheriting receiver.
						// Record that source owner too, preserving the original target body.
						var assembly = type.DefinitionAssembly;
						result.Add(Prefix + string.Join("|", new[] { MetadataTypeNames.SourceFullName(type), assembly.Name.String,
							assembly.Version.ToString(), assembly.Culture.String ?? "", alias }.Select(encode)) + "|" + Convert.ToBase64String(method.Name.Data));
					}
				}
			}
			return result.OrderBy(s => s, StringComparer.Ordinal).ToArray();
		}

		static readonly ConditionalWeakTable<ModuleDef, Dictionary<MethodDef, string>> names = new ConditionalWeakTable<ModuleDef, Dictionary<MethodDef, string>>();
		static bool IsGenerated(TypeDef type) {
			for (; type != null; type = type.DeclaringType)
				if (type.CustomAttributes.Any(a => a.TypeFullName == "System.Runtime.CompilerServices.CompilerGeneratedAttribute")) return true;
			return false;
		}
		static MethodDef? FindBaseMethod(MethodDef method) {
			if (!method.IsVirtual || method.IsNewSlot) return null;
			var reference = method.DeclaringType.BaseType;
			var visited = new HashSet<TypeDef>();
			while (reference != null) {
				var type = reference.ResolveTypeDef();
				if (type == null || !visited.Add(type)) break;
				var arguments = ((reference as TypeSpec)?.TypeSig as GenericInstSig)?.GenericArguments;
				var matches = type.Methods.Where(m => m.IsVirtual && m.Name == method.Name &&
					new SigComparer().Equals(GenericArgumentResolver.Resolve(m.MethodSig, arguments, null), method.MethodSig)).ToArray();
				if (matches.Length == 1) return matches[0];
				if (matches.Length > 1) throw new InvalidOperationException("Ambiguous generated method override family.");
				reference = GenericArgumentResolver.Resolve(type.BaseType?.ToTypeSig(), arguments, null)?.ToTypeDefOrRef();
			}
			return null;
		}
		static Dictionary<MethodDef, string> Find(ModuleDef module) {
			var result = new Dictionary<MethodDef, string>();
			var allocated = new Dictionary<TypeDef, HashSet<string>>();
			var visiting = new HashSet<TypeDef>();
			HashSet<string> Allocate(TypeDef type) {
				if (allocated.TryGetValue(type, out var previous)) return previous;
				if (!visiting.Add(type)) return new HashSet<string>(StringComparer.Ordinal);
				var used = new HashSet<string>(type.Fields.Select(f => f.Name.String).Concat(type.Methods.Select(m => m.Name.String))
					.Concat(type.Properties.Select(p => p.Name.String)).Concat(type.Events.Select(e => e.Name.String))
					.Concat(type.NestedTypes.Select(MetadataTypeNames.GetName)), StringComparer.Ordinal);
				used.Add(MetadataTypeNames.GetName(type));
				used.UnionWith(type.Methods.Select(SourceNameAliases.Get).Where(n => n != null).Select(n => n!));
				used.UnionWith(type.GenericParameters.Select(p => p.Name.String));
				used.UnionWith(type.Methods.SelectMany(m => m.GenericParameters).Select(p => p.Name.String));
				var parent = type.BaseType?.ResolveTypeDef();
				if (parent != null) used.UnionWith(Allocate(parent));
				bool generated = IsGenerated(type);
				var collisions = new HashSet<MethodDef>();
				var comparer = new SigComparer();
				foreach (var group in type.Methods.Where(m => !m.IsConstructor && m.MethodSig != null).GroupBy(m => new { Name = m.Name.String, Arity = m.GenericParameters.Count, Count = m.MethodSig.Params.Count })) {
					var candidates = group.ToArray();
					if (candidates.Length < 2) continue;
					foreach (var method in candidates.Where(m => m.IsPrivate && !m.IsVirtual && !m.HasOverrides && m.SemanticsAttributes == 0))
						if (candidates.Any(other => other != method && method.MethodSig.Params.Zip(other.MethodSig.Params,
							(a, b) => comparer.Equals(a, b)).All(equal => equal))) collisions.Add(method);
				}
				foreach (var method in type.Methods.OrderBy(m => m.MDToken.Raw)) {
					bool collision = collisions.Contains(method);
					if (method.IsConstructor || method.HasOverrides || (!collision && (MetadataTypeNames.IsIdentifier(method.Name) ||
						!(generated || method.CustomAttributes.Any(a => a.TypeFullName == "System.Runtime.CompilerServices.CompilerGeneratedAttribute"))))) continue;
					var baseMethod = FindBaseMethod(method);
					if (baseMethod != null && result.TryGetValue(baseMethod, out var shared)) {
						result.Add(method, shared); used.Add(shared); continue;
					}
					string stem = (collision && MetadataTypeNames.IsIdentifier(method.Name) ? method.Name.String + "_" : "method_") + method.MDToken.Raw.ToString("X8", CultureInfo.InvariantCulture), alias = stem;
					for (int suffix = 1; !used.Add(alias); suffix++) alias = stem + "_" + suffix.ToString(CultureInfo.InvariantCulture);
					result.Add(method, alias);
				}
				visiting.Remove(type);
				return allocated[type] = used;
			}
			foreach (var type in module.GetTypes()) Allocate(type);
			return result;
		}
	}
}
