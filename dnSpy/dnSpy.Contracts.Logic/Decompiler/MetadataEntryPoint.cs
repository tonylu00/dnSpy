using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using dnlib.DotNet;

namespace dnSpy.Contracts.Decompiler {
	/// <summary>Compilation scaffolding for CLR entry points not named Main.</summary>
	public static class MetadataEntryPoint {
		/// <summary>Marks the original entry method.</summary>
		public const string Feature = "dnSpy.metadata.entry-point.v1";
		/// <summary>Marks the temporary compiler entry point class.</summary>
		public const string StubFeature = "dnSpy.metadata.entry-point-stub.v1";
		static readonly ConditionalWeakTable<ModuleDef, string> names = new ConditionalWeakTable<ModuleDef, string>();
		/// <summary>Returns a module-local stub name when a metadata entry point needs restoration.</summary>
		public static string? GetName(ModuleDef module) {
			var entry = module.EntryPoint;
			if (entry == null) return null;
			bool needed = entry.Name != "Main";
			for (var owner = entry.DeclaringType; owner != null; owner = owner.DeclaringType)
				needed |= MetadataTypeNames.GetName(owner) != MetadataTypeNames.SimpleName(owner.Name);
			return needed ? names.GetValue(module, CreateName) : null;
		}
		static string CreateName(ModuleDef module) {
			var used = new HashSet<string>(module.Types.Select(t => string.IsNullOrEmpty(t.Namespace) ? MetadataTypeNames.GetName(t) : t.Namespace.String.Split('.')[0]));
			string stem = "__DnSpyEntryPoint", name = stem;
			for (int suffix = 1; used.Contains(name); suffix++) name = stem + suffix;
			return name;
		}
	}
}
