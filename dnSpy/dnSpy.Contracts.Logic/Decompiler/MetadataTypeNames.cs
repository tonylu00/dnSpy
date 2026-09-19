using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text;
using dnlib.DotNet;

namespace dnSpy.Contracts.Decompiler {
	/// <summary>Projects metadata type names into C# without changing method contracts.</summary>
	public static class MetadataTypeNames {
		/// <summary>Assembly-level instructions for restoring source aliases after compilation.</summary>
		public const string Prefix = "dnSpy.metadata.type-name.v1|";
		/// <summary>Version 2 additionally restores the original namespace.</summary>
		public const string PrefixV2 = "dnSpy.metadata.type-name.v2|";
		static readonly ConditionalWeakTable<ModuleDef, Dictionary<TypeDef, string>> names = new ConditionalWeakTable<ModuleDef, Dictionary<TypeDef, string>>();
		static readonly ConditionalWeakTable<ModuleDef, string[]> mappings = new ConditionalWeakTable<ModuleDef, string[]>();
		/// <summary>Removes the generic arity suffix used in metadata.</summary>
		public static string SimpleName(string name) {
			int index = name.LastIndexOf('`');
			return index >= 0 && index + 1 < name.Length && name.Skip(index + 1).All(char.IsDigit) ? name.Substring(0, index) : name;
		}
		/// <summary>Returns a stable identifier for declarations and references, including external references.</summary>
		public static string GetName(ITypeDefOrRef type) {
			var definition = type.ResolveTypeDef();
			var requested = SourceNameAliases.Get(definition);
			if (requested != null) return Leaf(requested);
			return definition?.Module != null && names.GetValue(definition.Module, Find).TryGetValue(definition, out var alias)
				? alias : SimpleName(type.Name);
		}
		/// <summary>The identifier part of an alias; a type alias may carry a namespace.</summary>
		static string Leaf(string name) {
			int index = name.LastIndexOf('.');
			return index < 0 ? name : name.Substring(index + 1);
		}
		/// <summary>Whether a string can be emitted as a C# identifier (keywords can be escaped).</summary>
		public static bool IsIdentifier(string name) {
			if (string.IsNullOrEmpty(name)) return false;
			for (int i = 0; i < name.Length; i++) {
				var category = char.GetUnicodeCategory(name[i]);
				if (name[i] == '_' || char.IsLetter(name[i]) || category == UnicodeCategory.LetterNumber) continue;
				if (i != 0 && (category == UnicodeCategory.DecimalDigitNumber || category == UnicodeCategory.ConnectorPunctuation || category == UnicodeCategory.NonSpacingMark || category == UnicodeCategory.SpacingCombiningMark || category == UnicodeCategory.Format)) continue;
				return false;
			}
			return true;
		}
		static IEnumerable<string> MemberNames(TypeDef type) => type.Methods.Where(m => !m.IsConstructor).Select(m => m.Name.String)
			.Concat(type.Properties.Select(p => p.Name.String)).Concat(type.Events.Select(e => e.Name.String));
		static Dictionary<TypeDef, string> Find(ModuleDef module) {
			var types = module.GetTypes().ToArray();
			var used = new HashSet<string>(StringComparer.Ordinal);
			foreach (var type in types) {
				used.Add(SimpleName(type.Name));
				var requested = SourceNameAliases.Get(type);
				if (requested != null) used.Add(requested);
				used.UnionWith((type.Namespace.String ?? "").Split('.'));
				used.UnionWith(MemberNames(type));
				used.UnionWith(type.Fields.Select(f => f.Name.String));
				used.UnionWith(type.GenericParameters.Select(p => p.Name.String));
				foreach (var method in type.Methods) {
					used.UnionWith(method.GenericParameters.Select(p => p.Name.String));
					used.UnionWith(method.Parameters.Select(p => p.Name));
				}
			}
			var result = new Dictionary<TypeDef, string>();
			foreach (var type in types.OrderBy(t => t.MDToken.Raw)) {
				if (type.IsGlobalModuleType && !type.HasMethods && !type.HasFields) continue;
				string name = SimpleName(type.Name);
				// A method may legally have its owner's name in IL, or share a name
				// with a nested type. Keep overload/virtual families intact; alias the type.
				bool collision = MemberNames(type).Contains(name) || type.DeclaringType != null &&
					(MemberNames(type.DeclaringType).Contains(name) || SimpleName(type.DeclaringType.Name) == name);
				if (IsIdentifier(name) && !collision) continue;
				string stem = "Type_" + type.MDToken.Rid.ToString(CultureInfo.InvariantCulture), alias = stem;
				for (int suffix = 1; !used.Add(alias); suffix++) alias = stem + "_" + suffix.ToString(CultureInfo.InvariantCulture);
				result.Add(type, alias);
			}
			return result;
		}
		/// <summary>Full nested source name, including projected aliases and generic arity.</summary>
		public static string SourceFullName(TypeDef type) {
			var name = SourceMetadataName(type);
			return type.DeclaringType != null ? SourceFullName(type.DeclaringType) + "/" + name :
				string.IsNullOrEmpty(type.Namespace) ? name : type.Namespace + "." + name;
		}
		/// <summary>The metadata full name a type had before an alias moved it.</summary>
		public static string OriginalFullName(TypeDef type) {
			string @namespace = SourceNameAliases.GetOriginalNamespace(type);
			string name = SourceNameAliases.GetOriginalName(type) ?? type.Name.String;
			return string.IsNullOrEmpty(@namespace) ? name : @namespace + "." + name;
		}
		static string SourceMetadataName(TypeDef type) {
			int arity = Math.Max(0, type.GenericParameters.Count - (type.DeclaringType?.GenericParameters.Count ?? 0));
			return GetName(type) + (arity == 0 ? "" : "`" + arity.ToString(CultureInfo.InvariantCulture));
		}
		static string Encode(string text) => Convert.ToBase64String(Encoding.UTF8.GetBytes(text));
		/// <summary>Maps local definitions and external references using the resolved input context.</summary>
		public static string[] GetMappings(ModuleDef module) => mappings.GetValue(module, CreateMappings);
		static string[] CreateMappings(ModuleDef module) {
			var types = new HashSet<TypeDef>(module.GetTypes());
			foreach (var reference in module.GetTypeRefs()) {
				for (var type = reference.ResolveTypeDef(); type != null; type = type.DeclaringType) types.Add(type);
			}
			var rows = new List<string>();
			foreach (var type in types) {
				if (type.IsGlobalModuleType || type.Module?.Assembly == null) continue;
				string source = SourceFullName(type);
				string originalNamespace = SourceNameAliases.GetOriginalNamespace(type);
				string originalName = SourceNameAliases.GetOriginalName(type) ?? type.Name.String;
				bool moved = originalNamespace != null && originalNamespace != (type.Namespace.String ?? string.Empty);
				if (!moved && SourceMetadataName(type) == originalName) continue;
				if (moved) {
					rows.Add(PrefixV2 + Encode(source) + "|" + Encode(type.DefinitionAssembly.Name) + "|" +
						Encode(type.DefinitionAssembly.Version.ToString()) + "|" + Encode(type.DefinitionAssembly.Culture ?? "") + "|" +
						Encode(originalNamespace) + "|" + Encode(originalName));
					continue;
				}
				rows.Add(Prefix + Encode(source) + "|" + Encode(type.DefinitionAssembly.Name) + "|" +
					Encode(type.DefinitionAssembly.Version.ToString()) + "|" + Encode(type.DefinitionAssembly.Culture ?? "") + "|" +
					Encode(originalName));
			}
			return rows.Distinct().OrderBy(s => s, StringComparer.Ordinal).ToArray();
		}
	}
}
