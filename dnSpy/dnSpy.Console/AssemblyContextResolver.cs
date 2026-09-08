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
		readonly List<Context> contexts = new List<Context>();
		public AssemblyContextResolver(IAssemblyResolver fallback, string manifest, IEnumerable<ModuleDef> inputs, bool useGac) {
			this.fallback = fallback;
			var document = new XmlDocument { XmlResolver = null };
			using (var reader = XmlReader.Create(manifest, new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null }))
				document.Load(reader);
			if (document.DocumentElement?.Name != "AssemblyContexts") throw new ErrorException("Expected AssemblyContexts root.");
			string root = Path.GetDirectoryName(manifest)!;
			var files = inputs.ToDictionary(m => Path.GetFullPath(m.Location), StringComparer.OrdinalIgnoreCase);
			var sources = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
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
				var resolver = new AssemblyResolver { EnableFrameworkRedirect = false, FindExactMatch = true, EnableTypeDefCache = true, UseGAC = useGac };
				resolver.PreSearchPaths.Add(directory);
				IAssemblyResolver configured = resolver;
				if (element.HasAttribute("Config")) configured = new ApplicationConfigResolver(configured, FullPath("Config"));
				var context = new ModuleContext { AssemblyResolver = configured, Resolver = new Resolver(configured) };
				resolver.DefaultModuleContext = context;
				contexts.Add(new Context(module, configured));
			}
		}

		public AssemblyDef? Resolve(IAssembly assembly, ModuleDef? sourceModule) {
			foreach (var context in contexts)
				if (ReferenceEquals(context.Source, sourceModule)) {
					if (sourceModule?.Assembly is AssemblyDef own && own.FullNameToken == assembly.FullNameToken) return own;
					// Do not fall back to the host's incompatible copy on a miss.
					return context.Resolver.Resolve(assembly, null);
				}
			// Dependency closure queries sometimes use the root project's resolver.
			// Respect the isolated context already attached to those dependencies.
			if (sourceModule?.Context?.AssemblyResolver is IAssemblyResolver nested && contexts.Any(c => ReferenceEquals(c.Resolver, nested)))
				return nested.Resolve(assembly, sourceModule);
			return fallback.Resolve(assembly, sourceModule);
		}
		sealed class Context {
			public ModuleDef Source { get; }
			public IAssemblyResolver Resolver { get; }
			public Context(ModuleDef source, IAssemblyResolver resolver) { Source = source; Resolver = resolver; }
		}
	}
}
