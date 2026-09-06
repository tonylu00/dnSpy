using System;
using System.Collections.Generic;
using System.Xml;
using dnlib.DotNet;

namespace dnSpy_Console {
	// A DLL can reference an older contract while the host application selects a
	// newer implementation. Apply only the explicitly supplied host's redirects.
	sealed class ApplicationConfigResolver : IAssemblyResolver {
		readonly IAssemblyResolver resolver;
		readonly List<Redirect> redirects = new List<Redirect>();
		public ApplicationConfigResolver(IAssemblyResolver resolver, string path) {
			this.resolver = resolver;
			var document = new XmlDocument { XmlResolver = null };
			using (var reader = XmlReader.Create(path, new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null }))
				document.Load(reader);
			foreach (XmlElement dependency in document.SelectNodes("/configuration/runtime/*[local-name()='assemblyBinding']/*[local-name()='dependentAssembly']")!) {
				var identity = dependency.SelectSingleNode("*[local-name()='assemblyIdentity']") as XmlElement;
				var binding = dependency.SelectSingleNode("*[local-name()='bindingRedirect']") as XmlElement;
				if (identity is null || binding is null || string.IsNullOrEmpty(identity.GetAttribute("name"))) continue;
				var range = binding.GetAttribute("oldVersion").Split('-');
				if (range.Length > 2 || !Version.TryParse(range[0], out var minimum) ||
					!Version.TryParse(range[range.Length - 1], out var maximum) ||
					!Version.TryParse(binding.GetAttribute("newVersion"), out var version) || minimum > maximum)
					throw new ErrorException("Invalid assembly binding redirect for " + identity.GetAttribute("name"));
				redirects.Add(new Redirect(identity, minimum, maximum, version));
			}
		}
		public AssemblyDef? Resolve(IAssembly assembly, ModuleDef sourceModule) {
			foreach (var redirect in redirects) {
				if (!redirect.Matches(assembly)) continue;
				return resolver.Resolve(new AssemblyNameInfo(assembly.FullName) { Version = redirect.Version }, sourceModule);
			}
			return resolver.Resolve(assembly, sourceModule);
		}
		sealed class Redirect {
			readonly string name, token, culture;
			readonly Version minimum, maximum;
			public Version Version { get; }
			public Redirect(XmlElement identity, Version minimum, Version maximum, Version version) {
				name = identity.GetAttribute("name"); token = identity.GetAttribute("publicKeyToken"); culture = identity.GetAttribute("culture");
				this.minimum = minimum; this.maximum = maximum; Version = version;
			}
			public bool Matches(IAssembly assembly) =>
				StringComparer.OrdinalIgnoreCase.Equals(name, assembly.Name.String) && assembly.Version >= minimum && assembly.Version <= maximum &&
				(token.Length == 0 || StringComparer.OrdinalIgnoreCase.Equals(token, PublicKeyBase.ToPublicKeyToken(assembly.PublicKeyOrToken)?.ToString() ?? "null")) &&
				(culture.Length == 0 || StringComparer.OrdinalIgnoreCase.Equals(culture == "neutral" ? "" : culture, assembly.Culture?.String ?? ""));
		}
	}
}
