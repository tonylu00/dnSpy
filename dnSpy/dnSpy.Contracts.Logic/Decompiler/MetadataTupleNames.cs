using System;
using System.Collections.Generic;
using System.Linq;
using dnlib.DotNet;
namespace dnSpy.Contracts.Decompiler {
	/// <summary>Tuple annotations which the legacy C# AST cannot express as named tuple syntax.</summary>
	public static class MetadataTupleNames {
		public const string Prefix = "dnSpy.metadata.tuple-names.v1|";
		public const string AttributeName = "System.Runtime.CompilerServices.TupleElementNamesAttribute";
		public static IEnumerable<string> Encode(IHasCustomAttribute provider, string target) {
			if (provider == null) yield break;
			foreach (var attribute in provider.CustomAttributes.Where(a => a.TypeFullName == AttributeName)) {
				if (attribute.ConstructorArguments.Count != 1 || !(attribute.ConstructorArguments[0].Value is IList<CAArgument> names))
					throw new InvalidOperationException("Invalid tuple element-name annotation.");
				var values = names.Select(a => a.Value == null ? "N" : "V" + Convert.ToBase64String(a.Value.ToString().SelectMany(c => new[] { (byte)c, (byte)(c >> 8) }).ToArray()));
				var assembly = attribute.AttributeType.DefinitionAssembly;
				yield return Prefix + target + "|" + Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes(assembly.FullName)) + "|" + string.Join(",", values);
			}
		}
	}
}
