using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using NuGet.Frameworks;

namespace dnSpy.Decompiler.MSBuild {
	// Package labels and simple assembly names do not establish a compatible
	// replacement. Check the assets NuGet would choose for this project's TFM.
	// Cache is scoped to this export process and keyed by physical package path.
	sealed class PackageAssemblyIdentity {
		readonly ConcurrentDictionary<string, bool> matches = new ConcurrentDictionary<string, bool>(StringComparer.Ordinal);

		public bool Matches(string directory, string framework, string assemblyName, string identity) {
			if (string.IsNullOrEmpty(directory) || string.IsNullOrEmpty(framework) ||
				string.IsNullOrEmpty(assemblyName) || string.IsNullOrEmpty(identity)) return false;
			var path = Path.GetFullPath(directory);
			var key = path + "\0" + framework + "\0" + assemblyName + "\0" + identity;
			return matches.GetOrAdd(key, _ => Check(path, framework, assemblyName, identity));
		}

		static bool Check(string directory, string framework, string assemblyName, string identity) {
			try {
				if (!Directory.Exists(directory) || Path.GetFileName(assemblyName) != assemblyName) return false;
				var target = NuGetFramework.ParseFolder(framework);
				if (target.IsUnsupported) return false;
				string fileName = assemblyName + ".dll";
				// No RID is emitted by this exporter. Do not infer runtime selection
				// from a matching lib asset when RID-specific managed replacements exist.
				var runtimes = Path.Combine(directory, "runtimes");
				if (Directory.Exists(runtimes) && Directory.EnumerateFiles(runtimes, fileName, SearchOption.AllDirectories).Any()) return false;
				string? runtime = SelectAsset(Path.Combine(directory, "lib"), target, fileName, out bool runtimeGroup);
				string? compile = SelectAsset(Path.Combine(directory, "ref"), target, fileName, out bool refGroup);
				if (!refGroup) compile = runtime;
				return runtimeGroup && SameIdentity(runtime, identity) && SameIdentity(compile, identity);
			}
			catch (IOException) { return false; }
			catch (UnauthorizedAccessException) { return false; }
			catch (ArgumentException) { return false; }
			catch (BadImageFormatException) { return false; }
		}

		static string? SelectAsset(string root, NuGetFramework target, string fileName, out bool selectedGroup) {
			selectedGroup = false;
			if (!Directory.Exists(root)) return null;
			var groups = new List<(NuGetFramework Framework, string Directory)>();
			foreach (string directory in Directory.EnumerateDirectories(root)) {
				var framework = NuGetFramework.ParseFolder(Path.GetFileName(directory));
				if (!framework.IsUnsupported) groups.Add((framework, directory));
			}
			var nearest = new FrameworkReducer().GetNearest(target, groups.Select(g => g.Framework));
			if (nearest == null) return null;
			selectedGroup = true;
			var selected = groups.Where(g => g.Framework.Equals(nearest)).ToArray();
			// An empty nearest group or an ambiguous folder is not permission
			// to use a matching DLL from a more distant framework group.
			return selected.Length == 1 ? Path.Combine(selected[0].Directory, fileName) : null;
		}

		static bool SameIdentity(string? path, string identity) => path != null && File.Exists(path) &&
			StringComparer.OrdinalIgnoreCase.Equals(AssemblyName.GetAssemblyName(path).FullName, identity);
	}
}
