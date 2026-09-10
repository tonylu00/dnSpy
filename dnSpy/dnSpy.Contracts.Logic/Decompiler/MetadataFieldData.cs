using System;
using System.IO;
using dnlib.DotNet;

namespace dnSpy.Contracts.Decompiler {
	/// <summary>Data attached to retained fields which C# cannot declare exactly.</summary>
	public static class MetadataFieldData {
		/// <summary>Reversible field data instruction.</summary>
		public const string Prefix = "dnSpy.metadata.field-data.v1|";
		/// <summary>Whether the declaration needs post-compilation metadata restoration.</summary>
		public static bool Required(FieldDef field) => field.HasFieldRVA || field.IsCompilerControlled || field.Constant != null && !field.IsLiteral;
		/// <summary>Preserves binary constants, including floating-point bit patterns and UTF-16 code units.</summary>
		public static string Encode(FieldDef field) {
			string constant = "N";
			if (field.Constant?.Value != null) {
				using (var stream = new MemoryStream()) {
					using (var writer = new BinaryWriter(stream)) {
						object value = field.Constant.Value;
						switch (field.Constant.Type) {
						case ElementType.Boolean: writer.Write((bool)value); break;
						case ElementType.Char: writer.Write((ushort)(char)value); break;
						case ElementType.I1: writer.Write((sbyte)value); break;
						case ElementType.U1: writer.Write((byte)value); break;
						case ElementType.I2: writer.Write((short)value); break;
						case ElementType.U2: writer.Write((ushort)value); break;
						case ElementType.I4: writer.Write((int)value); break;
						case ElementType.U4: writer.Write((uint)value); break;
						case ElementType.I8: writer.Write((long)value); break;
						case ElementType.U8: writer.Write((ulong)value); break;
						case ElementType.R4: writer.Write((float)value); break;
						case ElementType.R8: writer.Write((double)value); break;
						case ElementType.String: foreach (char c in (string)value) writer.Write((ushort)c); break;
						default: throw new InvalidDataException("Unsupported field constant kind: " + field.Constant.Type);
						}
						writer.Flush(); constant = "V" + Convert.ToBase64String(stream.ToArray());
					}
				}
			}
			return Prefix + Convert.ToBase64String(field.Name.Data) + "|" + ((uint)field.Attributes).ToString(System.Globalization.CultureInfo.InvariantCulture) + "|" +
				(field.Constant == null ? "none" : ((int)field.Constant.Type).ToString(System.Globalization.CultureInfo.InvariantCulture)) + "|" + constant + "|" +
				(field.HasFieldRVA ? Convert.ToBase64String(field.InitialValue ?? throw new InvalidDataException("Missing field RVA data.")) : "none");
		}
	}
}
