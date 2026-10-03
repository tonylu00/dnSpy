using System;
using System.Collections.Generic;
using dnlib.DotNet;

namespace dnSpy.Decompiler {
	/// <summary>Compilation target for modules without explicit framework metadata.</summary>
	public static class CompilationFrameworkInference {
		/// <summary>
		/// Dependencies must already be resolved in the caller's physical compatibility
		/// context. This helper neither resolves by name nor changes input metadata.
		/// </summary>
		public static TargetFrameworkInfo Infer(ModuleDef module, Func<ModuleDef, IEnumerable<ModuleDef>> dependencies) {
			var info = TargetFrameworkInfo.Create(module);
			if (info.FromAttribute || !info.IsDotNetFramework) return info;
			var pending = new Stack<ModuleDef>();
			var visited = new HashSet<ModuleDef>();
			pending.Push(module);
			while (pending.Count != 0) {
				var current = pending.Pop();
				if (!visited.Add(current)) continue;
				var candidate = TargetFrameworkInfo.Create(current);
				if (candidate.IsDotNetFramework && Version.TryParse(candidate.Version, out var version) &&
					Version.TryParse(info.Version, out var selected) && version > selected)
					info = candidate;
				foreach (var dependency in dependencies(current))
					if (dependency != null) pending.Push(dependency);
			}
			return info;
		}
	}
}
