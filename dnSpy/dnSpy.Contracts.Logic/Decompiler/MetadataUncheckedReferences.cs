using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Runtime.CompilerServices;
using dnlib.DotNet;

namespace dnSpy.Contracts.Decompiler {
	/// <summary>Source placeholders for reference transfers not expressible in C#.</summary>
	public static class MetadataUncheckedReferences {
		/// <summary>Identifies the generated placeholder type for the build task.</summary>
		public const string Feature = "dnSpy.metadata.unchecked-references.v1";
		static readonly ConditionalWeakTable<ModuleDef, string> names = new ConditionalWeakTable<ModuleDef, string>();
		/// <summary>Requests a collision-free placeholder name for a module.</summary>
		public static string Request(ModuleDef module) => names.GetValue(module, m => {
			var used = new HashSet<string>(m.Types.Select(t => string.IsNullOrEmpty(t.Namespace)
				? MetadataTypeNames.GetName(t).Split('`')[0] : t.Namespace.String.Split('.')[0]));
			used.UnionWith(m.GetTypeRefs().Select(t => string.IsNullOrEmpty(t.Namespace) ? t.Name.String.Split('`')[0] : t.Namespace.String.Split('.')[0]));
			string root = "__DnSpyUncheckedReference", name = root;
			for (int suffix = 1; used.Contains(name); suffix++) name = root + suffix.ToString(CultureInfo.InvariantCulture);
			return name;
		});
		/// <summary>Returns a requested placeholder name, or null if none was used.</summary>
		public static string? GetRequestedName(ModuleDef module) => names.TryGetValue(module, out var name) ? name : null;
	}
}

