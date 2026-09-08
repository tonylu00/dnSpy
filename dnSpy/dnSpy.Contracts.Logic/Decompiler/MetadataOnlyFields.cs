using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using dnlib.DotNet;

namespace dnSpy.Contracts.Decompiler {
	/// <summary>Fields which need metadata emission rather than a C# declaration.</summary>
	public static class MetadataOnlyFields {
		/// <summary>Identifies field restoration instructions in exported source.</summary>
		public const string Prefix = "dnSpy.metadata.string-field.v1|";
		static readonly ConditionalWeakTable<ModuleDef, HashSet<FieldDef>> cache = new ConditionalWeakTable<ModuleDef, HashSet<FieldDef>>();
		/// <summary>Whether the field can be restored without replacing direct field accesses.</summary>
		public static bool Contains(FieldDef field) => field.Module != null && cache.GetValue(field.Module, Find).Contains(field);
		static HashSet<FieldDef> Find(ModuleDef module) {
			var fields = new HashSet<FieldDef>(module.GetTypes().Where(t => t.IsAbstract && t.IsSealed || t.BaseType?.FullName == "System.MulticastDelegate")
				.SelectMany(t => t.Fields).Where(f => !f.IsStatic && (f.IsPrivate || f.IsCompilerControlled) &&
					f.FieldSig?.Type?.ElementType == ElementType.String && !f.HasCustomAttributes && !f.HasMarshalType && !f.HasFieldRVA && f.FieldOffset == null &&
					(f.Constant == null || f.Constant.Type == ElementType.I1 && f.Constant.Value is sbyte || f.Constant.Type == ElementType.String || f.Constant.Type == ElementType.Class && f.Constant.Value == null)));
			if (fields.Count == 0) return fields;
			foreach (var type in module.GetTypes()) foreach (var method in type.Methods) {
				if (!method.HasBody) continue;
				foreach (var instruction in method.Body.Instructions)
					if (instruction.Operand is IField reference) fields.Remove(reference.ResolveFieldDef());
			}
			foreach (var reference in module.GetMemberRefs())
				if (reference.IsFieldRef) fields.Remove(reference.ResolveFieldDef());
			return fields;
		}
		/// <summary>Encodes the exact field name, flags and constant.</summary>
		public static string Encode(FieldDef field) {
			string constant = field.Constant == null ? "none" : ((int)field.Constant.Type).ToString(System.Globalization.CultureInfo.InvariantCulture);
			string value = Convert.ToString(field.Constant?.Value, System.Globalization.CultureInfo.InvariantCulture) ?? "";
			return Prefix + Convert.ToBase64String(field.Name.Data) + "|" +
				((int)field.Attributes).ToString(System.Globalization.CultureInfo.InvariantCulture) + "|" + constant + "|" +
				(field.Constant?.Value == null ? "N" : "V" + Convert.ToBase64String(value.SelectMany(c => new[] { (byte)c, (byte)(c >> 8) }).ToArray()));
		}
	}
}
