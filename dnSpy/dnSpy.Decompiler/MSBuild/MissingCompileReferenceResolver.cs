using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Xml.Linq;
using dnlib.DotNet;

namespace dnSpy.Decompiler.MSBuild {
	/// <summary>Resolves omitted compile references against explicitly supplied physical binaries.</summary>
	public static class MissingCompileReferenceResolver {
		public sealed class Resolution {
			public string Project { get; internal set; } = string.Empty;
			public string Source { get; internal set; } = string.Empty;
			public string SourceHash { get; internal set; } = string.Empty;
			public string Identity { get; internal set; } = string.Empty;
			public string Target { get; internal set; } = string.Empty;
			public string TargetHash { get; internal set; } = string.Empty;
			public Guid? TargetMvid { get; internal set; }
		}
		sealed class Candidate {
			public string Path = string.Empty, Hash = string.Empty, Identity = string.Empty;
			public Guid? Mvid;
		}
		static string Hash(string file) {
			using var stream = File.OpenRead(file);
			using var algorithm = SHA256.Create();
			return BitConverter.ToString(algorithm.ComputeHash(stream)).Replace("-", string.Empty);
		}
		static string Identity(string name) => new AssemblyName(name).FullName!;
		static void NoLinks(string path) {
			for (string? current = path; current != null; current = Path.GetDirectoryName(current))
				if ((File.GetAttributes(current) & System.IO.FileAttributes.ReparsePoint) != 0)
					throw new InvalidDataException("Linked export or candidate path: " + path);
		}
		/// <summary>Validates all proposed bindings before changing generated projects; never edits source or binaries.</summary>
		public static IReadOnlyList<Resolution> Resolve(string exportDirectory, IEnumerable<string> binaryDirectories) {
			string root = Path.GetFullPath(exportDirectory);
			NoLinks(root);
			string mapPath = Path.Combine(root, "dnspy-export-map.xml");
			NoLinks(mapPath);
			var map = XDocument.Load(mapPath).Root;
			if (map == null || map.Name != "DnSpyExportMap" || (string?)map.Attribute("Version") != "1" || (string?)map.Attribute("ExportErrors") != "0")
				throw new InvalidDataException("A successful physical dnSpy export map is required.");
			var candidates = new Dictionary<string, List<Candidate>>(StringComparer.OrdinalIgnoreCase);
			foreach (string directory in binaryDirectories.Select(Path.GetFullPath).Distinct(StringComparer.OrdinalIgnoreCase)) {
				NoLinks(directory);
				foreach (string path in Directory.EnumerateFiles(directory).OrderBy(p => p, StringComparer.Ordinal)) {
					if (!Path.GetExtension(path).Equals(".dll", StringComparison.OrdinalIgnoreCase) && !Path.GetExtension(path).Equals(".exe", StringComparison.OrdinalIgnoreCase)) continue;
					NoLinks(path);
					string identity;
					try { identity = AssemblyName.GetAssemblyName(path).FullName!; }
					catch (BadImageFormatException) { continue; }
					using var module = ModuleDefMD.Load(path);
					var candidate = new Candidate { Path = path, Identity = identity, Hash = Hash(path), Mvid = module.Mvid };
					if (!candidates.TryGetValue(identity, out var group)) candidates.Add(identity, group = new List<Candidate>());
					group.Add(candidate);
				}
			}
			var plans = new List<Tuple<string, XDocument>>();
			var resolutions = new List<Resolution>();
			var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
			foreach (var entry in map.Elements("Project")) {
				string relative = (string?)entry.Attribute("Project") ?? throw new InvalidDataException("Missing project path.");
				string projectPath = Path.GetFullPath(Path.Combine(root, relative));
				if (!projectPath.StartsWith(root.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) ||
					!projectPath.EndsWith(".csproj", StringComparison.OrdinalIgnoreCase) || !seen.Add(projectPath) ||
					projectPath.Split(Path.DirectorySeparatorChar).Any(p => p.Equals("bin", StringComparison.OrdinalIgnoreCase) || p.Equals("obj", StringComparison.OrdinalIgnoreCase)) ||
					Path.GetFileNameWithoutExtension(projectPath).EndsWith("_wpftmp", StringComparison.OrdinalIgnoreCase))
					throw new InvalidDataException("Invalid physical export project: " + relative);
				NoLinks(projectPath);
				string source = Path.GetFullPath((string?)entry.Attribute("Source") ?? throw new InvalidDataException("Missing source path."));
				using var module = ModuleDefMD.Load(source);
				if (module.Mvid != Guid.Parse((string?)entry.Attribute("Mvid") ?? string.Empty) || module.Assembly == null || module.Assembly.Name != (string?)entry.Attribute("AssemblyName"))
					throw new InvalidDataException("Original physical module identity changed: " + source);
				string sourceHash = Hash(source);
				var document = XDocument.Load(projectPath, LoadOptions.PreserveWhitespace);
				var project = document.Root ?? throw new InvalidDataException("Missing project root.");
				if (project.Name.LocalName != "Project") throw new InvalidDataException("Invalid project root.");
				XNamespace ns = project.Name.Namespace;
				bool changed = false;
				foreach (var reference in project.Elements(ns + "ItemGroup").Elements(ns + "Reference")) {
					if (reference.Element(ns + "HintPath") != null) continue;
					string? include = (string?)reference.Attribute("Include");
					if (string.IsNullOrEmpty(include)) continue;
					var refs = module.GetAssemblyRefs().Where(r => r.Name == include || r.FullName.Equals(include, StringComparison.OrdinalIgnoreCase)).ToArray();
					if (refs.Length == 0) continue;
					if (refs.Length != 1) throw new InvalidDataException("Ambiguous original assembly reference: " + include);
					string identity = Identity(refs[0].FullName);
					if (!candidates.TryGetValue(identity, out var matches)) continue;
					if (matches.Count != 1) throw new InvalidDataException("Ambiguous physical candidates for " + identity);
					var candidate = matches[0];
					reference.SetAttributeValue("Include", identity);
					reference.Add(new XElement(ns + "HintPath", candidate.Path));
					reference.SetElementValue(ns + "SpecificVersion", "true");
					if (!project.Descendants(ns + "DnSpyPreservedCompileReference").Any(e => (string?)e.Attribute("Include") == candidate.Path))
						project.Add(new XElement(ns + "ItemGroup", new XElement(ns + "DnSpyPreservedCompileReference", new XAttribute("Include", candidate.Path))));
					resolutions.Add(new Resolution { Project = projectPath, Source = source, SourceHash = sourceHash, Identity = identity,
						Target = candidate.Path, TargetHash = candidate.Hash, TargetMvid = candidate.Mvid });
					changed = true;
				}
				if (changed) plans.Add(Tuple.Create(projectPath, document));
			}
			foreach (var resolution in resolutions)
				if (Hash(resolution.Source) != resolution.SourceHash || Hash(resolution.Target) != resolution.TargetHash)
					throw new InvalidDataException("Physical binding changed during resolution.");
			foreach (var plan in plans) plan.Item2.Save(plan.Item1);
			return resolutions;
		}
	}
}
