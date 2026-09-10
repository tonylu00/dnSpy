using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using dnlib.DotNet;

namespace dnSpy.Contracts.Decompiler {
	/// <summary>Static CLR types referenced in value signatures require a C# projection.</summary>
	public static class MetadataStaticValues {
		static readonly ConditionalWeakTable<ModuleDef, HashSet<TypeDef>> cache = new ConditionalWeakTable<ModuleDef, HashSet<TypeDef>>();
		static readonly ConditionalWeakTable<ModuleDef, HashSet<TypeDef>> projectUses = new ConditionalWeakTable<ModuleDef, HashSet<TypeDef>>();
		/// <summary>Whether this type needs an instance-capable source declaration.</summary>
		public static bool Required(TypeDef type) {
			if (type.Module == null) return false;
			if (projectUses.TryGetValue(type.Module, out var uses)) lock (uses) if (uses.Contains(type)) return true;
			return cache.GetValue(type.Module, Find).Contains(type);
		}
		/// <summary>Register cross-module value signatures before parallel decompilation begins.</summary>
		public static void RegisterProjects(IEnumerable<ModuleDef> modules) {
			var roots = modules.Where(m => m.IsILOnly).Distinct().ToArray();
			var locations = roots.Where(m => !string.IsNullOrEmpty(m.Location)).ToLookup(m => System.IO.Path.GetFullPath(m.Location), System.StringComparer.OrdinalIgnoreCase);
			foreach (var module in roots) foreach (var referenced in FindReferenced(module)) {
				var uses = projectUses.GetOrCreateValue(referenced.Module);
				lock (uses) uses.Add(referenced);
				if (string.IsNullOrEmpty(referenced.Module.Location)) continue;
				foreach (var root in locations[System.IO.Path.GetFullPath(referenced.Module.Location)]) {
					if (root.Mvid != referenced.Module.Mvid) continue;
					var type = root.ResolveToken(referenced.MDToken.Raw) as TypeDef;
					if (type == null || !type.IsAbstract || !type.IsSealed || type.FullName != referenced.FullName) continue;
					uses = projectUses.GetOrCreateValue(root);
					lock (uses) uses.Add(type);
				}
			}
		}
		static HashSet<TypeDef> Find(ModuleDef module) {
			return new HashSet<TypeDef>(FindReferenced(module).Where(t => t.Module == module));
		}
		static HashSet<TypeDef> FindReferenced(ModuleDef module) {
			var result = new HashSet<TypeDef>();
			void Inspect(TypeSig signature) {
				if (signature == null) return;
				var definition = signature.ToTypeDefOrRef()?.ResolveTypeDef();
				if (definition?.Module != null && definition.IsAbstract && definition.IsSealed &&
					!definition.IsInterface && !definition.Methods.Any(m => m.IsInstanceConstructor)) result.Add(definition);
				if (signature.Next != null) Inspect(signature.Next);
				if (signature is GenericInstSig generic) foreach (var argument in generic.GenericArguments) Inspect(argument);
			}
			foreach (var type in module.GetTypes()) {
				foreach (var field in type.Fields) Inspect(field.FieldType);
				foreach (var method in type.Methods) {
					if (method.MethodSig != null) {
						Inspect(method.MethodSig.RetType);
						foreach (var parameter in method.MethodSig.Params) Inspect(parameter);
					}
					if (method.HasBody) foreach (var local in method.Body.Variables) Inspect(local.Type);
				}
			}
			return result;
		}
	}
}
