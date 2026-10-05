using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Xml;
using dnlib.DotNet;

namespace dnSpy_Console {
	// Explicit source contexts isolate compatibility files whose dependencies have
	// the same identities as a different implementation in the host directory.
	sealed class AssemblyContextResolver : IAssemblyResolver {
		readonly IAssemblyResolver fallback;
		readonly Dictionary<string, ModuleDef> inputs;
		readonly Dictionary<ModuleDef, IAssemblyResolver> contexts = new Dictionary<ModuleDef, IAssemblyResolver>();
		readonly HashSet<IAssemblyResolver> nestedResolvers = new HashSet<IAssemblyResolver>();
		public AssemblyContextResolver(IAssemblyResolver fallback, string manifest, IEnumerable<ModuleDef> inputs, bool useGac, IEnumerable<string> searchPaths) {
			this.fallback = fallback;
			var document = new XmlDocument { XmlResolver = null };
			using (var reader = XmlReader.Create(manifest, new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null }))
				document.Load(reader);
			if (document.DocumentElement?.Name != "AssemblyContexts") throw new ErrorException("Expected AssemblyContexts root.");
			string root = Path.GetDirectoryName(manifest)!;
			var files = inputs.ToDictionary(m => Path.GetFullPath(m.Location), StringComparer.OrdinalIgnoreCase);
			this.inputs = files;
			var sources = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
			// Share only an identical physical directory/configuration context.
			// Sharing by assembly identity would merge compatibility deployments;
			// one resolver per input duplicates the complete dependency graph.
			var shared = new Dictionary<(string Directory, string? Config), IAssemblyResolver>();
			var supportPaths = searchPaths.Distinct(StringComparer.OrdinalIgnoreCase).Where(Directory.Exists).ToArray();
			foreach (XmlNode node in document.DocumentElement.ChildNodes) {
				if (node is not XmlElement element) continue;
				if (element.Name != "Context") throw new ErrorException("Unknown assembly context element: " + element.Name);
				string FullPath(string attribute) {
					string value = element.GetAttribute(attribute);
					if (string.IsNullOrWhiteSpace(value)) throw new ErrorException("Missing assembly context " + attribute);
					return Path.GetFullPath(Path.Combine(root, value));
				}
				string source = FullPath("Source"), directory = FullPath("Directory");
				if (!files.TryGetValue(source, out var module) || !sources.Add(source)) throw new ErrorException("Assembly context source must name one distinct input: " + source);
				if (!Directory.Exists(directory)) throw new ErrorException("Assembly context directory does not exist: " + directory);
				string? config = element.HasAttribute("Config") ? FullPath("Config") : null;
				if (shared.TryGetValue((directory, config), out var cached)) {
					contexts.Add(module, cached);
					continue;
				}
				var resolver = new AssemblyResolver { EnableFrameworkRedirect = false, FindExactMatch = true, EnableTypeDefCache = true, UseGAC = useGac };
				resolver.PreSearchPaths.Add(directory);
				// Explicit support paths remain available without importing the host's
				// identity cache or automatically discovered application directory.
				foreach (var path in supportPaths) resolver.PostSearchPaths.Add(path);
				IAssemblyResolver configured = resolver;
				if (config != null) configured = new ApplicationConfigResolver(configured, config);
				var context = new ModuleContext { AssemblyResolver = configured, Resolver = new Resolver(configured) };
				resolver.DefaultModuleContext = context;
				shared.Add((directory, config), configured);
				contexts.Add(module, configured);
				nestedResolvers.Add(configured);
			}
		}

		public AssemblyDef? Resolve(IAssembly assembly, ModuleDef? sourceModule) {
			if (sourceModule != null && contexts.TryGetValue(sourceModule, out var sourceResolver)) {
				if (sourceModule.Assembly is AssemblyDef own && own.FullNameToken == assembly.FullNameToken) return own;
				// Do not fall back to the host's incompatible copy on a miss.
				return Canonicalize(sourceResolver.Resolve(assembly, null), sourceResolver);
			}
			// Dependency closure queries sometimes use the root project's resolver.
			// Respect the isolated context already attached to those dependencies.
			if (sourceModule?.Context?.AssemblyResolver is IAssemblyResolver nested && nestedResolvers.Contains(nested))
				return Canonicalize(nested.Resolve(assembly, sourceModule), nested);
			return fallback.Resolve(assembly, sourceModule);
		}

		AssemblyDef? Canonicalize(AssemblyDef? result, IAssemblyResolver resolver) {
			// Aliases are registered on the exported definitions. A separately
			// loaded copy of that exact file must use those definitions only when
			// its dependency context is also identical. Neither identity nor MVID
			// alone distinguishes compatibility files or host configurations.
			var module = result?.ManifestModule;
			if (module != null && !string.IsNullOrEmpty(module.Location) &&
				inputs.TryGetValue(Path.GetFullPath(module.Location), out var input) && input.Assembly != null &&
				contexts.TryGetValue(input, out var inputResolver) && ReferenceEquals(inputResolver, resolver) &&
				input.Mvid == module.Mvid && StringComparer.OrdinalIgnoreCase.Equals(input.Assembly.FullNameToken, result!.FullNameToken))
				return input.Assembly;
			return result;
		}
	}
}
