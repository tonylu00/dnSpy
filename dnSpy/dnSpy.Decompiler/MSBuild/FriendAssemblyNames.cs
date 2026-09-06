using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security;
using dnlib.DotNet;

namespace dnSpy.Decompiler.MSBuild {
	static class FriendAssemblyNames {
		public static IReadOnlyDictionary<CustomAttribute, string> Create(IEnumerable<ModuleDef> modules) {
			var assemblies = modules.Where(m => m.IsManifestModule && m.Assembly is not null).Select(m => m.Assembly!).Distinct().ToArray();
			var byName = assemblies.ToLookup(a => a.Name.String, StringComparer.OrdinalIgnoreCase);
			var names = new Dictionary<CustomAttribute, string>();
			foreach (var assembly in assemblies) {
				foreach (var attribute in assembly.CustomAttributes) {
					if (attribute.TypeFullName != "System.Runtime.CompilerServices.InternalsVisibleToAttribute" ||
						attribute.ConstructorArguments.Count != 1 || attribute.ConstructorArguments[0].Type.ElementType != ElementType.String)
						continue;
					var text = attribute.ConstructorArguments[0].Value;
					var friend = TryParse(text is UTF8String utf8 ? utf8.String : text as string);
					if (friend?.Name is null)
						continue;
					var key = friend.GetPublicKey();
					if (key is null || key.Length == 0)
						continue;
					var candidates = byName[friend.Name].ToArray();
					// Exported projects are unsigned. Adapt a keyed grant only when all
					// exported assemblies with this name had that exact full public key.
					// Compatible copies/versions are fine; mixed keys must not gain access.
					if (candidates.Length == 0 || candidates.Any(a => a.PublicKey?.Data is not byte[] data || !key.SequenceEqual(data)))
						continue;
					names.Add(attribute, new AssemblyName { Name = friend.Name }.FullName);
				}
			}
			return names;
		}

		static AssemblyName? TryParse(string? value) {
			if (string.IsNullOrEmpty(value))
				return null;
			// AssemblyName accepts and discards unknown qualifiers. Only project
			// a simple name plus PublicKey, respecting quoted/escaped name commas.
			char quote = '\0';
			int separator = -1;
			for (int i = 0; i < value!.Length; i++) {
				char c = value[i];
				if (c == '\\') { i++; continue; }
				if (quote != '\0') { if (c == quote) quote = '\0'; continue; }
				if (c == '\'' || c == '"') { quote = c; continue; }
				if (c == ',') { separator = i; break; }
			}
			if (separator < 0)
				return null;
			var qualifier = value.Substring(separator + 1).Split('=');
			if (qualifier.Length != 2 || !StringComparer.OrdinalIgnoreCase.Equals(qualifier[0].Trim(), "PublicKey") ||
				qualifier[1].Trim().Length == 0 || (qualifier[1].Trim().Length & 1) != 0 || qualifier[1].Trim().Any(c => !Uri.IsHexDigit(c)))
				return null;
			try {
				var name = new AssemblyName(value);
				// .NET Framework's display-name parser retains only the token.
				// Restore the full declared key for an exact comparison on both runtimes.
				name.SetPublicKey(new PublicKey(qualifier[1].Trim()).Data);
				return name;
			}
			catch (ArgumentException) { return null; }
			catch (FileLoadException) { return null; }
			catch (SecurityException) { return null; }
		}
	}
}
