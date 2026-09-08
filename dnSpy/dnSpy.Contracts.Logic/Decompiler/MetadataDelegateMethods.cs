using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Runtime.CompilerServices;
using dnlib.DotNet;

namespace dnSpy.Contracts.Decompiler {
	/// <summary>Tracks source companions for methods whose runtime owner is a delegate.</summary>
	public static class MetadataDelegateMethods {
		/// <summary>Identifies the temporary mapping attribute.</summary>
		public const string Feature = "dnSpy.metadata.delegate-methods.v1";
		sealed class State {
			public readonly SortedDictionary<string, string> Maps = new SortedDictionary<string, string>(StringComparer.Ordinal);
			public string? AttributeName;
		}
		static readonly ConditionalWeakTable<ModuleDef, Dictionary<TypeDef, string>> names = new ConditionalWeakTable<ModuleDef, Dictionary<TypeDef, string>>();
		static readonly ConditionalWeakTable<ModuleDef, State> requests = new ConditionalWeakTable<ModuleDef, State>();
		/// <summary>Returns the companion name for supported delegate methods.</summary>
		public static string? GetName(TypeDef type) => type.BaseType?.FullName == "System.MulticastDelegate" && type.Module != null && names.GetValue(type.Module, Find).TryGetValue(type, out var name) ? name : null;
		static Dictionary<TypeDef, string> Find(ModuleDef module) {
			var result = new Dictionary<TypeDef, string>();
			foreach (var type in module.GetTypes()) {
				if (type.BaseType?.FullName != "System.MulticastDelegate" || type.HasProperties || type.HasEvents || type.HasNestedTypes ||
					!type.Methods.Any(m => m.HasBody) || type.Methods.Any(m => m.HasBody && (!m.IsStatic || m.IsConstructor)) ||
					type.Methods.Any(m => !m.HasBody && (!m.IsRuntime || m.IsStatic ||
						(m.Name != ".ctor" && m.Name != "Invoke" && m.Name != "BeginInvoke" && m.Name != "EndInvoke"))) ||
					type.Fields.Any(f => !MetadataOnlyFields.Contains(f))) continue;
				var used = new HashSet<string>((type.DeclaringType?.NestedTypes ?? module.Types).Select(t => t.Name.String.Split('`')[0]));
				if (type.DeclaringType == null) used.UnionWith(module.Types.Select(t => t.Namespace.String.Split('.')[0]));
				else used.UnionWith(type.DeclaringType.Methods.Select(m => m.Name.String).Concat(type.DeclaringType.Fields.Select(f => f.Name.String)));
				used.UnionWith(result.Values);
				string root = "__DnSpyDelegateMethods_" + type.MDToken.Raw.ToString("X8", CultureInfo.InvariantCulture), name = root;
				for (int suffix = 1; used.Contains(name); suffix++) name = root + "_" + suffix.ToString(CultureInfo.InvariantCulture);
				result[type] = name;
			}
			return result;
		}
		/// <summary>Registers fully qualified unbound C# type expressions for the build task.</summary>
		public static void Request(ModuleDef module, string companion, string target) {
			var state = requests.GetOrCreateValue(module);
			lock (state) state.Maps[companion] = target;
		}
		/// <summary>Returns requested mappings, ordered independently of export scheduling.</summary>
		public static KeyValuePair<string, string>[] GetMappings(ModuleDef module) {
			if (!requests.TryGetValue(module, out var state)) return Array.Empty<KeyValuePair<string, string>>();
			lock (state) return state.Maps.ToArray();
		}
		/// <summary>Allocates a module-local mapping attribute without shadowing user types.</summary>
		public static string GetAttributeName(ModuleDef module) {
			var state = requests.GetOrCreateValue(module);
			lock (state) {
				if (state.AttributeName != null) return state.AttributeName;
				var used = new HashSet<string>(module.Types.Select(t => string.IsNullOrEmpty(t.Namespace) ? t.Name.String.Split('`')[0] : t.Namespace.String.Split('.')[0]));
				used.UnionWith(module.GetTypeRefs().Select(t => string.IsNullOrEmpty(t.Namespace) ? t.Name.String.Split('`')[0] : t.Namespace.String.Split('.')[0]));
				string root = "__DnSpyDelegateMethodsMapAttribute", name = root;
				for (int suffix = 1; used.Contains(name); suffix++) name = root + suffix.ToString(CultureInfo.InvariantCulture);
				return state.AttributeName = name;
			}
		}
	}
}
