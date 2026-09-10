using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Runtime.CompilerServices;
using dnlib.DotNet;

namespace dnSpy.Contracts.Decompiler {
	/// <summary>Stable C# field aliases and reversible runtime-name instructions.</summary>
	public static class MetadataFieldNames {
		/// <summary>Assembly instructions for restoring aliased fields.</summary>
		public const string Prefix = "dnSpy.metadata.field-name.v1|";
		/// <summary>Returns the source identifier from the resolved declaring module.</summary>
		public static string GetName(FieldDef field) => field.Module != null && names.GetValue(field.Module, Find).TryGetValue(field, out var alias) ? alias : field.Name.String;
		static readonly ConditionalWeakTable<ModuleDef, string[]> mappings = new ConditionalWeakTable<ModuleDef, string[]>();
		/// <summary>Instructions use resolved assembly context and source owner/alias pairs.</summary>
		public static string[] GetMappings(ModuleDef module) => mappings.GetValue(module, CreateMappings);
		static string[] CreateMappings(ModuleDef module) {
			var localTypes = module.GetTypes().ToArray();
			var usedFields = new HashSet<FieldDef>(localTypes.SelectMany(t => t.Fields));
			foreach (var reference in module.GetMemberRefs().Where(r => r.IsFieldRef)) {
				var field = reference.ResolveFieldDef();
				if (field != null) usedFields.Add(field);
			}
			var types = new HashSet<TypeDef>(localTypes);
			foreach (var reference in module.GetTypeRefs()) {
				var type = reference.ResolveTypeDef();
				if (type != null) types.Add(type);
			}
			foreach (var field in usedFields) types.Add(field.DeclaringType);
			var result = new HashSet<string>(StringComparer.Ordinal);
			Func<string, string> encode = value => Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes(value));
			foreach (var type in types.Where(t => t?.Module?.Assembly != null)) {
				var visited = new HashSet<TypeDef>();
				for (var owner = type; owner != null && visited.Add(owner); owner = owner.BaseType?.ResolveTypeDef()) {
					foreach (var field in owner.Fields.Where(usedFields.Contains)) {
						var alias = GetName(field);
						if (alias == field.Name.String) continue;
						// C# may encode a field reference through an inheriting receiver.
						// Record that source owner too, without changing the field's storage.
						var assembly = type.DefinitionAssembly;
						result.Add(Prefix + string.Join("|", new[] { MetadataTypeNames.SourceFullName(type), assembly.Name.String,
							assembly.Version.ToString(), assembly.Culture.String ?? "", alias }.Select(encode)) + "|" + Convert.ToBase64String(field.Name.Data));
					}
				}
			}
			return result.OrderBy(s => s, StringComparer.Ordinal).ToArray();
		}
		static readonly ConditionalWeakTable<ModuleDef, Dictionary<FieldDef, string>> names = new ConditionalWeakTable<ModuleDef, Dictionary<FieldDef, string>>();

		static Dictionary<FieldDef, string> Find(ModuleDef module) {
			var result = new Dictionary<FieldDef, string>();
			var allocated = new Dictionary<TypeDef, HashSet<string>>();
			var visiting = new HashSet<TypeDef>();
			HashSet<string> Allocate(TypeDef type) {
				if (allocated.TryGetValue(type, out var existing)) return existing;
				if (!visiting.Add(type)) return new HashSet<string>(StringComparer.Ordinal);
				var inheritedNames = new HashSet<string>(type.Methods.Select(m => m.Name.String)
					.Concat(type.Properties.Select(p => p.Name.String)).Concat(type.Events.Select(e => e.Name.String))
					.Concat(type.NestedTypes.Select(MetadataTypeNames.GetName)), StringComparer.Ordinal);
				var occupied = new HashSet<string>(inheritedNames, StringComparer.Ordinal);
				occupied.UnionWith(type.GenericParameters.Select(p => p.Name.String));
				occupied.Add(MetadataTypeNames.GetName(type));
				// A derived alias must not shadow inherited storage or callable
				// members. Otherwise a preserved IL base reference binds to the
				// derived field in C#, especially inside nested async helpers.
				var baseType = type.BaseType?.ResolveTypeDef();
				if (baseType != null) {
					var baseNames = Allocate(baseType);
					occupied.UnionWith(baseNames);
					inheritedNames.UnionWith(baseNames);
				}
				var used = new HashSet<string>(occupied.Concat(type.Fields.Select(f => f.Name.String)), StringComparer.Ordinal);
				foreach (var field in type.Fields.OrderBy(f => f.MDToken.Raw)) {
					var name = field.Name.String;
					bool legal = MetadataTypeNames.IsIdentifier(name);
					if (legal && occupied.Add(name)) { inheritedNames.Add(name); continue; }
					string root = legal ? name : "field_" + field.MDToken.Raw.ToString("X8", CultureInfo.InvariantCulture);
					string alias = root;
					int suffix = 0;
					while (!used.Add(alias)) alias = root + "_" + (++suffix).ToString(CultureInfo.InvariantCulture);
					occupied.Add(alias);
					inheritedNames.Add(alias);
					result.Add(field, alias);
				}
				visiting.Remove(type);
				return allocated[type] = inheritedNames;
			}
			foreach (var type in module.GetTypes()) Allocate(type);
			return result;
		}
	}
}
