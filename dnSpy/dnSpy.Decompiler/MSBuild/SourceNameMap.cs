using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Xml;
using System.Xml.Linq;
using dnlib.DotNet;
using dnSpy.Contracts.Decompiler;

namespace dnSpy.Decompiler.MSBuild {
	static class SourceNameMap {
		public static string Apply(string path, IEnumerable<ModuleDef> inputs) {
			var settings = new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null };
			using var reader = XmlReader.Create(path, settings);
			var root = XDocument.Load(reader).Root;
			if (root?.Name != "SourceNameMap" || (string?)root.Attribute("Version") != "1") throw new InvalidDataException("Expected SourceNameMap Version=1.");
			var directory = Path.GetFullPath(Required(root, "InputDirectory")).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
			var modules = inputs.ToDictionary(m => Path.GetFullPath(m.Location), StringComparer.OrdinalIgnoreCase);
			var proposals = new Dictionary<IMemberDef, string>();
			foreach (var entry in root.Elements()) {
				if (entry.Name != "Module") throw new InvalidDataException("Unsupported source-map entry: " + entry.Name);
				var location = Path.GetFullPath(Path.Combine(directory, Required(entry, "Path")));
				if (!location.StartsWith(directory, StringComparison.OrdinalIgnoreCase) || !modules.TryGetValue(location, out var module)) throw new InvalidDataException("Mapped module is not an exact export input: " + location);
				if (module.Mvid != Guid.Parse(Required(entry, "Mvid"))) throw new InvalidDataException("Source map MVID mismatch: " + location);
				using (var stream = File.OpenRead(location)) using (var hash = SHA256.Create())
					if (!string.Equals(BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", ""), Required(entry, "Sha256"), StringComparison.OrdinalIgnoreCase))
						throw new InvalidDataException("Source map input hash mismatch: " + location);
				foreach (var row in entry.Elements()) {
					if (row.HasElements || (row.Name != "Type" && row.Name != "Method")) throw new InvalidDataException("Source maps currently accept type and nonvirtual method aliases only.");
					string tokenText = Required(row, "Token");
					if (!tokenText.StartsWith("0x", StringComparison.Ordinal)) throw new InvalidDataException("Expected hexadecimal metadata token.");
					var member = module.ResolveToken(uint.Parse(tokenText.Substring(2), NumberStyles.HexNumber, CultureInfo.InvariantCulture)) as IMemberDef;
					if (member == null || (row.Name == "Type" ? !(member is TypeDef) : !(member is MethodDef)) || member.Name != Required(row, "ExpectedName") || member.FullName != Required(row, "Signature")) throw new InvalidDataException("Source map token/name/signature mismatch.");
					string name = Required(row, "NewName");
					if (!MetadataTypeNames.IsIdentifier(name) || name.Any(c => char.GetUnicodeCategory(c) == UnicodeCategory.Format)) throw new InvalidDataException("Invalid source alias: " + name);
					if (member is TypeDef type && (type.IsGlobalModuleType || type.HasGenericParameters)) throw new InvalidDataException("This source-map version requires a non-generic type.");
					if (member is MethodDef method && (method.IsConstructor || method.IsVirtual || method.HasOverrides || method.IsRuntimeSpecialName || method.IsSpecialName || method.IsPinvokeImpl || method.IsRuntime)) throw new InvalidDataException("Source method alias requires an ordinary nonvirtual method.");
					proposals.Add(member, name);
				}
			}
			// Reserve aliases across each module to avoid ambiguous restore instructions
			// and collisions with unmodified declarations, including nested members.
			foreach (var group in proposals.GroupBy(p => p.Key is TypeDef t ? t.Module : p.Key.DeclaringType.Module)) {
				var used = new HashSet<string>(StringComparer.Ordinal);
				foreach (var type in group.Key.GetTypes()) {
					used.UnionWith((type.Namespace.String ?? "").Split('.'));
					used.UnionWith(type.GenericParameters.Select(p => p.Name.String));
					used.UnionWith(type.Methods.SelectMany(m => m.GenericParameters).Select(p => p.Name.String));
					used.UnionWith(type.Methods.SelectMany(m => m.Parameters).Select(p => p.Name));
					// Reserve original names too: swaps can make restore ordering ambiguous.
					used.Add(MetadataTypeNames.SimpleName(type.Name));
					foreach (var method in type.Methods) used.Add(method.Name);
					used.UnionWith(type.Fields.Select(f => f.Name.String));
					used.UnionWith(type.Properties.Select(p => p.Name.String));
					used.UnionWith(type.Events.Select(e => e.Name.String));
				}
				foreach (var proposal in group) if (!used.Add(proposal.Value)) throw new InvalidDataException("Source alias collision: " + proposal.Value);
			}
			foreach (var proposal in proposals) SourceNameAliases.Register(proposal.Key, proposal.Value);
			return root.ToString(SaveOptions.DisableFormatting);
		}
		static string Required(XElement element, string name) => (string?)element.Attribute(name) ?? throw new InvalidDataException("Missing source-map attribute: " + name);
	}
}
