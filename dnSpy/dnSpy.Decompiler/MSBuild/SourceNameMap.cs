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
using SourceNameMapping;

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
			var parameterProposals = new Dictionary<Parameter, string>();
			var contractProposals = new Dictionary<MethodDef, string>();
			foreach (var entry in root.Elements()) {
				if (entry.Name != "Module") throw new InvalidDataException("Unsupported source-map entry: " + entry.Name);
				var location = Path.GetFullPath(Path.Combine(directory, Required(entry, "Path")));
				if (!location.StartsWith(directory, StringComparison.OrdinalIgnoreCase) || !modules.TryGetValue(location, out var module)) throw new InvalidDataException("Mapped module is not an exact export input: " + location);
				if (module.Mvid != Guid.Parse(Required(entry, "Mvid"))) throw new InvalidDataException("Source map MVID mismatch: " + location);
				using (var stream = File.OpenRead(location)) using (var hash = SHA256.Create())
					if (!string.Equals(BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", ""), Required(entry, "Sha256"), StringComparison.OrdinalIgnoreCase))
						throw new InvalidDataException("Source map input hash mismatch: " + location);
				foreach (var row in entry.Elements()) {
					if ((row.Name != "Type" && row.Name != "Method" && row.Name != "Field") || row.Name != "Method" && row.HasElements) throw new InvalidDataException("Source maps accept types, ordinary fields and methods with parameter aliases.");
					string tokenText = Required(row, "Token");
					if (!tokenText.StartsWith("0x", StringComparison.Ordinal)) throw new InvalidDataException("Expected hexadecimal metadata token.");
					var member = module.ResolveToken(uint.Parse(tokenText.Substring(2), NumberStyles.HexNumber, CultureInfo.InvariantCulture)) as IMemberDef;
					if (member == null || (row.Name == "Type" ? !(member is TypeDef) : row.Name == "Field" ? !(member is FieldDef) : !(member is MethodDef)) || member.Name != Required(row, "ExpectedName") || member.FullName != Required(row, "Signature")) throw new InvalidDataException("Source map token/name/signature mismatch.");
					string? name = (string?)row.Attribute("NewName");
					if (name != null) ValidateName(name);
					else if (!row.HasElements) throw new InvalidDataException("A source-map row must propose a name or parameters.");
					if (member is TypeDef type && (type.IsGlobalModuleType || type.HasGenericParameters)) throw new InvalidDataException("This source-map version requires a non-generic type.");
					if (member is FieldDef field && FieldAliasScope.Blocker(field) != null) throw new InvalidDataException("Unsupported source field alias: " + FieldAliasScope.Blocker(field));
					string? contract = (string?)row.Attribute("ContractFamily");
					if (member is MethodDef method) {
						if (MethodContractFamilies.MethodBlocker(method) != null || contract == null && method.IsVirtual) throw new InvalidDataException("Source method alias requires an ordinary method or a supported complete contract family.");
						if (contract != null) contractProposals.Add(method, contract);
					}
					else if (contract != null) throw new InvalidDataException("ContractFamily requires a method row.");
					if (name != null) proposals.Add(member, name);
					foreach (var parameterRow in row.Elements()) {
						if (parameterRow.Name != "Parameter" || parameterRow.HasElements || !(member is MethodDef owner)) throw new InvalidDataException("Expected a parameter alias.");
						int sequence = int.Parse(Required(parameterRow, "Sequence"), CultureInfo.InvariantCulture);
						var parameter = owner.Parameters.SingleOrDefault(p => !p.IsHiddenThisParameter && p.MethodSigIndex + 1 == sequence);
						if (sequence <= 0 || parameter?.ParamDef == null || parameter.Name != Required(parameterRow, "ExpectedName")) throw new InvalidDataException("Source parameter sequence/name mismatch or absent metadata row.");
						string alias = Required(parameterRow, "NewName"); ValidateName(alias);
						parameterProposals.Add(parameter, alias);
					}
				}
			}
			if (contractProposals.Count != 0) {
				var graph = new MethodContractFamilies(modules.Values, module => {
					var location = Path.GetFullPath(module.Location);
					return (location.StartsWith(directory, StringComparison.OrdinalIgnoreCase) ? location.Substring(directory.Length) : location).Replace('\\', '/');
				}, useHostResolver: true);
				foreach (var proposal in contractProposals) {
					var family = graph.Get(proposal.Key);
					if (family == null || family.Id != proposal.Value || family.Blockers.Length != 0)
						throw new InvalidDataException("Stale or unsupported source contract family: " + proposal.Key.FullName);
					if (family.Methods.Any(m => !contractProposals.TryGetValue(m, out var id) || id != family.Id || !proposals.ContainsKey(m)) ||
						family.Methods.Select(m => proposals[m]).Distinct(StringComparer.Ordinal).Count() != 1)
						throw new InvalidDataException("Source contract family must be mapped completely with one name: " + proposal.Key.FullName);
				}
			}
			foreach (var group in parameterProposals.GroupBy(p => p.Key.Method)) {
				var used = new HashSet<string>(group.Key.Parameters.Select(p => p.Name), StringComparer.Ordinal);
				used.UnionWith(group.Key.GenericParameters.Select(p => p.Name.String));
				for (var type = group.Key.DeclaringType; type != null; type = type.DeclaringType)
					used.UnionWith(type.GenericParameters.Select(p => p.Name.String));
				foreach (var proposal in group) if (!used.Add(proposal.Value)) throw new InvalidDataException("Source parameter alias collision: " + proposal.Value);
			}
			// Reserve aliases across each module to avoid ambiguous restore instructions
			// and collisions with unmodified declarations, including nested members.
			foreach (var group in proposals.Where(p => !(p.Key is FieldDef)).GroupBy(p => p.Key is TypeDef t ? t.Module : p.Key.DeclaringType.Module)) {
				var used = new HashSet<string>(StringComparer.Ordinal);
				var shared = new Dictionary<string, string>(StringComparer.Ordinal);
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
				foreach (var proposal in group) {
					string? family = proposal.Key is MethodDef method && contractProposals.TryGetValue(method, out var id) ? id : null;
					if (!used.Add(proposal.Value) && (family == null || !shared.TryGetValue(proposal.Value, out var previous) || previous != family))
						throw new InvalidDataException("Source alias collision: " + proposal.Value);
					if (family != null) shared[proposal.Value] = family;
				}
				if (parameterProposals.Any(p => p.Key.Method.Module == group.Key && group.Any(m => m.Value == p.Value))) throw new InvalidDataException("Source parameter alias collides with a mapped member.");
			}
			if (proposals.Keys.Any(m => m is FieldDef)) {
				var scope = new FieldAliasScope(modules.Values, useHostResolver: true);
				foreach (var proposal in proposals.Where(p => p.Key is FieldDef))
					if (scope.Reserved((FieldDef)proposal.Key, member => proposals.TryGetValue(member, out var alias) ? alias : null).Contains(proposal.Value))
						throw new InvalidDataException("Source field alias collision in declaration/inheritance scope: " + proposal.Key.FullName + " -> " + proposal.Value);
			}
			foreach (var proposal in proposals) SourceNameAliases.Register(proposal.Key, proposal.Value);
			foreach (var proposal in parameterProposals) SourceNameAliases.RegisterParameter(proposal.Key, proposal.Value);
			return root.ToString(SaveOptions.DisableFormatting);
		}
		static void ValidateName(string name) {
			if (!MetadataTypeNames.IsIdentifier(name) || name.Any(c => char.GetUnicodeCategory(c) == UnicodeCategory.Format)) throw new InvalidDataException("Invalid source alias: " + name);
		}
		static string Required(XElement element, string name) => (string?)element.Attribute(name) ?? throw new InvalidDataException("Missing source-map attribute: " + name);
	}
}
