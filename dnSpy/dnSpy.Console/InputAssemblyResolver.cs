using System;
using System.Collections.Concurrent;
using System.IO;
using System.Linq;
using dnlib.DotNet;

namespace dnSpy_Console {
	// dnlib's global identity cache cannot distinguish compatibility deployments
	// or backup files. Keep the selected physical input stable for each source.
	sealed class InputAssemblyResolver : IAssemblyResolver {
		readonly IAssemblyResolver fallback;
		readonly ILookup<string, Candidate> candidates;
		readonly ConcurrentDictionary<(ModuleDef? Source, string Identity), AssemblyDef> cache = new ConcurrentDictionary<(ModuleDef?, string), AssemblyDef>();

		public InputAssemblyResolver(IAssemblyResolver fallback, System.Collections.Generic.IEnumerable<ModuleDef> modules) {
			this.fallback = fallback;
			candidates = modules.Where(m => m.IsManifestModule && m.Assembly is not null && !string.IsNullOrEmpty(m.Location))
				.Select(m => new Candidate(m)).ToLookup(c => c.Assembly.FullNameToken, StringComparer.OrdinalIgnoreCase);
		}

		public AssemblyDef? Resolve(IAssembly assembly, ModuleDef? sourceModule) {
			if (assembly is null)
				return null;
			if (sourceModule?.Assembly is AssemblyDef own && SameIdentity(own, assembly))
				return own;
			var identity = assembly.FullNameToken;
			if (cache.TryGetValue((sourceModule, identity), out var cached))
				return cached;
			var matches = candidates[identity].ToArray();
			if (matches.Length == 0)
				return fallback.Resolve(assembly, sourceModule);
			// A deployed Library.dll takes precedence over Library_orig.dll. Each
			// backup still resolves references to its own assembly through 'own'.
			var canonical = matches.Where(c => c.CanonicalName).ToArray();
			if (canonical.Length != 0)
				matches = canonical;
			var sourceDirectory = string.IsNullOrEmpty(sourceModule?.Location) ? null : Path.GetDirectoryName(sourceModule!.Location);
			var selected = matches.OrderBy(c => DirectoryRank(sourceDirectory, c.Directory))
				.ThenBy(c => c.Location, StringComparer.OrdinalIgnoreCase).First().Assembly;
			return cache.GetOrAdd((sourceModule, identity), selected);
		}

		static bool SameIdentity(IAssembly a, IAssembly b) => StringComparer.OrdinalIgnoreCase.Equals(a.FullNameToken, b.FullNameToken);

		static (int Kind, int Up, int Down) DirectoryRank(string? source, string target) {
			if (string.IsNullOrEmpty(source))
				return (2, 0, 0);
			int up = 0;
			for (var directory = new DirectoryInfo(source); directory is not null; directory = directory.Parent, up++) {
				if (StringComparer.OrdinalIgnoreCase.Equals(directory.FullName, target))
					return (0, up, 0);
				var prefix = directory.FullName.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar;
				if (target.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
					return (1, up, target.Substring(prefix.Length).Count(c => c == Path.DirectorySeparatorChar) + 1);
			}
			return (2, 0, 0);
		}

		sealed class Candidate {
			public AssemblyDef Assembly { get; }
			public string Location { get; }
			public string Directory { get; }
			public bool CanonicalName { get; }
			public Candidate(ModuleDef module) {
				Assembly = module.Assembly!;
				Location = Path.GetFullPath(module.Location);
				Directory = Path.GetDirectoryName(Location)!;
				var extension = Path.GetExtension(Location);
				CanonicalName = StringComparer.OrdinalIgnoreCase.Equals(Path.GetFileNameWithoutExtension(Location), Assembly.Name.String) &&
					(new[] { ".dll", ".exe", ".winmd" }).Contains(extension, StringComparer.OrdinalIgnoreCase);
			}
		}
	}
}
