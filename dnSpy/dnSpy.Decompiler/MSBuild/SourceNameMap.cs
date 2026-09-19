using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Xml;
using System.Xml.Linq;
using dnlib.DotNet;
using dnlib.DotNet.Emit;
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
			var localProposals = new Dictionary<Local, string>();
			var localOwners = new Dictionary<Local, MethodDef>();
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
					if ((row.Name != "Type" && row.Name != "Method" && row.Name != "Field") || row.Name != "Method" && row.HasElements) throw new InvalidDataException("Source maps accept types, ordinary fields and methods with parameter or local aliases.");
					var member = ResolveRow(module, row);
					string? name = (string?)row.Attribute("NewName");
					if (name != null) {
						// A type alias may carry the namespace the obfuscator flattened
						// away; everything else stays a single identifier.
						if (member is TypeDef) ValidateTypeName(name);
						else ValidateName(name);
					}
					else if (!row.HasElements) throw new InvalidDataException("A source-map row must propose a name, parameters or locals.");
					if (member is TypeDef type && (type.IsGlobalModuleType || type.HasGenericParameters)) throw new InvalidDataException("This source-map version requires a non-generic type.");
					if (member is FieldDef field && FieldAliasScope.Blocker(field) != null) throw new InvalidDataException("Unsupported source field alias: " + FieldAliasScope.Blocker(field));
					string? contract = (string?)row.Attribute("ContractFamily");
					if (member is MethodDef method) {
						if (MethodContractFamilies.MethodBlocker(method) != null || contract == null && method.IsVirtual) throw new InvalidDataException("Source method alias requires an ordinary method or a supported complete contract family.");
						if (contract != null) contractProposals.Add(method, contract);
					}
					else if (contract != null) throw new InvalidDataException("ContractFamily requires a method row.");
					if (name != null) proposals.Add(member, name);
					foreach (var aliasRow in row.Elements()) {
						if (aliasRow.HasElements || !(member is MethodDef owner)) throw new InvalidDataException("Expected a parameter or local alias.");
						if (aliasRow.Name == "Parameter") {
							int sequence = int.Parse(Required(aliasRow, "Sequence"), CultureInfo.InvariantCulture);
							var parameter = owner.Parameters.SingleOrDefault(p => !p.IsHiddenThisParameter && p.MethodSigIndex + 1 == sequence);
							if (sequence <= 0 || parameter?.ParamDef == null || parameter.Name != Required(aliasRow, "ExpectedName")) throw new InvalidDataException("Source parameter sequence/name mismatch or absent metadata row.");
							string alias = Required(aliasRow, "NewName"); ValidateName(alias);
							parameterProposals.Add(parameter, alias);
						}
						else if (aliasRow.Name == "Local") {
							var body = owner.Body;
							int index = int.Parse(Required(aliasRow, "Index"), CultureInfo.InvariantCulture);
							if (body == null || index < 0 || index >= body.Variables.Count || body.Variables[index].Type?.FullName != Required(aliasRow, "ExpectedType")) throw new InvalidDataException("Source local index/type mismatch.");
							string alias = Required(aliasRow, "NewName"); ValidateName(alias);
							localProposals.Add(body.Variables[index], alias);
							localOwners[body.Variables[index]] = owner;
						}
						else throw new InvalidDataException("Expected a parameter or local alias.");
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
			foreach (var group in localProposals.GroupBy(p => localOwners[p.Key])) {
				var used = new HashSet<string>(group.Key.Parameters.Where(p => !p.IsHiddenThisParameter).Select(p => p.Name), StringComparer.Ordinal);
				used.UnionWith(group.Key.GenericParameters.Select(p => p.Name.String));
				for (var type = group.Key.DeclaringType; type != null; type = type.DeclaringType)
					used.UnionWith(type.GenericParameters.Select(p => p.Name.String));
				foreach (var proposal in parameterProposals) if (proposal.Key.Method == group.Key) used.Add(proposal.Value);
				foreach (var proposal in group) if (!used.Add(proposal.Value)) throw new InvalidDataException("Source local alias collision: " + proposal.Value);
			}
			// C# scopes member names by declaring type, not by module, and every
			// rebuild instruction is qualified by its source owner. Reserve
			// aliases in their declaration scope, keeping original names reserved
			// because swaps can make restore ordering ambiguous.
			if (proposals.Any(p => !(p.Key is FieldDef))) {
				var scope = new MemberNameScope(modules.Values, useHostResolver: true);
				var claims = new MemberNameClaims(scope);
				var fullAliases = new HashSet<string>(StringComparer.Ordinal);
				foreach (var proposal in proposals.Where(p => !(p.Key is FieldDef))) {
					string? family = proposal.Key is MethodDef method && contractProposals.TryGetValue(method, out var id) ? id : null;
					// A dotted type alias moves the type into another namespace: the
					// declaration scope reserves its leaf, the full alias stays unique.
					string scopeName = proposal.Key is TypeDef ? Leaf(proposal.Value) : proposal.Value;
					bool duplicate = proposal.Key is TypeDef && !fullAliases.Add(proposal.Value);
					if (duplicate || claims.Conflicts(proposal.Key, scopeName, family))
						throw new InvalidDataException("Source alias collision: " + proposal.Key.FullName + " -> " + proposal.Value);
					// The registry carries the full type alias so the source
					// namespace of a claimed type stays known; the scope check
					// itself compares leaves.
					claims.Claim(proposal.Key, proposal.Key is TypeDef ? proposal.Value : scopeName, family);
				}
				var parameters = new Dictionary<TypeDef, HashSet<string>>();
				foreach (var proposal in parameterProposals) {
					var owner = proposal.Key.Method.DeclaringType;
					if (owner == null) continue;
					if (!parameters.TryGetValue(owner, out var names)) parameters.Add(owner, names = new HashSet<string>(StringComparer.Ordinal));
					names.Add(proposal.Value);
				}
				// A source parameter name only shadows members visible from the
				// body that declares it, so the reservation stays in its type scope.
				foreach (var proposal in proposals.Where(p => !(p.Key is FieldDef) && p.Key.DeclaringType != null)) {
					foreach (var type in scope.Types(proposal.Key.DeclaringType))
						if (parameters.TryGetValue(type, out var names) && names.Contains(proposal.Value))
							throw new InvalidDataException("Source parameter alias collides with a mapped member: " + proposal.Key.FullName + " -> " + proposal.Value);
				}
			}
			if (proposals.Keys.Any(m => m is FieldDef)) {
				var scope = new FieldAliasScope(modules.Values, useHostResolver: true);
				foreach (var proposal in proposals.Where(p => p.Key is FieldDef))
					if (scope.Reserved((FieldDef)proposal.Key, member => proposals.TryGetValue(member, out var alias) ? alias : null).Contains(proposal.Value))
						throw new InvalidDataException("Source field alias collision in declaration/inheritance scope: " + proposal.Key.FullName + " -> " + proposal.Value);
			}
			foreach (var proposal in proposals) {
				if (proposal.Key is TypeDef type) SourceNameAliases.RegisterTypeName(type, proposal.Value);
				else SourceNameAliases.Register(proposal.Key, proposal.Value);
			}
			foreach (var proposal in parameterProposals) SourceNameAliases.RegisterParameter(proposal.Key, proposal.Value);
			foreach (var proposal in localProposals) SourceNameAliases.RegisterLocal(proposal.Key, proposal.Value);
			return root.ToString(SaveOptions.DisableFormatting);
		}

		// A row may name its member by metadata token or by signature. Name-only rows
		// let a mapping be authored without tokens as long as the signature identifies
		// exactly one member in the module.
		static IMemberDef ResolveRow(ModuleDef module, XElement row) {
			string? tokenText = (string?)row.Attribute("Token");
			if (tokenText != null) {
				if (!tokenText.StartsWith("0x", StringComparison.Ordinal)) throw new InvalidDataException("Expected hexadecimal metadata token.");
				var member = module.ResolveToken(uint.Parse(tokenText.Substring(2), NumberStyles.HexNumber, CultureInfo.InvariantCulture)) as IMemberDef;
				if (member == null || (row.Name == "Type" ? !(member is TypeDef) : row.Name == "Field" ? !(member is FieldDef) : !(member is MethodDef)) || member.Name != Required(row, "ExpectedName") || member.FullName != Required(row, "Signature")) throw new InvalidDataException("Source map token/name/signature mismatch.");
				return member;
			}
			string expected = Required(row, "ExpectedName");
			string signature = Required(row, "Signature");
			var matches = module.GetTypes().SelectMany(type => row.Name == "Type" ? new IMemberDef[] { type } :
				row.Name == "Field" ? type.Fields.Cast<IMemberDef>() : type.Methods.Cast<IMemberDef>())
				.Where(m => m.Name == expected && m.FullName == signature).ToArray();
			if (matches.Length != 1) throw new InvalidDataException("Source map name-only row must identify exactly one member: " + signature + " (" + matches.Length + " matches)");
			return matches[0];
		}
		static void ValidateName(string name) {
			if (!MetadataTypeNames.IsIdentifier(name) || name.Any(c => char.GetUnicodeCategory(c) == UnicodeCategory.Format)) throw new InvalidDataException("Invalid source alias: " + name);
		}
		static void ValidateTypeName(string name) {
			if (name.Split('.').Any(part => !MetadataTypeNames.IsIdentifier(part)) || name.Any(c => char.GetUnicodeCategory(c) == UnicodeCategory.Format))
				throw new InvalidDataException("Invalid source type alias: " + name);
		}
		static string Leaf(string name) {
			int index = name.LastIndexOf('.');
			return index < 0 ? name : name.Substring(index + 1);
		}
		static string Required(XElement element, string name) => (string?)element.Attribute(name) ?? throw new InvalidDataException("Missing source-map attribute: " + name);
	}
}
