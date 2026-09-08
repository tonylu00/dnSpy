using System.Linq;
using dnlib.DotNet;

namespace dnSpy.Contracts.Decompiler {
	/// <summary>Attribute rules which must be restored after compiling metadata-valid usages.</summary>
	public static class MetadataAttributeUsages {
		/// <summary>Identifies an original AttributeUsage.ValidOn value.</summary>
		public const string Prefix = "dnSpy.metadata.attribute-usage.v1|";
		/// <summary>Gets a usage declaration supported by the restoration task.</summary>
		public static CustomAttribute? GetUsage(TypeDef type) => type.CustomAttributes.FirstOrDefault(a =>
			a.TypeFullName == "System.AttributeUsageAttribute" && a.ConstructorArguments.Count == 1 &&
			a.ConstructorArguments[0].Value is int);
	}
}
