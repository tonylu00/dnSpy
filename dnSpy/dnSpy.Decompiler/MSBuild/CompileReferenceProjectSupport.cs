using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Xml;
using System.Xml.Linq;

namespace dnSpy.Decompiler.MSBuild {
	/// <summary>Retains physical binary contracts when NuGet adds conflicting compile assets.</summary>
	public static class CompileReferenceProjectSupport {
		const string TaskName = "DnSpyFilterPreservedCompileReferences";
		const string TargetName = "DnSpyResolvePreservedCompileReferences";
		const string SourceFile = ".dnspy-metadata/FilterCompileReferences.cs";
		const string PreservedItem = "DnSpyPreservedCompileReference";
		static string SourceText() {
			using var stream = typeof(CompileReferenceProjectSupport).Assembly.GetManifestResourceStream("dnSpy.Decompiler.MSBuild.CompileReferenceTask.cs.txt");
			using var reader = new StreamReader(stream ?? throw new InvalidOperationException("Compile-reference task resource missing."));
			return reader.ReadToEnd();
		}
		static XElement[] Elements(XNamespace ns) => new[] {
			new XElement(ns + "UsingTask", new XAttribute("TaskName", TaskName), new XAttribute("TaskFactory", "RoslynCodeTaskFactory"),
				new XAttribute("AssemblyFile", "$(MSBuildToolsPath)/Microsoft.Build.Tasks.Core.dll"),
				new XElement(ns + "Task", new XElement(ns + "Code", new XAttribute("Type", "Class"), new XAttribute("Language", "cs"), new XAttribute("Source", "$(MSBuildProjectDirectory)/" + SourceFile)))),
			new XElement(ns + "Target", new XAttribute("Name", TargetName), new XAttribute("BeforeTargets", "_HandlePackageFileConflicts;ResolveAssemblyReferences"),
				new XElement(ns + TaskName, new XAttribute("References", "@(Reference)"), new XAttribute("ProjectDirectory", "$(MSBuildProjectDirectory)"), new XAttribute("PreservedReferences", "@(" + PreservedItem + ")"),
					new XElement(ns + "Output", new XAttribute("TaskParameter", "FilteredReferences"), new XAttribute("ItemName", "_DnSpyFilteredReferences"))),
				new XElement(ns + "ItemGroup", new XElement(ns + "Reference", new XAttribute("Remove", "@(Reference)")),
					new XElement(ns + "Reference", new XAttribute("Include", "@(_DnSpyFilteredReferences)")),
					new XElement(ns + "_DnSpyFilteredReferences", new XAttribute("Remove", "@(_DnSpyFilteredReferences)"))))
		};
		static void WriteSource(string directory) {
			string path = Path.Combine(directory, SourceFile);
			Directory.CreateDirectory(Path.GetDirectoryName(path)!);
			string text = SourceText();
			if (!File.Exists(path) || File.ReadAllText(path) != text) File.WriteAllText(path, text);
		}
		internal static void Write(string directory, XmlWriter writer) {
			WriteSource(directory);
			foreach (var element in Elements(XNamespace.None)) element.WriteTo(writer);
		}
		internal static void WritePreservedReference(XmlWriter writer, string path) {
			writer.WriteStartElement(PreservedItem);
			writer.WriteAttributeString("Include", path);
			writer.WriteEndElement();
		}
		static IEnumerable<string> Projects(string directory) {
			// Do not refresh generated copies or follow directory links outside the export.
			foreach (var file in Directory.EnumerateFiles(directory, "*.csproj"))
				if ((File.GetAttributes(file) & FileAttributes.ReparsePoint) == 0) yield return file;
			foreach (var child in Directory.EnumerateDirectories(directory)) {
				if ((File.GetAttributes(child) & FileAttributes.ReparsePoint) != 0) continue;
				var name = Path.GetFileName(child);
				if (name.Equals("bin", StringComparison.OrdinalIgnoreCase) || name.Equals("obj", StringComparison.OrdinalIgnoreCase)) continue;
				foreach (var file in Projects(child)) yield return file;
			}
		}
		static bool Equivalent(XElement left, XElement right) => XNode.DeepEquals(
			XElement.Parse(left.ToString()), XElement.Parse(right.ToString()));
		/// <summary>Refreshes only compile-reference build support in dnSpy-exported projects.</summary>
		public static int Refresh(string directory) {
			string root = Path.GetFullPath(directory);
			if (!Directory.Exists(root)) throw new DirectoryNotFoundException(root);
			int count = 0;
			foreach (var file in Projects(root)) {
				var document = XDocument.Load(file, LoadOptions.PreserveWhitespace);
				var project = document.Root ?? throw new InvalidDataException("Project root missing: " + file);
				if (!project.Elements().Any(e => e.Name.LocalName == "UsingTask" && (string?)e.Attribute("TaskName") == "DnSpyRestoreMetadataFields")) continue;
				// WPF temporary projects contain generated copies; only refresh
				// the real source project with its own exported support directory.
				if (!File.Exists(Path.Combine(Path.GetDirectoryName(file)!, ".dnspy-metadata", "RestoreFields.cs"))) continue;
				if (Path.GetFileNameWithoutExtension(file).EndsWith("_wpftmp", StringComparison.OrdinalIgnoreCase)) continue;
				var old = project.Elements().Where(e => e.Name.LocalName == "UsingTask" && (string?)e.Attribute("TaskName") == TaskName ||
					e.Name.LocalName == "Target" && (string?)e.Attribute("Name") == TargetName).ToArray();
				var replacements = Elements(project.Name.Namespace);
				bool same = old.Length == replacements.Length && old.Zip(replacements, Equivalent).All(x => x);
				var paths = project.Descendants().Where(e => e.Name.LocalName == "Reference" &&
					e.Elements().Any(x => x.Name.LocalName == "SpecificVersion" && x.Value.Equals("true", StringComparison.OrdinalIgnoreCase)))
					.Select(e => e.Elements().FirstOrDefault(x => x.Name.LocalName == "HintPath")?.Value)
					.Where(p => !string.IsNullOrEmpty(p)).Distinct(StringComparer.Ordinal).OrderBy(p => p, StringComparer.Ordinal).ToArray();
				var preserved = project.Descendants(project.Name.Namespace + PreservedItem).ToArray();
				bool samePaths = preserved.Select(e => (string?)e.Attribute("Include")).OrderBy(p => p, StringComparer.Ordinal).SequenceEqual(paths);
				WriteSource(Path.GetDirectoryName(file)!);
				if (!same || !samePaths) {
					if (!same) {
						foreach (var element in old) element.Remove();
						project.Add(replacements);
					}
					if (!samePaths) {
						foreach (var element in preserved) element.Remove();
						if (paths.Length != 0) project.Add(new XElement(project.Name.Namespace + "ItemGroup",
							paths.Select(p => new XElement(project.Name.Namespace + PreservedItem, new XAttribute("Include", p!)))));
					}
					document.Save(file);
				}
				count++;
			}
			return count;
		}
	}
}
