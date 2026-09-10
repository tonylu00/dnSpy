using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using dnlib.DotNet;

namespace dnSpy.Contracts.Decompiler {
	/// <summary>Temporary source entry points for hidden protected, nonvirtual methods.</summary>
	public static class MetadataProtectedCalls {
		/// <summary>Marks a compilation stub and encodes the original method name.</summary>
		public const string Prefix = "dnSpy.metadata.protected-call.v1|";
		static readonly ConditionalWeakTable<ModuleDef, Dictionary<MethodDef, string>> names = new ConditionalWeakTable<ModuleDef, Dictionary<MethodDef, string>>();
		/// <summary>Whether this module needs compilation stubs.</summary>
		public static bool Required(ModuleDef module) => names.GetValue(module, Find).Count != 0;
		/// <summary>Returns the stable source stub name for a method.</summary>
		public static string? GetName(MethodDef method) => method.Module != null && names.GetValue(method.Module, Find).TryGetValue(method, out var name) ? name : null;
		static Dictionary<MethodDef, string> Find(ModuleDef module) {
			var types = module.GetTypes().ToArray();
			var candidates = new HashSet<MethodDef>();
			foreach (var type in types) {
				var hidden = new HashSet<string>(type.Methods.Select(m => m.Name.String).Concat(type.Fields.Select(f => f.Name.String))
					.Concat(type.Properties.Select(p => p.Name.String)).Concat(type.Events.Select(e => e.Name.String)));
				var visited = new HashSet<TypeDef>();
				for (var parent = type.BaseType?.ResolveTypeDef(); parent != null && visited.Add(parent); parent = parent.BaseType?.ResolveTypeDef()) {
					if (parent.Module != module) continue;
					foreach (var method in parent.Methods)
						if (method.IsFamily && !method.IsStatic && !method.IsVirtual && !method.IsSpecialName && method.HasBody &&
							MetadataTypeNames.IsIdentifier(method.Name) && hidden.Contains(method.Name)) candidates.Add(method);
				}
			}
			var result = new Dictionary<MethodDef, string>();
			var used = new HashSet<string>(types.SelectMany(t => t.Methods.Select(m => m.Name.String).Concat(t.Fields.Select(f => f.Name.String))).Concat(types.Select(MetadataTypeNames.GetName)));
			used.UnionWith(module.GetMemberRefs().Select(r => r.Name.String));
			foreach (var method in candidates.OrderBy(m => m.MDToken.Raw)) {
				string stem = "__DnSpyProtected_" + method.MDToken.Raw.ToString("X8"), name = stem;
				for (int suffix = 1; !used.Add(name); suffix++) name = stem + "_" + suffix;
				result.Add(method, name);
			}
			return result;
		}
	}
}
